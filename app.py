# app.py
import threading
from flask import Flask
from flask_socketio import SocketIO
from data import repository_firebase as repository  
from presentation.views.web_view import web_bp
from presentation.presenters.bot_presenter import create_bot_app
import asyncio

# ==========================
# ⚙️ Flask + SocketIO
# ==========================
app = Flask(__name__, template_folder="ui/templates")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Registrar blueprint web
app.register_blueprint(web_bp)

# Vincular eventos entre capa de datos y socket.io
def _emit_event(name, payload):
    try:
        socketio.emit(name, payload)
    except Exception as e:
        print("⚠️ Emit error:", e)

repository.set_emit_callback(_emit_event)

# ==========================
# 🤖 Integración Telegram + Flask
# ==========================
def run_bot():
    """Ejecuta el bot de Telegram en un hilo separado (sin crear loops adicionales)."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    bot_app = loop.run_until_complete(create_bot_app())
    print("🤖 VeciBot (bot de Telegram) iniciado correctamente...")
    bot_app.run_polling()

if __name__ == "__main__":
    print("✅ Firebase conectado correctamente (no se requiere init_db).")

    # Ejecutar el bot en un hilo
    threading.Thread(target=run_bot, daemon=True).start()

    print("🌍 Servidor Flask + SocketIO corriendo en http://localhost:5000 ...")
    socketio.run(app, host="0.0.0.0", port=5000)
