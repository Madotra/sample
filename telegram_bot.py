import json
from datetime import datetime
from telegram import Update, BotCommand, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters

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
    keyboard = [["/next", "/all_flights", "/flight_by_number"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to the YTZ Flight Bot! ✈️\nChoose an option below:",
        reply_markup=reply_markup
    )

# /next command handler - Show the next flight from precomputed JSON field
async def next_flight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = load_flight_data()
        next_flight = data.get("next_arrival_flight")

        if next_flight:
            msg = f"🛬 *Next Arrival Flight:*\n\n{format_flight_pretty(next_flight)}"
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

# /flight_by_number command handler
async def flight_by_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Prompt the user to enter a flight number
    await update.message.reply_text("Please provide a flight number to search for.")

    # Wait for the next message which should contain the flight number
    # The message will be handled by the next handler, which we'll define below

# Flight number search handler
async def search_flight_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flight_number = update.message.text.strip()

    data = load_flight_data()
    flights = data.get("flights", [])

    # Remove any prefix like 'AC' if present
    flight_number = flight_number.replace("AC", "").strip()

    # Search for the flight by number
    matching_flight = None
    for flight in flights:
        if flight["flight_number"] == flight_number:
            matching_flight = flight
            break

    if matching_flight:
        # If a match is found, format and send the flight details
        msg = format_flight_pretty(matching_flight)
        await update.message.reply_text(msg, parse_mode="Markdown")
    else:
        # If no match is found, inform the user
        await update.message.reply_text("Sorry, unable to find such a flight.")


# Main function to start the bot
def main():
    TOKEN = "6391330002:AAF7D0_8-CWgM6SijlP1PcbXjsVz2iH1OT8"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_flight))
    app.add_handler(CommandHandler("all_flights", all_flights))
    app.add_handler(CommandHandler("flight_by_number", flight_by_number))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_flight_number))
    
    app.bot.set_my_commands([
        BotCommand("start", "Start the bot and get help"),
        BotCommand("next", "Show the next arriving flight"),
        BotCommand("all_flights", "List all today’s flights"),
        BotCommand("flight_by_number", "Search flight by its number"),
    ])

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
