from fastapi import FastAPI
from src.services.openai_connector import openai_connector 
from src.services.cosmos_connector import cosmos_connector  # Il tuo connettore Cosmos
from pydantic import BaseModel
from datetime import datetime
import uuid
from src.models.schemas import ChatRequest

app = FastAPI()

DATABASE_NAME = "users"
CONTAINER_NAME = "users_chat"

@app.post("/ask")
def ask_model(data: ChatRequest):
    try:
        user_id = data.user_id
        session_id = data.session_id
        
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
            # Se il ruolo è user usa 'input_text', se è assistant usa 'output_text'
            content_type = "input_text" if msg["role"] == "user" else "output_text"
            
            history_for_openai.append({
                "role": msg["role"],
                "content": [
                    {
                        "type": content_type,
                        "text": msg["content"]
                    }
                ]
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
            "messages": chat_document["messages"] # Opzionale: restituisce tutta la cronologia al front
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

# Nuovo endpoint per caricare la cronologia nella sidebar di Streamlit
@app.get("/history/{user_id}")
def get_user_history(user_id: str):
    try:
        # Recuperiamo solo id e titolo ordinati per data
        query = "SELECT c.id, c.title FROM c WHERE c.user_id = @userId ORDER BY c.updatedAt DESC"
        parameters = [{"name": "@userId", "value": user_id}]
        
        lista_chat = cosmos_connector.query_items(
            database_name=DATABASE_NAME,
            container_name=CONTAINER_NAME,
            query=query,
            parameters=parameters,
            enable_cross_partition_query=False
        )
        return {"success": True, "history": lista_chat}
    except Exception as e:
        return {"success": False, "error": str(e)}

# Nuovo endpoint per recuperare i messaggi di una chat specifica quando ci clicchi sopra
@app.get("/chat/{user_id}/{session_id}")
def get_chat_messages(user_id: str, session_id: str):
    try:
        chat = cosmos_connector.get_item(DATABASE_NAME, CONTAINER_NAME, session_id, user_id)
        return {"success": True, "messages": chat.get("messages", [])}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="127.0.0.1", port=8080, reload=True)