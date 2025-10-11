import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("No bot token provided! Please set BOT_TOKEN environment variable.")


app = Flask(__name__)
telegram_app = None  # This will hold the Telegram Application instance

# Telegram command handler example
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello! I'm your stock alert bot.")

# Flask route for basic health check or webhook (optional)
@app.route("/")
def index():
    return "Stock Alert Bot is running!"

# If you want to support webhooks instead of polling, set up Flask route like this:
@app.route(f"/webhook/{TOKEN}", methods=["POST"])
async def telegram_webhook():
    data = await request.get_json()
    update = Update.de_json(data, telegram_app.bot)
    await telegram_app.update_queue.put(update)
    return "OK"

async def main():
    global telegram_app

    # Create the Telegram Application (bot)
    telegram_app = Application.builder().token(TOKEN).build()

    # Register command handlers
    telegram_app.add_handler(CommandHandler("start", start))

    # Run polling in a background task
    polling_task = asyncio.create_task(telegram_app.run_polling())

    # Run Flask in an executor (since Flask is sync by default)
    loop = asyncio.get_event_loop()
    from threading import Thread

    def run_flask():
        app.run(host="0.0.0.0", port=10000)

    flask_thread = Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Wait for the polling to finish (never, unless interrupted)
    await polling_task

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError as e:
        # This can happen if event loop is already running, e.g., in Jupyter
        print(f"Runtime error: {e}")