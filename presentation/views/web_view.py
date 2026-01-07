# presentation/views/web_view.py

from flask import Blueprint, render_template, jsonify, request
from dotenv import load_dotenv
import os, json
from core.incident_service import mark_resolved, respond_incident
from core.geolocalizador import geocode_address
from data.repository_firebase import get_all_incidents
from core.stats_service import get_statistics
from datetime import datetime

load_dotenv()

web_bp = Blueprint("web", __name__, template_folder="../../ui/templates")

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "")
ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "vecibot_admin")

# --- 🔧 Función auxiliar ---
def clean_value(v):
    """Convierte valores no serializables (datetime, Timestamp, etc.) a string."""
    try:
        if hasattr(v, "isoformat"):
            return v.isoformat()
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        pass
    return v


def normalize_incidents():
    """
    Obtiene los incidentes desde Firebase y los normaliza
    para el mapa y panel admin, incluyendo feedback externo.
    """
    try:
        from data.repository_firebase import db  # Import aquí para evitar ciclos

        incidents_raw = get_all_incidents()
        incidents = []

        # === Cargar todos los feedbacks y convertirlos en un diccionario ===
        feedback_docs = db.collection("feedback").stream()
        feedback_map = {}
        for fb in feedback_docs:
            data = fb.to_dict()
            if not data:
                continue
            incident_id = data.get("incident_id")
            if incident_id:
                feedback_map[incident_id] = {
                    "rating": data.get("rating", 0),
                    "comment": data.get("comment", "")
                }

        for inc in incidents_raw:
            if not inc:
                continue

            lat = inc.get("lat")
            lon = inc.get("lon")

            if lat is None or lon is None:
                continue

            # --- Buscar feedback por ID ---
            fb = feedback_map.get(inc.get("id"), {})
            rating = fb.get("rating", 0)
            comment = fb.get("comment", "")

            incidents.append({
                "id": inc.get("id"),
                "user_id": inc.get("user_id"),
                "username": inc.get("username", "—"),
                "reporter_name": inc.get("reporter_name") or inc.get("username", "—"),
                "reporter_dni": inc.get("reporter_dni", "—"),
                "reporter_phone": inc.get("reporter_phone", "—"),
                "message": inc.get("message", ""),
                "category": inc.get("category", "Sin categoría"),
                "address": inc.get("address", "—"),
                "status": inc.get("status", "open"),
                "response": inc.get("response", ""),
                "lat": float(lat),
                "lon": float(lon),
                "created_at": clean_value(inc.get("created_at")),
                # ⭐ Feedback externo
                "rating": rating,
                "comment": comment,
            })

        return incidents

    except Exception as e:
        print("❌ Error al normalizar incidentes Firebase:", e)
        return []





# === 🌍 Página principal con mapa ===
@web_bp.route("/")
def index():
    incidents = normalize_incidents()
    incidents_json = json.dumps(incidents, ensure_ascii=False)
    return render_template(
        "index.html",
        INCIDENTS_JSON=incidents_json,
        MAPBOX_TOKEN=MAPBOX_TOKEN,
        ADMIN_TOKEN=ADMIN_TOKEN
    )


# === 🧰 Panel administrativo ===
@web_bp.route("/admin")
def admin():
    token = request.args.get("token", "")
    if token != ADMIN_TOKEN:
        return "⛔ Acceso denegado. Token inválido.", 403
    return render_template("admin.html", ADMIN_TOKEN=ADMIN_TOKEN)


# === 📡 API: lista de incidentes (mapa y panel) ===
@web_bp.route("/incidents")
def incidents():
    incidents = normalize_incidents()
    return jsonify(incidents)


# === 🗺️ Geocodificación ===
@web_bp.route("/geocode")
def geocode():
    q = request.args.get("q", "")
    if not q:
        return jsonify({"error": "missing query"}), 400
    result = geocode_address(q)
    if not result:
        return jsonify({"error": "not found"}), 404
    return jsonify(result)


# === ✅ Resolver incidente ===
@web_bp.route("/admin/resolve", methods=["POST"])
def resolve():
    token = request.args.get("token", "")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "invalid token"}), 403

    data = request.get_json()
    inc_id = data.get("id")
    inc = mark_resolved(inc_id)
    return jsonify(inc)


# === 💬 Responder incidente ===
@web_bp.route("/admin/respond", methods=["POST"])
def respond():
    token = request.args.get("token", "")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "invalid token"}), 403

    data = request.get_json()
    inc_id = data.get("id")
    msg = data.get("message")

    if not msg or not inc_id:
        return jsonify({"error": "missing parameters"}), 400

    inc = respond_incident(inc_id, msg)
    return jsonify(inc)


# === 📊 Página de estadísticas ===
@web_bp.route("/stats")
def stats():
    token = request.args.get("token")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "No autorizado"}), 403
    return render_template("stats.html", ADMIN_TOKEN=ADMIN_TOKEN)


# === 📈 API de estadísticas ===
@web_bp.route("/api/incidents/stats")
def api_stats():
    token = request.args.get("token")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "No autorizado"}), 403

    year = request.args.get("year")
    month = request.args.get("month")
    status = request.args.get("status")

    stats_data = get_statistics(year, month, status)
    return jsonify(stats_data)
# === 📋 API: Lista de incidentes (para stats.html) ===
@web_bp.route("/api/incidents/list")
def api_incident_list():
    token = request.args.get("token")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "No autorizado"}), 403

    from data.repository_firebase import db

    year = request.args.get("year")
    month = request.args.get("month")
    status = request.args.get("status")
    user_id = request.args.get("user")

    incidents = get_all_incidents()

    # === Cargar feedback separado ===
    feedback_docs = db.collection("feedback").stream()
    feedback_map = {}
    for fb in feedback_docs:
        data = fb.to_dict()
        if not data:
            continue
        incident_id = data.get("incident_id")
        if incident_id:
            feedback_map[incident_id] = {
                "rating": data.get("rating", 0),
                "comment": data.get("comment", "")
            }

    filtered = []
    for inc in incidents:
        if not inc:
            continue

        created_at = inc.get("created_at")
        if hasattr(created_at, "isoformat"):
            created_at = created_at.isoformat()

        # --- Aplicar filtros ---
        if year and str(created_at)[:4] != str(year):
            continue
        if month and f"-{int(month):02d}-" not in str(created_at):
            continue
        if status and inc.get("status") != status:
            continue
        if user_id and str(inc.get("user_id")) != str(user_id):
            continue

        # --- Asociar feedback por incident_id ---
        fb = feedback_map.get(inc.get("id"), {})
        rating = fb.get("rating", 0)
        comment = fb.get("comment", "")

        filtered.append({
            "id": inc.get("id"),
            "usuario": inc.get("reporter_name", inc.get("username", "—")),
            "fecha": created_at,
            "categoria": inc.get("category", "—"),
            "descripcion": inc.get("message", ""),
            "estado": inc.get("status", "open"),
            "rating": rating,
            "comentario": comment
        })

    return jsonify(filtered)



# === 👤 API: Lista de usuarios (para filtro desplegable) ===
@web_bp.route("/api/users/list")
def api_users_list():
    token = request.args.get("token")
    if token != ADMIN_TOKEN:
        return jsonify({"error": "No autorizado"}), 403

    from data.repository_firebase import db
    users_docs = db.collection("users").stream()
    users = [
        {
            "id": u.id,
            "username": u.to_dict().get("username", ""),
            "full_name": u.to_dict().get("full_name", ""),
        }
        for u in users_docs
    ]
    return jsonify(users)
