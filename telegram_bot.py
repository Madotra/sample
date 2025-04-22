import json
import logging
from datetime import datetime
from telegram import Update, BotCommand, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import pytz

# Set up logging with a timestamp in the log format
logging.basicConfig(
    filename='/home/flight/sample/telegram_bot.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Assuming your server timezone is Toronto
tz = pytz.timezone('America/Toronto')

# Load flight data from the JSON file
def load_flight_data():
    with open("flight_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Function to format flight details in a pretty way
def format_flight_pretty(flight):
    msg = (
        f"✈️ *{flight['flight_number']}*\n"
        f"From: {flight['origin_city']}\n"
        f"🕑 Departed: {flight['origin_time']} | ETA: {flight['destination_time']}\n"
        f"📍 Status: {status_icon(flight['flight_status'])} {flight['flight_status']} | "
        f"Plane: {flight['fin_number'] or 'N/A'}"
    )

    if "live_tracking_link" in flight:
        msg += f"\n🔗 [Live Tracking]({flight['live_tracking_link']})"

    return msg

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["/next", "/all_flights"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to the YTZ Flight Bot! ✈️\nChoose an option below:",
        reply_markup=reply_markup
    )

def format_arrival_time_eta(destination_time_str):
    if not destination_time_str:
        return ""

    try:
        now = datetime.now()
        eta = datetime.strptime(destination_time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
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
    except Exception:
        return ""

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

async def all_flights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        logging.info(f"Inside all_flights Function")
        data = load_flight_data()
        flights = data.get("flights", [])
        msg = "*All Flights:*\n"
        for flight in flights:
            msg += format_flight_pretty(flight) + "\n\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Error reading flight data: {e}")

async def flight_arrival_watcher(context: ContextTypes.DEFAULT_TYPE):
    try:
        logging.info("[Watcher] Checking flight ETA")
        data = load_flight_data()
        next_flight = data.get("next_arrival_flight")
        if not next_flight:
            return

        eta_str = next_flight.get("destination_time")
        if not eta_str:
            return

        now = datetime.now(pytz.timezone("America/Toronto"))
        flight_eta = datetime.strptime(eta_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day, tzinfo=pytz.timezone("America/Toronto")
        )

        # Adjust for post-midnight
        if flight_eta < now:
            flight_eta = flight_eta.replace(day=now.day + 1)

        minutes_left = (flight_eta - now).total_seconds() / 60

        if 0 < minutes_left <= 5:
            msg = f"🚨 Flight landing in approximately {int(minutes_left)} minutes!"
            await context.bot.send_message(chat_id=6207265706, text=msg)

            # Simulate /next command
            fake_update = Update(update_id=0, message=None)
            fake_update.effective_chat = type("Chat", (), {"id": 6207265706})
            await next_flight(fake_update, context)

    except Exception as e:
        logging.error(f"[Watcher Error] {e}")


def main():
    logging.info(f"Inside main Function")
    TOKEN = "6391330002:AAF7D0_8-CWgM6SijlP1PcbXjsVz2iH1OT8"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_flight))
    app.add_handler(CommandHandler("all_flights", all_flights))
    # Run arrival check every 2 minutes
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
