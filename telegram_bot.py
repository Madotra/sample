import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from telegram import Update, BotCommand, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import pytz
import os

# ==== Logging Setup with Rotation ====
LOG_FILE = '/home/flight/sample/telegram_bot.log'
log_handler = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)  # 5 MB max per file
logging.basicConfig(
    handlers=[log_handler],
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Timezone for flight time comparisons
tz = pytz.timezone('America/Toronto')

# ==== Load Flight Data ====
def load_flight_data():
    try:
        with open("flight_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logging.error("flight_data.json not found.")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding flight_data.json: {e}")
        return {}

# ==== Format Flight Messages ====
def status_icon(status):
    if not status:
        return "ℹ️"
    status_lower = status.lower()
    if status_lower in ["arrived", "landed"]:
        return "✅"
    elif "on time" in status_lower:
        return "🟢"
    elif "delayed" in status_lower:
        return "⚠️"
    elif "in flight" in status_lower:
        return "✈️"
    elif "early" in status_lower:
        return "⏱"
    elif "Cancelled" in status_lower or "Canceled" in status_lower:
        return "❌"
    else:
        return "ℹ️"

def format_flight_pretty(flight):
    msg = (
        f"✈️ *{flight.get('flight_number', 'N/A')}*\n"
        f"From: {flight.get('origin_city', 'N/A')}\n"
        f"🕑 Departed: {flight.get('origin_time', 'N/A')} | ETA: {flight.get('destination_time', 'N/A')}\n"
        f"📍 Status: {status_icon(flight.get('flight_status'))} {flight.get('flight_status', 'N/A')} | "
        f"Plane: {flight.get('fin_number') or 'N/A'}"
    )
    if "live_tracking_link" in flight:
        msg += f"\n🔗 [Live Tracking]({flight['live_tracking_link']})"
    return msg

def format_arrival_time_eta(destination_time_str):
    if not destination_time_str:
        return ""
    try:
        now = datetime.now(tz)
        eta = datetime.strptime(destination_time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        eta = tz.localize(eta)

        if eta < now:
            eta += timedelta(days=1)

        diff = eta - now
        total_minutes = int(diff.total_seconds() / 60)

        if total_minutes < 60:
            return f"⏳ Arriving in approximately: {total_minutes} minutes"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"⏳ Arriving in approximately: {hours} hour{'s' if hours > 1 else ''} {minutes} minutes"
    except Exception as e:
        logging.error(f"Error parsing ETA: {e}")
        return ""

# ==== Command Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["/next", "/all_flights"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to the YTZ Flight Bot! ✈️\nChoose an option below:",
        reply_markup=reply_markup
    )

async def next_flight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = load_flight_data()
        next_flight_data = data.get("next_arrival_flight")
        last_updated = data.get("last_updated_at", "Unknown")

        if next_flight_data:
            eta_string = format_arrival_time_eta(next_flight_data.get("destination_time"))
            msg = (
                f"🛬 *Next Arrival Flight:*\n\n"
                f"{format_flight_pretty(next_flight_data)}\n"
                f"{eta_string}\n"
                f"🕒 _Last updated at: {last_updated}_"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("No upcoming flights found in the data.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching next flight:\n`{e}`", parse_mode=ParseMode.MARKDOWN)

async def all_flights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = load_flight_data()
        flights = data.get("flights", [])
        total_flights = data.get("total_flights", len(flights))
        msg = f"*All Flights (Total: {total_flights}):*\n\n"
        for flight in flights:
            msg += format_flight_pretty(flight) + "\n\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Error reading flight data: {e}")

# ==== Background Watcher ====
async def flight_arrival_watcher(context: ContextTypes.DEFAULT_TYPE):
    try:
        logging.info("[Watcher] Checking arrival time of next flight...")
        data = load_flight_data()
        next_flight_data = data.get("next_arrival_flight")
        if not next_flight_data:
            return

        eta_str = next_flight_data.get("destination_time")
        if not eta_str:
            return

        now = datetime.now(tz)
        eta = datetime.strptime(eta_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        eta = tz.localize(eta)

        if eta < now:
            eta += timedelta(days=1)

        minutes_left = (eta - now).total_seconds() / 60
        if 0 < minutes_left <= 5:
            eta_msg = f"🚨 *Flight {next_flight_data.get('flight_number', 'N/A')} landing in approximately {int(minutes_left)} minute(s)*"
            await context.bot.send_message(chat_id=6207265706, text=eta_msg, parse_mode=ParseMode.MARKDOWN)

            # Reuse formatting logic directly
            last_updated = data.get("last_updated_at", "Unknown")
            flight_msg = (
                f"🛬 *Next Arrival Flight:*\n\n"
                f"{format_flight_pretty(next_flight_data)}\n"
                f"{format_arrival_time_eta(eta_str)}\n"
                f"🕒 _Last updated at: {last_updated}_"
            )
            await context.bot.send_message(chat_id=6207265706, text=flight_msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logging.error(f"[Watcher Error] {e}")

# ==== Main ====
def main():
    logging.info("Starting the Flight Status Bot...")
    TOKEN = "6391330002:AAF7D0_8-CWgM6SijlP1PcbXjsVz2iH1OT8"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_flight))
    app.add_handler(CommandHandler("all_flights", all_flights))

    app.job_queue.run_repeating(flight_arrival_watcher, interval=120, first=10)

    app.bot.set_my_commands([
        BotCommand("start", "Start the bot and get help"),
        BotCommand("next", "Show the next arriving flight"),
        BotCommand("all_flights", "List all today’s flights"),
    ])

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
