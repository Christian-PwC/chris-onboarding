# src/routers/chat.py
from fastapi import APIRouter, Depends, HTTPException
import uuid
import requests
from bs4 import BeautifulSoup
from src.models.schemas import ChatRequest
from src.dependencies.auth import get_current_user
from src.services.openai_connector import openai_connector 
from src.services.cosmos_connector import cosmos_connector  

DATABASE_NAME = "users"
CONTAINER_NAME = "users_chat"
USER_CONTAINER_NAME = "users_list"  
URL_FISSO = "https://www.mymovies.it/cinema/milano/"

headers_browser = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

router = APIRouter(
    tags=["Chat"]
)

@router.post("/ask")
def ask_model(data: ChatRequest, current_user: str = Depends(get_current_user)):
    try:
        user_id = current_user
        session_id = data.session_id
        
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

        prompt_di_sistema_finale = (chat_document.get("system_prompt") or "") + contesto_preferiti
        
        if data.web_search:
            try:
                res_web = requests.get(URL_FISSO, timeout=15, headers=headers_browser)
                if res_web.status_code == 200:
                    soup = BeautifulSoup(res_web.text, 'html.parser')
                    for script in soup(["script", "style"]):
                        script.extract()
                    testo_pulito = soup.get_text(separator=" ", strip=True)[:4000]
                    
                    contesto_web = f"\n\n[CONTESTO AGGIUNTIVO DAL SITO {URL_FISSO}]:\n{testo_pulito}\n"
                    prompt_di_sistema_finale += contesto_web
            except Exception as e:
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


@router.get("/history/{user_id}")
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


@router.get("/chat/{user_id}/{session_id}")
def get_chat_messages(user_id: str, session_id: str, current_user: str = Depends(get_current_user)):
    try:
        if user_id != current_user:
            raise HTTPException(status_code=403, detail="Accesso negato")
        chat = cosmos_connector.get_item(DATABASE_NAME, CONTAINER_NAME, session_id, user_id)
        return {
            "success": True, 
            "messages": chat.get("messages", []),
            "system_prompt": chat.get("system_prompt", "") 
        }
    except HTTPException as http_ex:
        raise http_ex
    except Exception as e:
        return {"success": False, "error": str(e)}