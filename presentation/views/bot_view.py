from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup,
    KeyboardButton, ReplyKeyboardMarkup, Update
)
from telegram.ext import ContextTypes
from core.geolocalizador import reverse_latlon
from core.incident_service import register_incident, save_feedback_service
from data.repository_firebase import register_user, get_user


class BotView:

    # === /start ===
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.message.from_user
        db_user = get_user(user.id)

        keyboard = [
            [InlineKeyboardButton("🆘 Reportar incidente", callback_data="reporte")],
            [InlineKeyboardButton("🗺️ Ver mapa público", callback_data="mapa")],
            [InlineKeyboardButton("📝 Registrar mis datos", callback_data="registrar")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if db_user:
            msg = (
                f"👋 ¡Hola {db_user['full_name']}!\n"
                f"DNI: {db_user['dni']}\n📱 {db_user['phone_number']}\n\n"
                "Selecciona una opción:"
            )
        else:
            msg = (
                "👋 *Bienvenido a VeciBot*\n\n"
                "Antes de reportar emergencias, puedes registrar tus datos personales "
                "para agilizar reportes futuros."
            )

        await update.message.reply_photo(
            photo="https://i.imgur.com/Yy5qZnN.png",
            caption=msg,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

    # === Botones principales ===
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data

        # Reportar incidente
        if data == "reporte":
            kb = [[KeyboardButton("📍 Enviar ubicación actual", request_location=True)]]
            await query.message.reply_text(
                "📍 Comparte tu ubicación para reportar:",
                reply_markup=ReplyKeyboardMarkup(kb, one_time_keyboard=True, resize_keyboard=True)
            )
            context.user_data["modo"] = "esperando_ubicacion"

        elif data == "mapa":
            await query.message.reply_text("🗺️ Abre el mapa en: http://localhost:5000/")

        elif data == "registrar":
            await query.message.reply_text("🧍‍♂️ Por favor, escribe tu *nombre completo:*", parse_mode="Markdown")
            context.user_data["modo"] = "registrando_nombre"

        # Rating con ID de incidente
        elif data.startswith("rate_"):
            try:
                _, rating_s, incident_id = data.split("_", 2)  # <-- admite IDs con guiones o letras
                rating = int(rating_s)
            except Exception:
                await query.message.reply_text("⚠️ No se pudo identificar el reporte a calificar.")
                return

            context.user_data["rating"] = rating
            context.user_data["incident_id"] = incident_id
            context.user_data["modo"] = "esperando_feedback"

            await query.message.reply_text(
                f"⭐ Gracias por calificar con {rating} estrellas.\n\n"
                "💬 Ahora puedes dejar un breve comentario sobre la atención (opcional)."
            )

    # === Mensajes ===
    async def recibir_mensaje(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        modo = context.user_data.get("modo")
        text = (update.message.text or "").strip()
        user = update.message.from_user

        # Registro paso 1
        if modo == "registrando_nombre":
            context.user_data["full_name"] = text
            context.user_data["modo"] = "registrando_dni"
            await update.message.reply_text("🪪 Ahora ingresa tu *DNI:*", parse_mode="Markdown")
            return

        # Registro paso 2
        if modo == "registrando_dni":
            if not text.isdigit() or len(text) != 8:
                await update.message.reply_text("⚠️ El DNI debe tener 8 dígitos. Intenta de nuevo.")
                return
            context.user_data["dni"] = text
            context.user_data["modo"] = "registrando_telefono"
            button = KeyboardButton("📱 Compartir mi número", request_contact=True)
            markup = ReplyKeyboardMarkup([[button]], one_time_keyboard=True, resize_keyboard=True)
            await update.message.reply_text("Perfecto ✅\nAhora comparte tu número de teléfono:", reply_markup=markup)
            return

        # Descripción del incidente
        if modo == "esperando_descripcion":
            context.user_data["mensaje_incidente"] = text
            context.user_data["modo"] = "esperando_categoria"
            keyboard = [
                [InlineKeyboardButton("🚨 Robo", callback_data="cat_robo")],
                [InlineKeyboardButton("😠 Acoso", callback_data="cat_acoso")],
                [InlineKeyboardButton("🎨 Vandalismo", callback_data="cat_vandalismo")],
                [InlineKeyboardButton("🔥 Emergencia", callback_data="cat_emergencia")],
                [InlineKeyboardButton("❓ Otro", callback_data="cat_otro")]
            ]
            await update.message.reply_text(
                "Selecciona la categoría que mejor describa el incidente:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        # Feedback
        if modo == "esperando_feedback":
            rating = context.user_data.get("rating")
            incident_id = context.user_data.get("incident_id")

            if not rating or not incident_id:
                await update.message.reply_text("⚠️ Error al registrar tu calificación. Intenta nuevamente.")
                context.user_data.clear()
                return

            comment = text if text else "Sin comentario"
            save_feedback_service(user.id, incident_id, rating, comment)

            await update.message.reply_text(
                f"🙏 Gracias por tu comentario.\n⭐ {rating} estrellas\n💬 {comment}"
            )
            context.user_data.clear()
            return

        await update.message.reply_text("Usa /start para iniciar o registrar tus datos.")

    # === Contacto ===
    async def recibir_contacto(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        contact = update.message.contact
        if not contact:
            await update.message.reply_text("⚠️ Usa el botón para compartir tu número.")
            return

        register_user(
            contact.user_id,
            update.message.from_user.username,
            context.user_data.get("full_name", ""),
            context.user_data.get("dni", ""),
            contact.phone_number
        )

        await update.message.reply_text("✅ Registro completado. Ya puedes reportar incidentes.")
        context.user_data.clear()

    # === Ubicación ===
    async def recibir_ubicacion(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        loc = update.message.location
        info = reverse_latlon(loc.latitude, loc.longitude)
        address = info.get("address", "Ubicación desconocida")

        context.user_data.update({
            "lat": loc.latitude,
            "lon": loc.longitude,
            "address": address,
            "modo": "esperando_descripcion"
        })

        await update.message.reply_text(
            f"✅ Ubicación detectada:\n📍 {address}\n\nAhora describe el incidente."
        )

    # === Categoría ===
    async def categoria_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user = query.from_user
        data = context.user_data
        if "modo" not in data or data["modo"] != "esperando_categoria":
            await query.message.reply_text("Usa /start para comenzar un nuevo reporte.")
            return

        categoria_map = {
            "cat_robo": "Robo",
            "cat_acoso": "Acoso",
            "cat_vandalismo": "Vandalismo",
            "cat_emergencia": "Emergencia",
            "cat_otro": "Otro"
        }
        categoria = categoria_map.get(query.data, "Otro")

        lat, lon, address, msg = data.get("lat"), data.get("lon"), data.get("address"), data.get("mensaje_incidente")
        incident = register_incident(user.id, user.username or user.first_name, msg, address, lat, lon, categoria)

        await query.message.reply_text(
            f"✅ Reporte registrado exitosamente.\n📍 {address}\n🗂️ Categoría: *{categoria}*\n🆔 ID: {incident.get('id')}",
            parse_mode="Markdown"
        )
        context.user_data.clear()
