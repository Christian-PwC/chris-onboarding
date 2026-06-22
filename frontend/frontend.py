import streamlit as st
import requests

st.title("Interfaccia AI con FastAPI")

user_question = st.text_input("Inserisci la tua domanda:", value="Ciao, come stai?")
FASTAPI_URL = "http://127.0.0.1:8080/ask"

if st.button("Invia domanda"):
    if user_question:
        with st.spinner("Il modello sta rispondendo..."):
            try:
                payload = {"question": user_question}                
                response = requests.post(FASTAPI_URL, json=payload) #response sarebbe quello che mi ridò da app.py
                
                if response.status_code == 200:
                    data = response.json() #lo trasforma da json a dict
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