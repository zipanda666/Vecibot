import os
from dotenv import load_dotenv
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
from presentation.views.bot_view import BotView

# Cargar token desde .env
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ No se encontró TELEGRAM_TOKEN en el archivo .env")

async def create_bot_app():
    """
    Crea y devuelve la aplicación del bot de Telegram.
    Aplica el patrón MVP: el Presenter conecta eventos del bot
    con las funciones de la vista (BotView).
    """
    view = BotView()

    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .build()
    )

    # === Comandos ===
    app.add_handler(CommandHandler("start", view.start))

    # === Callbacks de botones ===
    # Menú principal + rating (agregamos 'rate_' al patrón)
    app.add_handler(CallbackQueryHandler(view.button_handler, pattern="^(reporte|mapa|registrar|rate_.*)$"))

    # Botones de categorías
    app.add_handler(CallbackQueryHandler(view.categoria_handler, pattern="^cat_"))

    # === Mensajes y contenido ===
    # Ubicación (reportes)
    app.add_handler(MessageHandler(filters.LOCATION, view.recibir_ubicacion))

    # Contacto (registro de usuario)
    app.add_handler(MessageHandler(filters.CONTACT, view.recibir_contacto))

    # Texto general (nombre, DNI, descripción, feedback)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, view.recibir_mensaje))

    return app
