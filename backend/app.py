from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.services.openai_connector import openai_connector 
from src.services.cosmos_connector import cosmos_connector  # Il tuo connettore Cosmos
from pydantic import BaseModel
from datetime import datetime
import uuid
from src.models.schemas import ChatRequest, LoginRequest
from src.services.auth_service import verify_password, create_access_token, decode_token, hash_password
import uvicorn


app = FastAPI()
security_agent = HTTPBearer()

DATABASE_NAME = "users"
CONTAINER_NAME = "users_chat"
USER_CONTAINER_NAME = "users_list"  # Container per salvare le credenziali utenti


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_agent)) -> str:
    try:
        token = credentials.credentials
        payload = decode_token(token)
        return payload.sub  
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token non valido o scaduto",
            headers={"WWW-Authenticate": "Bearer"},
        )

@app.post("/register")
def register_user(credentials: LoginRequest):
    try:
        # controllo se l'utente esiste già per evitare duplicati
        try:
            existing_user = cosmos_connector.get_item(
                database_name=DATABASE_NAME,
                container_name=USER_CONTAINER_NAME,
                item_id=credentials.user_id,
                partition_key=credentials.user_id  # La partizione è user_id
            )
            if existing_user:
                return {"success": False, "error": "Questo User ID è già registrato."}
        except Exception:
            pass

        # Hashiamo la password usando la funzione bcrypt dell'auth_service
        password_encrypted = hash_password(credentials.password)

        # Creiamo il documento utente conforme a Cosmos DB
        user_document = {
            "id": credentials.user_id,          # ID univoco
            "user_id": credentials.user_id,     # Partition Key obbligatoria
            "password_hash": password_encrypted,
            "createdAt": datetime.utcnow().isoformat() + "Z"
        }

        # Salviamo l'utente nel container dedicato
        cosmos_connector.upsert_item(
            database_name=DATABASE_NAME,
            container_name=USER_CONTAINER_NAME,
            item=user_document
        )
        return {"success": True}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


# ENDPOINT AGGIORNATO: LOGIN REALE SU COSMOS
@app.post("/login")
def login(credentials: LoginRequest):
    try:
        # Andiamo a prendere l'utente reale salvato su Cosmos DB
        try:
            user_document = cosmos_connector.get_item(
                database_name=DATABASE_NAME,
                container_name=USER_CONTAINER_NAME,
                item_id=credentials.user_id,
                partition_key=credentials.user_id
            )
        except Exception:
            return {"success": False, "error": "User ID o Password errati (Utente non trovato)"}
        
        # Estraiamo l'hash salvato nel documento
        db_hash = user_document.get("password_hash")
        
        # Verifichiamo la password inserita con l'hash del DB
        if verify_password(credentials.password, db_hash):
            token = create_access_token(
                user_id=credentials.user_id,
                email=f"{credentials.user_id}@azienda.com",
                name=credentials.user_id,
                is_global_admin=False,
            )
            return {"success": True, "access_token": token, "user_id": credentials.user_id}
        
        return {"success": False, "error": "User ID o Password errati"}
    except Exception as e:
        return {"success": False, "error": str(e)}

# STOP LOGIN!

@app.post("/ask")
def ask_model(data: ChatRequest, current_user: str = Depends(get_current_user)):
    try:
        user_id = data.user_id
        session_id = data.session_id
        if user_id != current_user:
            raise HTTPException(status_code=403, detail="Non sei autorizzato ad accedere ai dati di un altro utente")
        
        # se non viene passata una session_id, significa che è una NUOVA chat e crea un nuovo item nel cosmos
        if not session_id:
            session_id = str(uuid.uuid4())
            chat_document = {
                "id": session_id,
                "user_id": user_id,
                "title": data.question[:30] + "...", # inizio della domanda come titolo temporaneo
                "messages": []
            }
        else:
            # recupero la chat
            try:
                chat_document = cosmos_connector.get_item(
                    database_name=DATABASE_NAME,
                    container_name=CONTAINER_NAME,
                    item_id=session_id,
                    partition_key=user_id
                )
            except Exception:
                # se per qualche motivo il session_id non esiste, lo creiamo da zero
                chat_document = {
                    "id": session_id,
                    "user_id": user_id,
                    "title": data.question[:30] + "...",
                    "messages": []
                }

        # metto il nuovo messaggio dell'utente nella cronologia
        chat_document["messages"].append({"role": "user", "content": data.question})

        history_for_openai = []
        for msg in chat_document["messages"]:
            content_type = "input_text" if msg["role"] == "user" else "output_text"
            history_for_openai.append({
                "role": msg["role"],
                "content": [{"type": content_type, "text": msg["content"]}]
            })

        answ = openai_connector.get_output_text(input=history_for_openai)
        chat_document["messages"].append({"role": "assistant", "content": answ})

        # 5. Salviamo la chat aggiornata su Cosmos DB
        cosmos_connector.upsert_item(
            database_name=DATABASE_NAME,
            container_name=CONTAINER_NAME,
            item=chat_document
        )

        return {
            "success": True, 
            "answer": answ, 
            "session_id": session_id,
            "messages": chat_document["messages"] 
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/history/{user_id}")
def get_user_history(user_id: str, current_user: str = Depends(get_current_user)):
    try:
        if user_id != current_user:
            raise HTTPException(status_code=403, detail="Accesso negato")
        query = "SELECT c.id, c.title FROM c WHERE c.user_id = @userId ORDER BY c.updatedAt DESC"
        parameters = [{"name": "@userId", "value": user_id}]
        lista_chat = cosmos_connector.query_items(
            database_name=DATABASE_NAME, container_name=CONTAINER_NAME,
            query=query, parameters=parameters, enable_cross_partition_query=False
        )
        return {"success": True, "history": lista_chat}
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/chat/{user_id}/{session_id}")
def get_chat_messages(user_id: str, session_id: str, current_user: str = Depends(get_current_user)):
    try:
        if user_id != current_user:
            raise HTTPException(status_code=403, detail="Accesso negato")
        chat = cosmos_connector.get_item(DATABASE_NAME, CONTAINER_NAME, session_id, user_id)
        return {"success": True, "messages": chat.get("messages", [])}
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True)