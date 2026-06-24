from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.services.openai_connector import openai_connector 
from src.services.cosmos_connector import cosmos_connector  
from pydantic import BaseModel
from datetime import datetime
import uuid
from src.models.schemas import ChatRequest, LoginRequest, ProfileUpdateRequest
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

        password_encrypted = hash_password(credentials.password) #CRIPTO LA PASSWORD

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
        
        # CREO ACCESS TOKEN
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
        # Sovrascriviamo o usiamo direttamente current_user per evitare disallineamenti
        user_id = current_user
        session_id = data.session_id
        
        # Gestione recupero/creazione dello chat_document
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
                chat_document = {
                    "id": session_id, 
                    "user_id": user_id, 
                    "title": data.question[:30] + "...", 
                    "system_prompt": data.system_prompt, 
                    "messages": []
                }

        chat_document["messages"].append({"role": "user", "content": data.question})

        # --- RECUPERO DEI FILM PREFERITI DAL PROFILO UTENTE ---
        contesto_preferiti = ""
        try:
            user_profile = cosmos_connector.get_item(
                database_name=DATABASE_NAME,
                container_name=USER_CONTAINER_NAME,
                item_id=user_id,
                partition_key=user_id
            )
            fav_movies = user_profile.get("favorite_movies", [])
            if fav_movies:
                lista_film_str = ", ".join(fav_movies)
                contesto_preferiti = f"\n\n[INFORMAZIONI UTENTE]: I film preferiti dell'utente attuale sono: {lista_film_str}. Usa questa informazione per personalizzare i tuoi consigli o fare riferimenti se pertinente."
        except Exception as e:
            print(f"Nessun profilo trovato o errore nel recupero preferiti: {e}")

        # Uniamo il system prompt con il contesto dei film preferiti
        prompt_di_sistema_finale = (chat_document.get("system_prompt") or "") + contesto_preferiti
        
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
                    
                    # Arricchiamo il system prompt temporaneo per questa chiamata
                    contesto_web = f"\n\n[CONTESTO AGGIUNTIVO DAL SITO {URL_FISSO}]:\n{testo_pulito}\n"
                    prompt_di_sistema_finale += contesto_web
            except Exception as e:
                # Logga l'errore o gestiscilo come preferisci; qui andiamo avanti senza bloccare la chat
                print(f"Errore scraping backend: {e}")

        history_for_openai = []
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

        answ = openai_connector.get_output_text(input=history_for_openai)
        chat_document["messages"].append({"role": "assistant", "content": answ})

        cosmos_connector.upsert_item(DATABASE_NAME, CONTAINER_NAME, chat_document)
        return {"success": True, "answer": answ, "session_id": session_id, "messages": chat_document["messages"]}
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
    
@app.post("/update_profile")
def update_profile(data: ProfileUpdateRequest, current_user: str = Depends(get_current_user)):
    try:
        # Usiamo direttamente 'current_user' (che contiene lo user_id validato dal JWT)
        user_id = current_user
        
        # Recuperiamo il documento dell'utente dal container degli utenti
        user_document = cosmos_connector.get_item(
            database_name=DATABASE_NAME,
            container_name=USER_CONTAINER_NAME,
            item_id=user_id,
            partition_key=user_id
        )
        
        # Aggiorniamo il campo dei film preferiti
        user_document["favorite_movies"] = data.favorite_movies
        user_document["updatedAt"] = datetime.utcnow().isoformat() + "Z"
        
        # Salviamo nuovamente su Cosmos DB
        cosmos_connector.upsert_item(
            database_name=DATABASE_NAME,
            container_name=USER_CONTAINER_NAME,
            item=user_document
        )
        return {"success": True, "message": "Profilo aggiornato con successo"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/get_profile")
def get_profile(current_user: str = Depends(get_current_user)):
    try:
        user_id = current_user
        
        user_document = cosmos_connector.get_item(
            database_name=DATABASE_NAME,
            container_name=USER_CONTAINER_NAME,
            item_id=user_id,
            partition_key=user_id
        )
        
        fav_movies = user_document.get("favorite_movies", [])
        
        return {
            "success": True, 
            "favorite_movies": fav_movies
        } # errore e nel caso restituisco una lista vuota
    except Exception as e:
        return {
            "success": False, 
            "favorite_movies": [], 
            "error": str(e)
        }

if __name__ == "__main__":
    uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True)