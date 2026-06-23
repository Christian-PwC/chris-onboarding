import uuid
from datetime import datetime
from azure.cosmos import exceptions
from src.services.cosmos_connector import cosmos_connector 

DATABASE_NAME = "users"      
CONTAINER_NAME = "users_chat"

def run_test():
    print("--- 🚀 Inizio Test con CosmosConnector ---")
    session_id = str(uuid.uuid4())
    user_id = "utente_mario_123" # Questa sarà la nostra Partition Key
    
    chat_document = {
        "id": session_id,          # ID univoco della chat
        "user_id": user_id,         # Partition Key
        "title": "Discussione su Architettura Cosmos",
        "messages": [
            {"role": "user", "content": "Il mio connettore Cosmos funziona?"},
            {"role": "assistant", "content": "Sì, la struttura della classe è ottima!"}
        ]
    }

    sql_query = "SELECT * FROM c WHERE c.user_id = @userId ORDER BY c.updatedAt DESC"

    # 2. Prepariamo i parametri nel formato richiesto da Azure Cosmos DB
    query_parameters = [
        {
            "name": "@userId", 
            "value": user_id
        }
    ]

    # 3. Eseguiamo la query usando il TUO metodo
    # Impostiamo enable_cross_partition_query=False perché stiamo filtrando 
    # sulla Partition Key (userId), rendendo la query super efficiente ed economica!
    lista_chat = cosmos_connector.query_items(
        database_name=DATABASE_NAME,
        container_name=CONTAINER_NAME,
        query=sql_query,
        parameters=query_parameters,
        enable_cross_partition_query=False  # <--- Ottimizzazione cruciale!
    )
    
    # 4. Leggiamo i risultati
    print(f"Trovate {len(lista_chat)} chat per questo utente:\n")
    for chat in lista_chat:
        print(f"📌 ID Chat: {chat['id']}")
        print(f"   Titolo:  {chat['title']}")
        print(f"   Messaggi totali: {len(chat['messages'])}")
        print("-" * 30)
        
       

if __name__ == "__main__":
    run_test()