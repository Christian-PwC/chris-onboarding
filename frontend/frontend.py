import streamlit as st
import requests

st.set_page_config(layout="wide")
st.title("Interfaccia AI con Memoria (FastAPI + Cosmos DB)")

BASE_URL = "http://127.0.0.1:8080"

# 1. GESTIONE STATO DI STREAMLIT (Inizializzazione variabili)
if "user_id" not in st.session_state:
    st.session_state.user_id = "utente_mario_123" # Simuliamo un utente loggato
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None    # Nessuna chat selezionata (Nuova Chat)
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []           # Messaggi della chat corrente

# 2. BARRA LATERALE (SIDEBAR) - Cronologia Chat
with st.sidebar:
    st.header(f"Utente: {st.session_state.user_id}")
    
    # Pulsante per resettare e iniziare una nuova chat
    if st.button("➕ Nuova Chat", use_container_width=True):
        st.session_state.current_session_id = None
        st.session_state.chat_messages = []
        st.rerun()
        
    st.write("---")
    st.subheader("Le tue conversazioni:")
    
    # Recuperiamo la cronologia dal backend
    try:
        hist_response = requests.get(f"{BASE_URL}/history/{st.session_state.user_id}")
        if hist_response.status_code == 200 and hist_response.json()["success"]:
            history = hist_response.json()["history"]
            
            # Creiamo un pulsante nella sidebar per ogni vecchia chat
            for chat in history:
                if st.button(chat["title"], key=chat["id"], use_container_width=True):
                    # Se l'utente clicca una vecchia chat, aggiorna lo stato e carica i messaggi
                    st.session_state.current_session_id = chat["id"]
                    msg_res = requests.get(f"{BASE_URL}/chat/{st.session_state.user_id}/{chat['id']}")
                    if msg_res.status_code == 200 and msg_res.json()["success"]:
                        st.session_state.chat_messages = msg_res.json()["messages"]
                    st.rerun()
        else:
            st.caption("Nessuna cronologia trovata.")
    except Exception:
        st.error("Errore di connessione per la cronologia.")

# 3. AREA PRINCIPALE DELLA CHAT
# Mostra i messaggi passati se ci sono
if st.session_state.chat_messages:
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

# Input per la nuova domanda (usando il widget nativo di chat di Streamlit)
user_question = st.chat_input("Inserisci la tua domanda...")

if user_question:
    # Mostra immediatamente il messaggio inserito dall'utente a schermo
    st.chat_message("user").write(user_question)
    
    # Prepara la richiesta per FastAPI
    payload = {
        "user_id": st.session_state.user_id,
        "session_id": st.session_state.current_session_id, # Può essere None
        "question": user_question
    }
    
    with st.spinner("Il modello sta rispondendo..."):
        try:
            response = requests.post(f"{BASE_URL}/ask", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    # Mostra la risposta dell'IA
                    st.chat_message("assistant").write(data["answer"])
                    
                    # Aggiorna lo stato della sessione corrente
                    st.session_state.current_session_id = data["session_id"]
                    st.session_state.chat_messages = data["messages"]
                    
                    # Forza il rinfresco della pagina per aggiornare la sidebar con il nuovo titolo
                    st.rerun()
                else:
                    st.error(f"Errore: {data['error']}")
            else:
                st.error(f"Errore server: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            st.error("Impossibile raggiungere il backend FastAPI.")