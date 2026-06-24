from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.services.openai_connector import openai_connector 
from src.services.cosmos_connector import cosmos_connector  
from pydantic import BaseModel
from datetime import datetime
import uuid
from src.models.schemas import ChatRequest, LoginRequest
from src.services.auth_service import verify_password, create_access_token, decode_token, hash_password
import uvicorn
import requests
from bs4 import BeautifulSoup


app = FastAPI()
security_agent = HTTPBearer()

DATABASE_NAME = "users"
CONTAINER_NAME = "users_chat"
USER_CONTAINER_NAME = "users_list"  
URL_FISSO = "https://www.mymovies.it/cinema/milano/"


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
        try:
            existing_user = cosmos_connector.get_item(
                database_name=DATABASE_NAME,
                container_name=USER_CONTAINER_NAME,
                item_id=credentials.user_id,
                partition_key=credentials.user_id  
            )
            if existing_user:
                return {"success": False, "error": "Questo User ID è già registrato."}
        except Exception:
            pass

        password_encrypted = hash_password(credentials.password)

        user_document = {
            "id": credentials.user_id,          
            "user_id": credentials.user_id,     
            "password_hash": password_encrypted,
            "createdAt": datetime.utcnow().isoformat() + "Z"
        }

        cosmos_connector.upsert_item(
            database_name=DATABASE_NAME,
            container_name=USER_CONTAINER_NAME,
            item=user_document
        )
        return {"success": True}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/login")
def login(credentials: LoginRequest):
    try:
        try:
            user_document = cosmos_connector.get_item(
                database_name=DATABASE_NAME,
                container_name=USER_CONTAINER_NAME,
                item_id=credentials.user_id,
                partition_key=credentials.user_id
            )
        except Exception:
            return {"success": False, "error": "User ID o Password errati (Utente non trovato)"}
        
        db_hash = user_document.get("password_hash")
        
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

headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

@app.post("/ask")
def ask_model(data: ChatRequest, current_user: str = Depends(get_current_user)):
    try:
        user_id = data.user_id
        session_id = data.session_id
        if user_id != current_user:
            raise HTTPException(status_code=403, detail="Non sei autorizzato")
        
        # Gestione recupero/creazione del documento chat (identica a prima)
        if not session_id:
            session_id = str(uuid.uuid4())
            chat_document = {
                "id": session_id,
                "user_id": user_id,
                "title": data.question[:30] + "...", 
                "system_prompt": data.system_prompt,
                "messages": []
            }
        else:
            try:
                chat_document = cosmos_connector.get_item(DATABASE_NAME, CONTAINER_NAME, session_id, user_id)
                chat_document["system_prompt"] = data.system_prompt 
            except Exception:
                chat_document = {"id": session_id, "user_id": user_id, "title": data.question[:30] + "...", "system_prompt": data.system_prompt, "messages": []}

        # Salva il messaggio dell'utente
        chat_document["messages"].append({"role": "user", "content": data.question})

        # --- LOGICA DI SCRAPING LATO BACKEND ---
        prompt_di_sistema_finale = chat_document.get("system_prompt") or ""
        
        if data.web_search:
            try:
                # Eseguiamo la chiamata HTTP (verify=False se hai problemi di certificati aziendali)
                res_web = requests.get(URL_FISSO, timeout=15, headers = headers_browser)
                # print("stat", res_web)
                if res_web.status_code == 200:
                    soup = BeautifulSoup(res_web.text, 'html.parser')
                    # Pulizia dei tag inutili
                    for script in soup(["script", "style"]):
                        script.extract()
                    testo_pulito = soup.get_text(separator=" ", strip=True)[:4000] # Tronca per stare nei limiti di token
                    print("t pulito", soup.get_text)
                    
                    # Arricchiamo il system prompt temporaneo per questa chiamata
                    contesto_web = f"\n\n[CONTESTO AGGIUNTIVO DAL SITO {URL_FISSO}]:\n{testo_pulito}\n"
                    prompt_di_sistema_finale += contesto_web
            except Exception as e:
                # Logga l'errore o gestiscilo come preferisci; qui andiamo avanti senza bloccare la chat
                print(f"Errore scraping backend: {e}")

        # Costruzione della history per OpenAI
        history_for_openai = []
        
        # Se c'è un prompt di sistema (base o arricchito dal web), lo inseriamo all'inizio
        if prompt_di_sistema_finale:
            history_for_openai.append({
                "role": "system",
                "content": [{"type": "input_text", "text": prompt_di_sistema_finale}]
            })

        

        for msg in chat_document["messages"]:
            content_type = "input_text" if msg["role"] == "user" else "output_text"
            history_for_openai.append({
                "role": msg["role"],
                "content": [{"type": content_type, "text": msg["content"]}]
            })

        # Chiamata all'LLM
        answ = openai_connector.get_output_text(input=history_for_openai)
        chat_document["messages"].append({"role": "assistant", "content": answ})

        # Salvataggio definitivo su Cosmos DB
        cosmos_connector.upsert_item(DATABASE_NAME, CONTAINER_NAME, chat_document)

        return {
            "success": True, 
            "answer": answ, 
            "session_id": session_id,
            "messages": chat_document["messages"] 
        }
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
        
        # <-- MODIFICATO: Restituisce anche il system_prompt oltre ai messaggi
        return {
            "success": True, 
            "messages": chat.get("messages", []),
            "system_prompt": chat.get("system_prompt", "") 
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True)