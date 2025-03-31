import streamlit as st
import numpy as np
from PIL import Image
from database import initialize_database, add_user, get_user_by_username, hash_password, verify_password
from utils.face_recognition import register_face, recognize_face
import requests
from authlib.integrations.requests_client import OAuth2Session
from urllib.parse import urlencode
import sqlite3

# Initialisation de la base de données
initialize_database()

# Configuration de la page
st.set_page_config(page_title="Authentification IA", page_icon="🔒", layout="wide")

# Configuration Google
GOOGLE_CLIENT_ID = st.secrets["google"]["client_id"]
GOOGLE_CLIENT_SECRET = st.secrets["google"]["client_secret"]
GOOGLE_REDIRECT_URI = st.secrets["google"]["redirect_uri"]

# Style CSS personnalisé
st.markdown("""
    <style>
    body {
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, #ff9a9e, #fad0c4);
        margin: 0;
        padding: 0;
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
    }

    .main {
        max-width: 800px;
        padding: 2rem;
        background: #ffffff;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0, 0, 0, 0.2);
        text-align: center;
        animation: fadeIn 1s ease-in-out;
    }

    .stButton>button {
        width: 100%;
        border-radius: 12px;
        padding: 0.8rem;
        background: linear-gradient(45deg, #ff758c, #ff7eb3);
        color: white;
        font-size: 1rem;
        font-weight: bold;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease-in-out;
    }

    .stButton>button:hover {
        background: linear-gradient(45deg, #ff5e78, #ff85a1);
        transform: scale(1.05);
        box-shadow: 0 4px 10px rgba(255, 94, 120, 0.3);
    }

    .stTextInput>div>div>input,
    .stTextInput>div>div>input:focus {
        border-radius: 12px;
        padding: 0.8rem;
        border: 2px solid #ff758c;
        width: 100%;
        font-size: 1rem;
        transition: border-color 0.3s, box-shadow 0.3s;
    }

    .stTextInput>div>div>input:focus {
        border-color: #ff5e78;
        box-shadow: 0 0 8px rgba(255, 94, 120, 0.4);
        outline: none;
    }

    .stCameraInput>div>div {
        border-radius: 12px;
        overflow: hidden;
        border: 2px solid #ff758c;
    }

    .google-btn {
        display: flex;
        justify-content: center;
        align-items: center;
        background: linear-gradient(45deg, #42a5f5, #478ed1);
        color: white;
        font-weight: bold;
        border-radius: 12px;
        padding: 0.8rem;
        margin: 1rem 0;
        font-size: 1rem;
        cursor: pointer;
        transition: all 0.3s ease-in-out;
    }

    .google-btn:hover {
        background: linear-gradient(45deg, #1e88e5, #1565c0);
        transform: scale(1.05);
        box-shadow: 0 4px 10px rgba(66, 165, 245, 0.3);
    }

    @keyframes fadeIn {
        from {
            opacity: 0;
            transform: translateY(-10px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
</style>

""", unsafe_allow_html=True)

# Gestion de l'état de session
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'user_email' not in st.session_state:
    st.session_state.user_email = None
if 'user_info' not in st.session_state:
    st.session_state.user_info = {}

# Fonctions pour l'authentification Google
def get_google_auth_url():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

def exchange_google_code(code):
    client = OAuth2Session(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET)
    token = client.fetch_token(
        "https://oauth2.googleapis.com/token",
        code=code,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )
    return token

def get_google_user_info(token):
    response = requests.get(
        "https://www.googleapis.com/oauth2/v1/userinfo",
        headers={"Authorization": f"Bearer {token}"},
    )
    return response.json()

def handle_google_auth():
    query_params = st.query_params
    if 'code' in query_params:
        try:
            code = query_params['code']
            token = exchange_google_code(code)
            user_info = get_google_user_info(token["access_token"])
            
            email = user_info["email"]
            name = user_info.get("family_name", "")
            first_name = user_info.get("given_name", "")
            
            if not get_user_by_username(email):
                add_social_user(name, first_name, email, "google")
            
            st.session_state.authenticated = True
            st.session_state.username = email
            st.session_state.user_email = email
            st.session_state.user_info = {
                "first_name": first_name,
                "name": name,
                "email": email
            }
            
            st.query_params.clear()
            st.rerun()
            
        except Exception as e:
            st.error(f"Erreur de connexion Google: {str(e)}")

