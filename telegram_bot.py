import json
from datetime import datetime
from telegram import Update, BotCommand, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import pytz
from telegram import Bot

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

    # Check if live tracking link is available and add it
    if "live_tracking_link" in flight:
        msg += f"\n🔗 [Live Tracking]({flight['live_tracking_link']})"

    return msg

# Function to return the appropriate status icon based on the flight status
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

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["/next", "/all_flights"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to the YTZ Flight Bot! ✈️\nChoose an option below:",
        reply_markup=reply_markup
    )

# Background job to notify when flight is within 5 minutes
async def notify_if_flight_is_soon(context: ContextTypes.DEFAULT_TYPE):
    try:
        data = load_flight_data()
        next_flight = data.get("next_arrival_flight")

        if not next_flight:
            return

        # Extract flight time in HH:MM format
        flight_time_str = next_flight.get("destination_time")
        if not flight_time_str:
            return

        # Parse and localize the flight time to Toronto timezone
        now = datetime.now(pytz.timezone("America/Toronto"))
        flight_time = datetime.strptime(flight_time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day, tzinfo=pytz.timezone("America/Toronto")
        )

        # Handle case where flight is after midnight (past current time)
        if flight_time < now:
            flight_time = flight_time.replace(day=now.day + 1)

        # Check if flight is within 5 minutes
        minutes_left = (flight_time - now).total_seconds() / 60
        if 0 < minutes_left <= 5:
            msg = f"🚨 *Flight Arriving Soon!*\n\n{format_flight_pretty(next_flight)}"
            await context.bot.send_message(chat_id=6207265706, text=msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        print(f"[notify job error] {e}")


# /next command handler - Show the next flight from precomputed JSON field
async def next_flight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = load_flight_data()
        next_flight = data.get("next_arrival_flight")
        last_updated = data.get("last_updated_at", "Unknown")
        
        if next_flight:

                # Get the destination time as a string (e.g., "16:43")
                destination_time_str = next_flight.get("destination_time")
            
            if destination_time_str:
                # Convert destination time string to a datetime object
                destination_time = datetime.strptime(destination_time_str, "%H:%M")
                destination_time = tz.localize(destination_time)  # Localize to Toronto timezone
                
                # Get the current time in the server's timezone
                current_time = datetime.now(tz)

                # Calculate the time difference in minutes
                time_diff = destination_time - current_time
                minutes_remaining = time_diff.total_seconds() / 60  # Convert seconds to minutes
                minutes_remaining = max(0, round(minutes_remaining))  # Ensure it doesn't show negative minutes

                arriving_in_msg = f"⏳ Arriving in approximately: {minutes_remaining} minutes"
            else:
                arriving_in_msg = "⏳ Destination time not available"
            
            msg = (
                f"🛬 *Next Arrival Flight:*\n\n"
                f"{format_flight_pretty(next_flight)}\n"
                f"⏳ Arriving in approximately: {round(arrival_in_minutes)} minutes\n"
                f"🕒 _Last updated at: {last_updated}_"
            )
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("No upcoming flights found in the data.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error fetching next flight:\n`{e}`", parse_mode=ParseMode.MARKDOWN)

# /all_flights command handler
async def all_flights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = load_flight_data()
        flights = data.get("flights", [])
        msg = "*All Flights:*\n"
        for flight in flights:
            msg += format_flight_pretty(flight)
            msg += "\n"
            msg += "\n"
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"Error reading flight data: {e}")

# Main function to start the bot
def main():
    TOKEN = "6391330002:AAF7D0_8-CWgM6SijlP1PcbXjsVz2iH1OT8"

    app = ApplicationBuilder().token(TOKEN).build()

    # Register your command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_flight))
    app.add_handler(CommandHandler("all_flights", all_flights))

    # Schedule background job
    app.job_queue.run_repeating(notify_if_flight_is_soon, interval=60, first=10)

    
    app.bot.set_my_commands([
        BotCommand("start", "Start the bot and get help"),
        BotCommand("next", "Show the next arriving flight"),
        BotCommand("all_flights", "List all today’s flights"),
    ])

    # Start the bot
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
