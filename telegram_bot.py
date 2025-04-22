import json
import logging
from datetime import datetime
from telegram import Update, BotCommand, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import pytz

# Set up logging to a file with timestamped log messages
logging.basicConfig(
    filename='/home/flight/sample/telegram_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Define the timezone (used for flight time comparisons)
tz = pytz.timezone('America/Toronto')

# Load flight data from JSON file
def load_flight_data():
    with open("flight_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Convert flight info into a user-friendly message format
def format_flight_pretty(flight):
    msg = (
        f"✈️ *{flight['flight_number']}*\n"
        f"From: {flight['origin_city']}\n"
        f"🕑 Departed: {flight['origin_time']} | ETA: {flight['destination_time']}\n"
        f"📍 Status: {status_icon(flight['flight_status'])} {flight['flight_status']} | "
        f"Plane: {flight['fin_number'] or 'N/A'}"
    )
    # If there's a live tracking link, add it to the message
    if "live_tracking_link" in flight:
        msg += f"\n🔗 [Live Tracking]({flight['live_tracking_link']})"

    return msg

# Convert flight status string into an emoji icon
def status_icon(status):
    if status.lower() in ["arrived", "landed"]:
        return "✅"
    elif "on time" in status.lower():
        return "🟢"
    elif "delayed" in status.lower():
        return "⚠️"
    elif "in flight" in status.lower():
        return "✈️"
    elif "early" in status.lower():
        return "⏱"
    else:
        return "ℹ️"

# Handle the /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["/next", "/all_flights"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to the YTZ Flight Bot! ✈️\nChoose an option below:",
        reply_markup=reply_markup
    )

# Show how long until the flight arrives
def format_arrival_time_eta(destination_time_str):
    if not destination_time_str:
        return ""

    try:
        now = datetime.now()
        eta = datetime.strptime(destination_time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )

        # If the time has already passed today, assume it's the next day
        if eta < now:
            eta = eta.replace(day=now.day + 1)

        diff = eta - now
        total_minutes = int(diff.total_seconds() / 60)

        if total_minutes < 60:
            return f"⏳ Arriving in approximately: {total_minutes} minutes"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            return f"⏳ Arriving in approximately: {hours} hour{'s' if hours > 1 else ''} {minutes} minutes"

    except Exception as e:
        return ""

# Handle the /next command – show next arriving flight
async def next_flight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logging.info(f"Inside next_flight Function")
        data = load_flight_data()
        next_flight = data.get("next_arrival_flight")
        last_updated = data.get("last_updated_at", "Unknown")

        if next_flight:
            eta_string = format_arrival_time_eta(next_flight.get("destination_time"))
            msg = (
                f"🛬 *Next Arrival Flight:*\n\n"
                f"{format_flight_pretty(next_flight)}\n"
                f"{eta_string}\n"
                f"🕒 _Last updated at: {last_updated}_"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("No upcoming flights found in the data.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching next flight:\n`{e}`", parse_mode=ParseMode.MARKDOWN)

# Handle the /all_flights command – show all flights in list
async def all_flights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logging.info(f"Inside all_flights Function")
        data = load_flight_data()
        flights = data.get("flights", [])
        total_flights = data.get("total_flights", len(flights))  # fallback in case the key is missing

        msg = f"*All Flights (Total: {total_flights}):*\n\n"
        for flight in flights:
            msg += format_flight_pretty(flight)
            msg += "\n\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Error reading flight data: {e}")

# This function runs every 2 minutes to check if flight is arriving soon
async def flight_arrival_watcher(context: ContextTypes.DEFAULT_TYPE):
    try:
        print("[DEBUG] Running watcher")
        logging.info("[Watcher] Checking arrival time of next flight...")
        data = load_flight_data()
        next_flight = data.get("next_arrival_flight")

        if not next_flight:
            return

        # Parse flight ETA
        flight_eta_str = next_flight.get("destination_time")
        if not flight_eta_str:
            return

        now = datetime.now(tz)
        naive_eta = datetime.strptime(flight_eta_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        flight_eta = tz.localize(naive_eta)

        if flight_eta < now:
            flight_eta = flight_eta.replace(day=now.day + 1)

        minutes_left = (flight_eta - now).total_seconds() / 60

        print(f"[DEBUG] ETA: {flight_eta}, Now: {now}, Minutes left: {minutes_left}")

        # If flight is arriving within 5 minutes, send notification + auto trigger /next
        if 0 < minutes_left <= 5:
            eta_msg = (f"🚨 *Flight {flight.get('flight_number', 'N/A')} landing in approximately {int(minutes_left)} minute(s)*")
            await context.bot.send_message(chat_id=6207265706, text=eta_msg, parse_mode=ParseMode.MARKDOWN)
            await next_flight(update=Update(update_id=0, message=None), context=context)

    except Exception as e:
        logging.error(f"[Watcher Error] {e}")

# Main function to start the Telegram bot
def main():
    logging.info("Starting the Flight Status Bot...")
    TOKEN = "6391330002:AAF7D0_8-CWgM6SijlP1PcbXjsVz2iH1OT8"

    app = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_flight))
    app.add_handler(CommandHandler("all_flights", all_flights))

    # Run our background task every 2 minutes (120s)
    app.job_queue.run_repeating(flight_arrival_watcher, interval=120, first=10)

    # Set Telegram command list in app
    app.bot.set_my_commands([
        BotCommand("start", "Start the bot and get help"),
        BotCommand("next", "Show the next arriving flight"),
        BotCommand("all_flights", "List all today’s flights"),
    ])

    # Start polling for updates
    print("Bot is running...")
    app.run_polling()

# Entry point of the script
if __name__ == "__main__":
    main()