# Pages de l'application
def home_page():
    st.title("Bienvenue dans l'application d'authentification IA")
    st.write("""
    Cette application propose plusieurs méthodes d'authentification sécurisées.
    """)

    if st.session_state.authenticated:
        user_info = st.session_state.user_info
        display_name = f"{user_info.get('first_name', '')} {user_info.get('name', '')}" if user_info.get('first_name') else st.session_state.username
        st.success(f"Vous êtes connecté en tant que {display_name}")
        if st.button("Déconnexion", type="primary"):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.user_email = None
            st.session_state.user_info = {}
            st.rerun()

def register_page():
    st.title("Inscription")
    
    with st.form("register_form"):
        username = st.text_input("Nom d'utilisateur", placeholder="Entrez votre nom d'utilisateur")
        email = st.text_input("Email", placeholder="Entrez votre email")
        password = st.text_input("Mot de passe", type="password", placeholder="Créez un mot de passe")
        confirm_password = st.text_input("Confirmer le mot de passe", type="password", placeholder="Confirmez votre mot de passe")
        
        st.subheader("Enregistrement facial (optionnel)")
        img_file_buffer = st.camera_input("Prendre une photo pour l'enregistrement facial", label_visibility="hidden")
        
        submitted = st.form_submit_button("S'inscrire", type="primary")
        
        if submitted:
            if password != confirm_password:
                st.error("Les mots de passe ne correspondent pas")
                return
                
            if get_user_by_username(username):
                st.error("Ce nom d'utilisateur est déjà pris")
                return
                
            face_encoding = None
            if img_file_buffer is not None:
                image = Image.open(img_file_buffer)
                image_np = np.array(image)
                result = register_face(image_np, username, email, password)
                if not result['success']:
                    st.warning(result['message'])
            else:
                hashed_password = hash_password(password)
                if not add_user(username, email, hashed_password, None):
                    st.error("Erreur lors de l'inscription")
                else:
                    st.success("Inscription réussie! Vous pouvez maintenant vous connecter.")
                    st.rerun()

def login_page():
    st.title("Connexion")
    handle_google_auth()
    
    tab1, tab2, tab3 = st.tabs(["Nom d'utilisateur/Mot de passe", "Reconnaissance faciale", "Google"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Nom d'utilisateur", placeholder="Entrez votre nom d'utilisateur")
            password = st.text_input("Mot de passe", type="password", placeholder="Entrez votre mot de passe")
            submitted = st.form_submit_button("Se connecter", type="primary")
            
            if submitted:
                user = get_user_by_username(username)
                if user and verify_password(user['password'], password):
                    st.session_state.authenticated = True
                    st.session_state.username = user['username']
                    st.session_state.user_email = user['email']
                    st.session_state.user_info = {
                        "first_name": user.get('first_name', ''),
                        "name": user.get('name', ''),
                        "email": user['email']
                    }
                    st.success("Connexion réussie!")
                    st.rerun()
                else:
                    st.error("Nom d'utilisateur ou mot de passe incorrect")
    
    with tab2:
        st.write("Connectez-vous en utilisant la reconnaissance faciale")
        img_file_buffer = st.camera_input("Prendre une photo pour la reconnaissance faciale", label_visibility="hidden")
        
        if img_file_buffer is not None:
            image = Image.open(img_file_buffer)
            image_np = np.array(image)
            result = recognize_face(image_np)
            
            if result['success']:
                st.session_state.authenticated = True
                st.session_state.username = result['username']
                st.session_state.user_email = result['email']
                st.session_state.user_info = {
                    "first_name": result.get('first_name', ''),
                    "name": result.get('name', ''),
                    "email": result['email']
                }
                st.success(f"Reconnaissance faciale réussie! Bienvenue {result.get('first_name', '')} {result.get('name', '')}")
                st.rerun()
            else:
                st.error(result['message'])
    
    with tab3:
        st.write("Connectez-vous avec Google")
        st.markdown(f"""
        <div class="google-btn">
            <a href="{get_google_auth_url()}">
                <img src="https://developers.google.com/identity/images/btn_google_signin_dark_normal_web.png" 
                     alt="Sign in with Google" style="width: 200px;"/>
            </a>
        </div>
        """, unsafe_allow_html=True)

# Application principale
def main():
    if not st.session_state.authenticated:
        pages = {
            "Accueil": home_page,
            "Connexion": login_page,
            "Inscription": register_page
        }
        
        st.sidebar.title("Navigation")
        selection = st.sidebar.radio("Aller à", list(pages.keys()))
        pages[selection]()
    else:
        home_page()
        st.write("Vous êtes maintenant authentifié et pouvez accéder à l'application.")

if __name__ == "__main__":
    main()