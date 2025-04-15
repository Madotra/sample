import json
from telegram import Update
from datetime import datetime
from telegram import BotCommand
from telegram import ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load flight data from the JSON file
def load_flight_data():
    with open("flight_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Inside /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["/next", "/flights"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Welcome to the YTZ Flight Bot! ✈️\nChoose an option below:",
        reply_markup=reply_markup
    )

# /next command handler
async def next_flight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = load_flight_data()
        flight = data.get("next_arrival_flight")

        if flight:
            now = datetime.now()
            dest_time_str = flight["destination_time"]
            dest_time = datetime.strptime(dest_time_str, "%H:%M").replace(
                year=now.year, month=now.month, day=now.day
            )

            time_diff = dest_time - now
            total_minutes = int(time_diff.total_seconds() // 60)

            # Format landing time nicely
            if total_minutes < 1:
                landing_str = "Landing now!"
            elif total_minutes < 60:
                landing_str = f"Landing in approximately {total_minutes} minute(s)."
            else:
                hours = total_minutes // 60
                minutes = total_minutes % 60
                landing_str = f"Landing in approximately {hours}h {minutes}m."

            msg = (
                f"✈️ Flight {flight['flight_number']} from {flight['origin_city']} "
                f"arrives in {flight['destination_city']} at {flight['destination_time']}.\n"
                f"Status: {flight['flight_status']}\n"
                f"🕓 {landing_str}"
            )

            if "live_tracking_link" in flight:
                msg += f"\n🔗 [Live Tracking]({flight['live_tracking_link']})"

            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("No upcoming flights found.")
    except Exception as e:
        await update.message.reply_text(f"Error reading flight data: {e}")

def format_flight_pretty(flight):
    return (
        f"✈️ *{flight['flight_number']}*\n"
        f"From: {flight['origin_city']}\n"
        f"🕑 Departed: {flight['origin_time']} | ETA: {flight['destination_time']}\n"
        f"📍 Status: {status_icon(flight['flight_status'])} {flight['flight_status']} | "
        f"Plane: {flight['fin_number'] or 'N/A'}"
    )

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


# /all flights command handler
async def all_flights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        data = load_flight_data()
        flights = data.get("flights", [])

        if not flights:
            await update.message.reply_text("No flights found.", parse_mode=ParseMode.MARKDOWN)
            return

        message = "📋 *All Flights to Toronto YTZ:*\n\n"
        messages = []

        for flight in flights:
            flight_text = format_flight_pretty(flight) + "\n\n"
            if len(message) + len(flight_text) > 3900:  # Telegram limit is 4096
                messages.append(message)
                message = ""
            message += flight_text

        messages.append(message)

        for msg in messages:
            await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        await update.message.reply_text(f"❌ Error reading flight data:\n`{e}`", parse_mode=ParseMode.MARKDOWN)


# Main function to start the bot
def main():
    TOKEN = "6391330002:AAF7D0_8-CWgM6SijlP1PcbXjsVz2iH1OT8"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_flight))
    app.add_handler(CommandHandler("all flights", all_flights))
    # Inside main() after app is created
    app.bot.set_my_commands([
        BotCommand("start", "Start the bot and get help"),
        BotCommand("next", "Show the next arriving flight"),
        BotCommand("all flights", "List all today’s flights"),
    ])

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
