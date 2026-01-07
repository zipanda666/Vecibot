from data import repository_firebase as repository
import asyncio
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
import os
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")


# ============================================================
# 🔹 Función auxiliar para enviar mensajes de Telegram
# ============================================================
async def _notify_user(telegram_id, message, reply_markup=None):
    """Envía un mensaje al usuario desde el bot de Telegram."""
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=telegram_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        print(f"✅ Mensaje enviado al usuario {telegram_id}")
    except Exception as e:
        print(f"⚠️ Error al enviar mensaje al usuario {telegram_id}: {e}")


# ============================================================
# 🔹 Registrar un nuevo incidente
# ============================================================
def register_incident(user_id, username, message, address, lat=None, lon=None, category=None):
    """Registra un nuevo incidente en la base de datos y emite evento de SocketIO."""
    incident = repository.create_incident(
        user_id, username, message, address, lat, lon, category
    )

    try:
        from app import socketio
        socketio.emit("new_incident", incident)
    except Exception as e:
        print(f"⚠️ No se pudo emitir evento new_incident: {e}")

    return incident


# ============================================================
# 🔹 Obtener todos los incidentes
# ============================================================
def list_incidents():
    return repository.get_all_incidents()


# ============================================================
# 🔹 Marcar incidente como resuelto
# ============================================================
def mark_resolved(incident_id):
    """Marca un incidente como resuelto, notifica y pide calificación."""
    incident = repository.update_incident_status(incident_id, "resolved")

    if incident:
        try:
            from app import socketio
            socketio.emit("update_incident", incident)
        except Exception as e:
            print(f"⚠️ No se pudo emitir evento update_incident: {e}")

        telegram_id = incident.get("user_id")
        if telegram_id:
            try:
                # Teclado de estrellas con ID del incidente
                keyboard = [[
                    InlineKeyboardButton("1⭐", callback_data=f"rate_1_{incident['id']}"),
                    InlineKeyboardButton("2⭐", callback_data=f"rate_2_{incident['id']}"),
                    InlineKeyboardButton("3⭐", callback_data=f"rate_3_{incident['id']}"),
                    InlineKeyboardButton("4⭐", callback_data=f"rate_4_{incident['id']}"),
                    InlineKeyboardButton("5⭐", callback_data=f"rate_5_{incident['id']}")
                ]]
                markup = InlineKeyboardMarkup(keyboard)

                asyncio.run(_notify_user(
                    telegram_id,
                    f"✅ Tu reporte #{incident['id']} ha sido *marcado como resuelto*.\n\n"
                    f"📝 Descripción: _{incident.get('message', 'Sin descripción')}_\n\n"
                    "Por favor, califica la atención recibida:",
                    reply_markup=markup
                ))
            except Exception as e:
                print(f"❌ Error al enviar mensaje de rating: {e}")

    return incident


# ============================================================
# 🔹 Responder a un incidente
# ============================================================
def respond_incident(incident_id, message):
    """Añade una respuesta al incidente y notifica al usuario."""
    incident = repository.set_incident_response(incident_id, message)

    if incident:
        try:
            from app import socketio
            socketio.emit("update_incident", incident)
        except Exception as e:
            print(f"⚠️ No se pudo emitir evento update_incident: {e}")

        telegram_id = incident.get("user_id")
        if telegram_id:
            asyncio.run(_notify_user(
                telegram_id,
                f"📢 *Respuesta de la comisaría:*\n\n{message}"
            ))

    return incident


# ============================================================
# 🔹 Guardar retroalimentación del usuario
# ============================================================
def save_feedback_service(user_id, incident_id, rating, comment):
    """Guarda la retroalimentación del usuario asociada a su incidente."""
    feedback = repository.save_feedback(user_id, incident_id, rating, comment)

    try:
        from app import socketio
        socketio.emit("new_feedback", feedback)
    except Exception as e:
        print(f"⚠️ No se pudo emitir evento new_feedback: {e}")

    return feedback
