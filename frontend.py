import streamlit as st
import requests

st.title("Interfaccia AI con FastAPI")

# Riquadro di input per l'utente
user_question = st.text_input("Inserisci la tua domanda:", value="Ciao, come stai?")

# URL dell'endpoint di FastAPI
FASTAPI_URL = "http://127.0.0.1:8080/ask"

if st.button("Invia domanda"):
    if user_question:
        with st.spinner("Il modello sta rispondendo..."):
            try:
                payload = {"question": user_question}                
                response = requests.post(FASTAPI_URL, json=payload)
                
                if response.status_code == 200:
                    data = response.json()
                    if data["success"]:
                        st.subheader("Risposta del modello:")
                        st.info(data["answer"])
                    else:
                        st.error(f"Errore del modello: {data['error']}")
                else:
                    st.error(f"Errore di comunicazione con il server: {response.status_code}")
                    
            except requests.exceptions.ConnectionError:
                st.error("Impossibile raggiungere il backend FastAPI.")
    else:
        st.warning("Inserisci una domanda prima di premere il pulsante.")