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
    st.session_state.current_session_id = None    
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []           
if "system_prompt" not in st.session_state:        
    st.session_state.system_prompt = ""

# Schermata Login / Registrazione
if st.session_state.access_token is None:
    tab_login, tab_register = st.tabs(["🔐 Accedi", "📝 Registrati"])
    
    with tab_login:
        st.subheader("Login")
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
                                
                                headers_profilo = {"Authorization": f"Bearer {login_data['access_token']}"}
                                try:
                                    res_profile = requests.get(f"{BASE_URL}/get_profile", headers=headers_profilo)
                                    if res_profile.status_code == 200:
                                        profile_data = res_profile.json()
                                        lista_film = profile_data.get("favorite_movies", [])
                                        # Trasformiamo la lista in stringa separata da virgole per darla in pasto all'input
                                        st.session_state.input_film_preferiti = ", ".join(lista_film)
                                    else:
                                        st.session_state.input_film_preferiti = ""
                                except Exception:
                                    st.session_state.input_film_preferiti = ""

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
                    
    st.stop()

auth_headers = {"Authorization": f"Bearer {st.session_state.access_token}"}

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.access_token = None
    st.session_state.user_id = None
    st.session_state.current_session_id = None
    st.session_state.chat_messages = []
    st.session_state.system_prompt = ""
    st.rerun()

# --- LOGICA SIDEBAR CHAT E PROMPT ---
with st.sidebar:
    st.header(f"Utente: {st.session_state.user_id}")
    if st.button("Nuova Chat", use_container_width=True):
        st.session_state.current_session_id = None
        st.session_state.chat_messages = []
        st.session_state.system_prompt = ""        # <-- RESETTA IL PROMPT SUL NUOVO AVVIO CHAT
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
                    msg_res = requests.get(f"{BASE_URL}/chat/{st.session_state.user_id}/{chat['id']}", headers=auth_headers) 
                    if msg_res.status_code == 200 and msg_res.json()["success"]:
                        st.session_state.chat_messages = msg_res.json()["messages"]
                        # <-- AGGIUNTO: Carica il system prompt associato alla chat selezionata
                        st.session_state.system_prompt = msg_res.json().get("system_prompt", "")
                    st.rerun()
        else:
            st.caption("Nessuna cronologia trovata.")
    except Exception:
        st.error("Errore di connessione per la cronologia.")

    st.write("---")

    st.subheader("⚙️ Impostazioni")
    st.session_state.system_prompt = st.text_area(
        label="System Prompt",
        value=st.session_state.system_prompt,
        placeholder="Es: Sei un chatbot che sa tutto di cinema e dà consigli cinematografici. Non essere troppo prolisso ma neanche troppo coinciso...",
        help="Questo testo istruisce il modello sul comportamento da adottare nella conversazione.",
        height=120
    )
    

# Visualizzazione dei messaggi
if st.session_state.chat_messages:
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])
        else:
            st.chat_message("assistant").write(msg["content"])

# 1. Definisci il toggle assegnandogli una 'key' univoca
st.sidebar.toggle("🌐 Programmazione in sala", key="web_search_toggle")

user_question = st.chat_input("Inserisci la tua domanda...")
if user_question:
    st.chat_message("user").write(user_question)
    
    # 2. Recupera il valore direttamente dal session_state per essere sicuri al 100%
    stato_web = st.session_state.web_search_toggle
    
    # Costruzione del payload con il flag stabile
    payload = {
        "user_id": st.session_state.user_id,
        "session_id": st.session_state.current_session_id,
        "question": user_question,
        "system_prompt": st.session_state.system_prompt,
        "web_search": stato_web  # <-- Passiamo il valore estratto dal session_state
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

st.write("---")
if "input_film_preferiti" not in st.session_state:
    st.session_state.input_film_preferiti = ""

with st.expander("Modifica Profilo"):
    
    if st.session_state.input_film_preferiti:
        st.info(f"**Film attualmente salvati:** {st.session_state.input_film_preferiti}")
    else:
        st.info("Non hai ancora salvato nessun film preferito.")

    film_input = st.text_input(
        label="Modifica i tuoi film preferiti (separati da virgola):",
        value=st.session_state.input_film_preferiti,
        placeholder="Es: Matrix, Inception, Interstellar",
        help="L'AI userà questa lista per conoscerti meglio e personalizzare le risposte."
    )

    if st.button("Salva Modifiche", use_container_width=True):
        if film_input:
            lista_film = [f.strip() for f in film_input.split(",") if f.strip()]
            
            # Mandiamo l'array dei film preferiti al backend
            payload_profilo = {
                "favorite_movies": lista_film
            }
            
            try:
                res_profilo = requests.post(f"{BASE_URL}/update_profile", json=payload_profilo, headers=auth_headers)
                if res_profilo.status_code == 200 and res_profilo.json().get("success"):
                    st.session_state.input_film_preferiti = film_input
                    st.success("Preferenze salvate nel tuo profilo!")
                    st.rerun() 
                else:
                    st.error(f"Errore durante il salvataggio: {res_profilo.json().get('error')}")
            except Exception as e:
                st.error(f"Impossibile connettersi al server: {e}")
        else:
            st.warning("Inserisci almeno un film prima di salvare.")