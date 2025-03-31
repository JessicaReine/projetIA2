import face_recognition
import numpy as np
import pickle
from typing import List, Dict, Optional

def extract_face_encodings(image: np.ndarray) -> List[np.ndarray]:
    """Extrait les encodages faciaux d'une image"""
    if len(image.shape) == 3 and image.shape[2] == 4:
        image = image[:, :, :3]
    return face_recognition.face_encodings(image)

def compare_faces(known_face_encodings: List[np.ndarray], face_encoding_to_check: np.ndarray, threshold: float = 0.6) -> List[bool]:
    """Compare une encodage facial avec une liste d'encodages connus"""
    distances = face_recognition.face_distance(known_face_encodings, face_encoding_to_check)
    return [distance <= threshold for distance in distances]

def register_face(image: np.ndarray, username: str, email: str, password: Optional[str] = None) -> Dict:
    """Enregistre un nouveau visage dans la base de données"""
    try:
        face_encodings = extract_face_encodings(image)
        if not face_encodings:
            return {"success": False, "message": "Aucun visage détecté"}
        
        face_encoding = face_encodings[0]
        serialized_encoding = pickle.dumps(face_encoding)
        
        from database import add_user
        if not add_user(username, email, password, serialized_encoding):
            return {"success": False, "message": "L'utilisateur existe déjà"}
            
        return {"success": True, "message": "Visage enregistré avec succès"}
    except Exception as e:
        return {"success": False, "message": f"Erreur: {str(e)}"}

def recognize_face(image: np.ndarray) -> Dict:
    """Reconnaît un visage à partir de l'image"""
    try:
        from database import get_all_users
        users = get_all_users()
        
        if not users:
            return {"success": False, "message": "Aucun utilisateur enregistré"}
        
        face_encodings = extract_face_encodings(image)
        if not face_encodings:
            return {"success": False, "message": "Aucun visage détecté"}
        
        captured_encoding = face_encodings[0]
        known_encodings = []
        user_data = []
        
        for user in users:
            if user['face_encoding']:
                known_encodings.append(pickle.loads(user['face_encoding']))
                user_data.append({
                    "username": user['username'],
                    "email": user['email']
                })
        
        if not known_encodings:
            return {"success": False, "message": "Aucune signature faciale enregistrée"}
        
        matches = compare_faces(known_encodings, captured_encoding)
        if any(matches):
            match_index = matches.index(True)
            distance = face_recognition.face_distance([known_encodings[match_index]], captured_encoding)[0]
            return {
                "success": True,
                "username": user_data[match_index]['username'],
                "email": user_data[match_index]['email'],
                "confidence": float(1 - distance)
            }
        else:
            return {"success": False, "message": "Aucune correspondance trouvée"}
    except Exception as e:
        return {"success": False, "message": f"Erreur: {str(e)}"}