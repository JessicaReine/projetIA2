import sqlite3
import os
import pickle
import hashlib
from typing import Optional, Dict, List

DB_PATH = os.path.join(os.path.dirname(__file__), "users.db")

def get_db_connection():
    """Crée une connexion à la base de données"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_database():
    """Initialise la base de données avec les tables nécessaires"""
    conn = get_db_connection()
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT,
            face_encoding BLOB,
            auth_provider TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        conn.commit()
    finally:
        conn.close()

def add_user(username: str, email: str, password: Optional[str], 
             face_encoding: Optional[bytes], auth_provider: Optional[str] = None) -> bool:
    """Ajoute un nouvel utilisateur à la base de données"""
    conn = get_db_connection()
    try:
        hashed_password = hash_password(password) if password else None
        conn.execute("""
        INSERT INTO users (username, email, password, face_encoding, auth_provider)
        VALUES (?, ?, ?, ?, ?)
        """, (username, email, hashed_password, face_encoding, auth_provider))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_username(username: str) -> Optional[Dict]:
    """Récupère un utilisateur par son nom d'utilisateur"""
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def get_user_by_email(email: str) -> Optional[Dict]:
    """Récupère un utilisateur par son email"""
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(user) if user else None
    finally:
        conn.close()

def get_all_users() -> List[Dict]:
    """Récupère tous les utilisateurs"""
    conn = get_db_connection()
    try:
        users = conn.execute("SELECT * FROM users").fetchall()
        return [dict(user) for user in users]
    finally:
        conn.close()

def update_face_encoding(username: str, face_encoding: bytes) -> bool:
    """Met à jour l'encodage facial d'un utilisateur"""
    conn = get_db_connection()
    try:
        conn.execute("""
        UPDATE users SET face_encoding = ? WHERE username = ?
        """, (face_encoding, username))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()

def hash_password(password: str) -> str:
    """Hache un mot de passe avec SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(hashed_password: str, password: str) -> bool:
    """Vérifie si le mot de passe correspond au hash"""
    return hashed_password == hash_password(password)

# Initialisation de la base de données
if __name__ == "__main__":
    initialize_database()