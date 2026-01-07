# data/firebase_connect.py
import os, json
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# Cargar variables .env
load_dotenv()

firebase_key_str = os.getenv("FIREBASE_KEY")
if not firebase_key_str:
    raise Exception("⚠️ No se encontró FIREBASE_KEY en el archivo .env")

# Convertir el JSON en string → dict
firebase_key_dict = json.loads(firebase_key_str)

# Inicializar Firebase (solo una vez)
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_key_dict)
    firebase_admin.initialize_app(cred)

# Cliente de Firestore
db = firestore.client()

# Test rápido opcional
def test_firebase():
    try:
        doc = {"test": "ok"}
        db.collection("test_connection").add(doc)
        print("✅ Firebase conectado correctamente.")
    except Exception as e:
        print("❌ Error conectando a Firebase:", e)

if __name__ == "__main__":
    test_firebase()
