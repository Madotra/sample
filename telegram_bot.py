import json
from telegram import Update
from datetime import datetime
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load flight data from the JSON file
def load_flight_data():
    with open("flight_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send /next to get the next arriving flight info.")

from datetime import datetime

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
            minutes_until_landing = int((dest_time - now).total_seconds() // 60)

            msg = (
                f"✈️ Flight {flight['flight_number']} from {flight['origin_city']} "
                f"arrives in {flight['destination_city']} at {flight['destination_time']}.\n"
                f"Status: {flight['flight_status']}\n"
                f"🕓 Landing in approximately {minutes_until_landing} minutes."
            )
            if "live_tracking_link" in flight:
                msg += f"\n🔗 [Live Tracking]({flight['live_tracking_link']})"

            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("No upcoming flights found.")
    except Exception as e:
        await update.message.reply_text(f"Error reading flight data: {e}")


# Main function to start the bot
def main():
    TOKEN = "6391330002:AAF7D0_8-CWgM6SijlP1PcbXjsVz2iH1OT8"

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("next", next_flight))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
