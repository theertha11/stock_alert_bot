from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import asyncio
import os
import threading
from flask import Flask

# --- Flask App to bind a port (for Render) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🟢 Stock Alert Bot is running on Render!"

# --- Global Storage ---
watchlist = {}  # Example: {'TCS.NS': 4200.0}
chat_ids = set()  # Track users to notify

BOT_TOKEN = os.getenv("BOT_TOKEN")
app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Command: /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_ids.add(update.effective_chat.id)
    await update.message.reply_text(
        "📈 Welcome to Stock Alert Bot!\n\n"
        "Use /add <symbol> <price> to set an alert.\n"
        "Example: /add TCS.NS 4200\n\n"
        "I’ll notify you when it reaches that price!"
    )

# --- Command: /add ---
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        symbol = context.args[0].upper()
        price = float(context.args[1])
        watchlist[symbol] = price
        chat_ids.add(update.effective_chat.id)
        await update.message.reply_text(f"✅ Added alert: {symbol} → ₹{price}")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /add SYMBOL PRICE\nExample: /add INFY.NS 1600")

# --- Command: /list ---
async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not watchlist:
        await update.message.reply_text("🕸️ No active alerts yet.")
        return
    msg = "🔔 Active Alerts:\n"
    for sym, val in watchlist.items():
        msg += f"• {sym} → ₹{val}\n"
    await update.message.reply_text(msg)

# --- Price Check Logic ---
async def check_prices():
    for symbol, target in list(watchlist.items()):
        await asyncio.sleep(2)  # delay to avoid rate-limit
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if data.empty:
            print(f"{symbol}: No data found, possibly delisted.")
            continue
        current_price = data["Close"].iloc[-1]
        print(f"Checking {symbol}: {current_price} vs {target}")
        if current_price >= target:
            for chat_id in chat_ids:
                try:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"🚨 {symbol} reached ₹{current_price:.2f} (Target ₹{target})"
                    )
                except Exception as e:
                    print(f"Failed to send message to chat {chat_id}: {e}")
            del watchlist[symbol]

# --- Scheduler Setup ---
scheduler = BackgroundScheduler()

# This function will be run by the scheduler every 2 minutes
def schedule_check_prices():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    asyncio.run_coroutine_threadsafe(check_prices(), loop)

scheduler.add_job(schedule_check_prices, 'interval', minutes=2)
scheduler.start()

# --- Register Commands ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", list_alerts))

# --- Run Flask in background thread ---
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Flask server running on port {port}")
    web_app.run(host='0.0.0.0', port=port)

# --- Main ---
if __name__ == '__main__':
    # Start Flask app in background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Run Telegram bot in main thread
    print("🤖 Stock Alert Bot polling started...")
    app.run_polling()