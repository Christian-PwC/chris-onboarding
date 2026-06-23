import streamlit as st
import requests

st.set_page_config(layout="wide")
st.title("OnBoarding ChatBot")

BASE_URL = "http://127.0.0.1:8080"

if "access_token" not in st.session_state:
    st.session_state.access_token = None
if "user_id" not in st.session_state:
    st.session_state.user_id = None 
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None    # nessuna chat selezionata
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []           # messaggi chat corrente

# Se l'utente non è loggato, mostra la schermata di Login / Registrazione
if st.session_state.access_token is None:
    # Creiamo due tab: uno per il Login e uno per la Registrazione
    tab_login, tab_register = st.tabs(["🔐 Accedi", "📝 Registrati"])
    
    with tab_login:
        st.subheader("Login Accesso Piattaforma")
        with st.form("login_form"):
            username_input = st.text_input("User ID")
            password_input = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Accedi")
            
            if submit_login:
                if username_input and password_input:
                    try:
                        login_res = requests.post(f"{BASE_URL}/login", json={"user_id": username_input, "password": password_input})
                        if login_res.status_code == 200:
                            login_data = login_res.json()
                            if login_data.get("success"):
                                st.session_state.access_token = login_data["access_token"]
                                st.session_state.user_id = login_data["user_id"]
                                st.success("Login effettuato con successo!")
                                st.rerun()
                            else:
                                st.error(f"Errore: {login_data.get('error')}")
                        else:
                            st.error("Credenziali non valide o errore di comunicazione.")
                    except Exception as e:
                        st.error(f"Impossibile connettersi al server: {e}")
                else:
                    st.warning("Inserisci sia lo User ID che la password.")
                    
    with tab_register:
        st.subheader("Crea un nuovo account")
        with st.form("register_form"):
            new_username = st.text_input("Scegli un User ID (es. mario_rossi)")
            new_password = st.text_input("Scegli una Password", type="password")
            confirm_password = st.text_input("Conferma Password", type="password")
            submit_register = st.form_submit_button("Registrati")
            
            if submit_register:
                if new_username and new_password and confirm_password:
                    if new_password != confirm_password:
                        st.error("Le password non coincidono.")
                    else:
                        try:
                            # Chiamata al nuovo endpoint di registrazione del backend
                            reg_res = requests.post(
                                f"{BASE_URL}/register", 
                                json={"user_id": new_username, "password": new_password}
                            )
                            if reg_res.status_code == 200:
                                reg_data = reg_res.json()
                                if reg_data.get("success"):
                                    st.success("Registrazione completata! Ora puoi accedere dal tab 'Accedi'.")
                                else:
                                    st.error(f"Errore: {reg_data.get('error')}")
                            else:
                                st.error("Errore durante la registrazione sul server.")
                        except Exception as e:
                            st.error(f"Impossibile connettersi al server: {e}")
                else:
                    st.warning("Compila tutti i campi del modulo.")
                    
    st.stop() # Interrompe l'esecuzione del resto della pagina se non loggato

# Configurazione header di sicurezza per tutte le richieste protette
auth_headers = {"Authorization": f"Bearer {st.session_state.access_token}"}

# Pulsante di Logout inserito in alto a destra
if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.access_token = None
    st.session_state.user_id = None
    st.session_state.current_session_id = None
    st.session_state.chat_messages = []
    st.rerun()

# --- BLOCCO LOGICA ORIGINALE CHAT ---
# [Il resto del tuo codice frontend Streamlit rimane esattamente identico a prima]
with st.sidebar:
    st.header(f"Utente: {st.session_state.user_id}")
    if st.button("Nuova Chat", use_container_width=True):
        st.session_state.current_session_id = None
        st.session_state.chat_messages = []
        st.rerun()
    st.write("---")
    st.subheader("Le tue conversazioni:")
    try:
        hist_response = requests.get(f"{BASE_URL}/history/{st.session_state.user_id}", headers=auth_headers)
        if hist_response.status_code == 200 and hist_response.json()["success"]:
            history = hist_response.json()["history"]
            for chat in history:
                if st.button(chat["title"], key=chat["id"], use_container_width=True):
                    st.session_state.current_session_id = chat["id"]
                    msg_res = requests.get(f"{BASE_URL}/chat/{st.session_state.user_id}/{chat['id']}", headers=auth_headers) # richiesta al backend che mi ridà i mess della vecchia chat
                    if msg_res.status_code == 200 and msg_res.json()["success"]:
                        st.session_state.chat_messages = msg_res.json()["messages"]
                    st.rerun()
        else:
            st.caption("Nessuna cronologia trouvata.")
    except Exception:
        st.error("Errore di connessione per la cronologia.")

if st.session_state.chat_messages:
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

user_question = st.chat_input("Inserisci la tua domanda...")
if user_question:
    st.chat_message("user").write(user_question)
    payload = {
        "user_id": st.session_state.user_id,
        "session_id": st.session_state.current_session_id,
        "question": user_question
    }
    with st.spinner("Il modello sta rispondendo..."):
        try:
            response = requests.post(f"{BASE_URL}/ask", json=payload, headers=auth_headers)
            if response.status_code == 200:
                data = response.json()
                if data["success"]:
                    st.chat_message("assistant").write(data["answer"])                    
                    st.session_state.current_session_id = data["session_id"]
                    st.session_state.chat_messages = data["messages"]                    
                    st.rerun()
                else:
                    st.error(f"Errore: {data['error']}")
            else:
                st.error(f"Errore server: {response.status_code}")
        except requests.exceptions.ConnectionError:
            st.error("Impossibile raggiungere il backend FastAPI.")