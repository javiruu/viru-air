#!/usr/bin/env python3
import sys
import logging
import json
from datetime import datetime, date
from typing import List, Dict, Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from ryanair import Ryanair

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Constantes/Archivos ---
MENU, NUEVO_VUELO = range(2)
HISTORICO_FILE = "precios_historicos.json"
VUELOS_FILE = "vuelos_guardados.json"
CHECK_INTERVAL_SECONDS = 12 * 3600  # 12h

# --- Token ---
try:
    with open("token.txt", "r") as f:
        TELEGRAM_TOKEN = f.read().strip()
except FileNotFoundError:
    logger.error("❌ No existe token.txt")
    sys.exit(1)

# --- Cliente y memoria ---
RYANAIR_CLIENT = Ryanair(currency="EUR")
vuelos_guardados: List[Dict[str, Any]] = []


# =========================
# Persistencia
# =========================
def cargar_vuelos_guardados() -> List[Dict[str, Any]]:
    try:
        with open(VUELOS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for v in data:
                if isinstance(v.get("date"), str):
                    v["date"] = datetime.strptime(v["date"], "%Y-%m-%d").date()
            return data
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error("Error cargando vuelos: %s", e)
        return []


def guardar_vuelos_guardados():
    try:
        serializable = []
        for v in vuelos_guardados:
            serializable.append(
                {
                    "origin": v["origin"],
                    "destination": v["destination"],
                    "date": v["date"].strftime("%Y-%m-%d") if isinstance(v["date"], date) else str(v["date"]),
                    "chat_id": v["chat_id"],
                }
            )
        with open(VUELOS_FILE, "w", encoding="utf-8") as f:
            json.dump(serializable, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error("Error guardando vuelos: %s", e)


def guardar_historico(entry: Dict[str, Any]):
    try:
        try:
            with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = []
        data.append(entry)
        with open(HISTORICO_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error("Error guardando histórico: %s", e)


def leer_historico() -> List[Dict[str, Any]]:
    try:
        with open(HISTORICO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error("Error leyendo histórico: %s", e)
        return []


# =========================
# UI / Handlers
# =========================
def menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("✈️ Programar Nuevo Vuelo", callback_data="programar"),
            InlineKeyboardButton("🔍 Revisar TODOS los Precios", callback_data="revisar_todos"),
        ],
        [
            InlineKeyboardButton("📊 Ver Histórico de Precios", callback_data="historico"),
            InlineKeyboardButton("🔔 Comprobar JobQueue", callback_data="comprobar_jobqueue"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # ÚNICO punto de entrada -> evita duplicados
    await (update.message or update.callback_query.message).reply_text(
        "👋 ¡Bienvenido al Bot de Ryanair! ¿Qué deseas hacer?",
        reply_markup=menu_keyboard(),
    )
    return MENU


async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    if query.data == "programar":
        await query.edit_message_text(
            "📅 **Programar Vuelo**:\n\n"
            "Envíame: **ORIGEN DESTINO FECHA(YYYY-MM-DD)**\n\n"
            "_Ejemplo: MAD BCN 2025-12-24_",
            parse_mode="Markdown",
            reply_markup=None,
        )
        return NUEVO_VUELO

    if query.data == "revisar_todos":
        return await review_all_prices(update, context)

    if query.data == "historico":
        return await show_history(update, context)

    if query.data == "comprobar_jobqueue":
        return await check_jobqueue_and_run_now(update, context)

    return MENU


async def new_flight_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    try:
        origin, destination, date_str = text.split()
        origin = origin.upper()
        destination = destination.upper()
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        chat_id = update.message.chat_id

        # Evitar duplicados exactos
        for v in vuelos_guardados:
            if (
                v["origin"] == origin
                and v["destination"] == destination
                and v["date"] == parsed_date
                and v["chat_id"] == chat_id
            ):
                await update.message.reply_text("⚠️ Ese vuelo ya está programado.")
                await cmd_menu(update, context)
                return MENU

        vuelo = {"origin": origin, "destination": destination, "date": parsed_date, "chat_id": chat_id}
        vuelos_guardados.append(vuelo)
        guardar_vuelos_guardados()

        await update.message.reply_text(
            f"✅ Guardado: _{origin}_ ➡️ _{destination}_ ({parsed_date:%Y-%m-%d})",
            parse_mode="Markdown",
        )

        await check_flight_price_and_notify(vuelo, context.application, silent=False)
        await cmd_menu(update, context)
        return MENU

    except Exception:
        await update.message.reply_text("❌ Formato inválido. Usa: ORIGEN DESTINO FECHA(YYYY-MM-DD)")
        return NUEVO_VUELO


async def review_all_prices(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not vuelos_guardados:
        await query.edit_message_text("😔 No tienes vuelos guardados.")
        return MENU

    await query.edit_message_text("⏳ Revisando todos los precios...", parse_mode="Markdown")
    for vuelo in vuelos_guardados:
        await check_flight_price_and_notify(vuelo, context.application, silent=True)

    # Volvemos a mostrar menú con un nuevo mensaje (no edit)
    await context.bot.send_message(chat_id=query.message.chat_id, text="Listo ✅", reply_markup=menu_keyboard())
    return MENU


async def check_flight_price_and_notify(vuelo: Dict[str, Any], application, silent: bool = False):
    try:
        flights = RYANAIR_CLIENT.get_cheapest_flights(vuelo["origin"], vuelo["date"], vuelo["date"])
        target_flight = next((f for f in flights if f.destination.upper() == vuelo["destination"].upper()), None)

        if target_flight:
            msg = (
                f"💰 {vuelo['origin']} ➡️ {vuelo['destination']} ({vuelo['date']})\n"
                f"Precio: {target_flight.price:.2f} {target_flight.currency}"
            )
            await application.bot.send_message(chat_id=vuelo["chat_id"], text=msg)

            guardar_historico(
                {
                    "origin": vuelo["origin"],
                    "destination": vuelo["destination"],
                    "date": vuelo["date"].strftime("%Y-%m-%d"),
                    "checked_at": datetime.now().isoformat(timespec="seconds"),
                    "price": target_flight.price,
                    "currency": target_flight.currency,
                    "notified_to": vuelo["chat_id"],
                }
            )
        else:
            if not silent:
                await application.bot.send_message(
                    chat_id=vuelo["chat_id"],
                    text=f"😔 No encontrado: {vuelo['origin']} ➡️ {vuelo['destination']} ({vuelo['date']})",
                )

    except Exception as e:
        logger.error(f"Error Ryanair {vuelo}: {e}")
        if not silent:
            try:
                await application.bot.send_message(
                    chat_id=vuelo["chat_id"],
                    text=f"❌ Error de conexión: {vuelo['origin']} ➡️ {vuelo['destination']}",
                )
            except Exception as send_err:
                logger.error("No se pudo avisar al usuario: %s", send_err)


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    data = leer_historico()

    if not data:
        await query.edit_message_text("📂 No hay datos históricos todavía.")
        return MENU

    resumen = {}
    for entry in data:
        key = f"{entry['origin']} ➡️ {entry['destination']} ({entry['date']})"
        resumen.setdefault(key, [])
        resumen[key].append(f"{entry['checked_at']}: {entry['price']:.2f} {entry['currency']}")

    text = "📊 **Histórico de Precios**\n\n"
    for ruta, checks in resumen.items():
        text += f"✈️ {ruta}\n" + "\n".join(f"   • {c}" for c in checks[-5:]) + "\n\n"

    await query.edit_message_text(text, parse_mode="Markdown")
    return MENU


# =========================
# Tareas y Errores
# =========================
async def periodic_check_job(context: ContextTypes.DEFAULT_TYPE):
    if not vuelos_guardados:
        return
    logger.info("Job periódica: %d vuelos", len(vuelos_guardados))
    for vuelo in list(vuelos_guardados):
        await check_flight_price_and_notify(vuelo, context.application, silent=True)


async def check_jobqueue_and_run_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    jq = context.application.job_queue
    if jq is None:
        await query.edit_message_text("❌ JobQueue no disponible. Instala: python-telegram-bot[job-queue]")
        return MENU

    await query.edit_message_text("⏳ JobQueue OK. Ejecutando comprobación inmediata…")
    try:
        await periodic_check_job(context)
        await context.application.bot.send_message(
            chat_id=query.message.chat_id,
            text="✅ Comprobación inmediata finalizada."
        )
    except Exception as e:
        await context.application.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❌ Error en comprobación inmediata: {e}"
        )
    return MENU


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Excepción no controlada", exc_info=context.error)


# =========================
# Main
# =========================
def main():
    # Cargar persistencia
    global vuelos_guardados
    vuelos_guardados = cargar_vuelos_guardados()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Error handler global
    app.add_error_handler(error_handler)

    # ConversationHandler SOLO para el flujo de botones/inputs
    conv = ConversationHandler(
        entry_points=[CommandHandler("menu", cmd_menu)],  # /menu es el ÚNICO entry point
        states={
            MENU: [CallbackQueryHandler(handle_buttons)],
            NUEVO_VUELO: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_flight_input)],
        },
        fallbacks=[CommandHandler("cancel", cmd_menu)],   # NO usamos /menu como fallback -> evita duplicados
        per_message=False,
    )
    app.add_handler(conv)

    # Alias de /start -> llama a /menu sin duplicar (fuera del ConversationHandler)
    app.add_handler(CommandHandler("start", cmd_menu))

    # Job periódica
    if app.job_queue:
        app.job_queue.run_repeating(periodic_check_job, interval=CHECK_INTERVAL_SECONDS, first=0)
    else:
        logger.warning("JobQueue no disponible. Instala python-telegram-bot[job-queue].")

    logger.info("✅ Bot de Ryanair corriendo con histórico y notificaciones cada 12h...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
