from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

# Replace with your actual token
TOKEN = "6391330002:AAF7D0_8-CWgM6SijlP1PcbXjsVz2iH1OT8"

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! I'm your flight information bot. Type /help to see what I can do.")

def help_command(update: Update, context: CallbackContext):
    update.message.reply_text("Use /get_flights to get the latest flight information.")

def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(TOKEN, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Register handlers for different commands
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))

    # Start the Bot
    updater.start_polling()

    # Run the bot until you send a signal to stop
    updater.idle()

if __name__ == '__main__':
    main()
