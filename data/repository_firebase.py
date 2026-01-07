from .firebase_connection import db
from google.cloud import firestore

_emit_callback = None

def set_emit_callback(fn):
    global _emit_callback
    _emit_callback = fn

def _maybe_emit(name, payload):
    if _emit_callback:
        try:
            _emit_callback(name, payload)
        except Exception as e:
            print("⚠️ Error al emitir evento:", e)

# === Usuarios ===
def register_user(telegram_id, username, full_name, dni, phone_number):
    ref = db.collection("users").document(str(telegram_id))
    ref.set({
        "telegram_id": telegram_id,
        "username": username,
        "full_name": full_name,
        "dni": dni,
        "phone_number": phone_number
    }, merge=True)
    print(f"✅ Usuario {full_name or username} registrado correctamente.")

def get_user(telegram_id):
    doc = db.collection("users").document(str(telegram_id)).get()
    return doc.to_dict() if doc.exists else None


# === Incidentes ===
def create_incident(user_id, username, message, address, lat, lon, category):
    user_doc = db.collection("users").document(str(user_id)).get()
    user = user_doc.to_dict() if user_doc.exists else {}

    incident_ref = db.collection("incidents").document()
    incident_data = {
        "id": incident_ref.id,
        "user_id": user_id,
        "username": username,
        "message": message,
        "address": address,
        "lat": lat,
        "lon": lon,
        "category": category,
        "status": "open",
        "response": "",
        "created_at": firestore.SERVER_TIMESTAMP,
        "reporter_name": user.get("full_name", username),
        "reporter_dni": user.get("dni"),
        "reporter_phone": user.get("phone_number")
    }

    incident_ref.set(incident_data)
    _maybe_emit("new_incident", incident_data)
    print(f"🚨 Nuevo incidente registrado por {username}: {category}")
    return incident_data

# Alias para compatibilidad
register_incident = create_incident


def get_all_incidents():
    docs = db.collection("incidents").order_by("created_at", direction=firestore.Query.DESCENDING).stream()
    return [d.to_dict() for d in docs]


def update_incident_status(incident_id, status):
    ref = db.collection("incidents").document(str(incident_id))
    ref.update({"status": status})
    doc = ref.get()
    incident = doc.to_dict()
    _maybe_emit("update_incident", incident)
    return incident


def set_incident_response(incident_id, message):
    ref = db.collection("incidents").document(str(incident_id))
    ref.update({"response": message})
    doc = ref.get()
    incident = doc.to_dict()
    _maybe_emit("update_incident", incident)
    return incident


# === Feedback ===
def save_feedback(user_id, incident_id, rating=None, comment=None):
    ref = db.collection("feedback").document(str(incident_id))
    data = {
        "user_id": user_id,
        "incident_id": incident_id,
        "created_at": firestore.SERVER_TIMESTAMP
    }
    if rating is not None:
        data["rating"] = rating
    if comment is not None:
        data["comment"] = comment

    ref.set(data, merge=True)
    fb = ref.get().to_dict()
    _maybe_emit("new_feedback", fb)
    print(f"💬 Feedback guardado correctamente: incidente={incident_id}, rating={rating}")
    return fb
