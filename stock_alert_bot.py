from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import asyncio
import os
import threading
from flask import Flask
import logging

# --- Logging setup (important for cron stability) ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- Flask App to bind a port (for Render) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🟢 Stock Alert Bot is running on Render!"

# --- Global Storage ---
watchlist = {} # Example: {'TCS.NS': ('>=', 4200.0)}
chat_ids = set() # Track users to notify

BOT_TOKEN = os.getenv("BOT_TOKEN")
app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- /start command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_ids.add(update.effective_chat.id)
    await update.message.reply_text(
        "📈 Welcome to Stock Alert Bot!\n\n"
        "Use /add <symbol> >= <price> or /add <symbol> <= <price> to set an alert.\n"
        "Example: /add TCS.NS >= 4200\n\n"
        "I’ll notify you when it reaches that price!"
    )

# --- /add command ---
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        symbol = context.args[0].upper()
        operator = context.args[1]
        price = float(context.args[2])

        if operator not in [">=", "<="]:
            raise ValueError("Invalid operator")

        watchlist[symbol] = (operator, price)
        chat_ids.add(update.effective_chat.id)
        await update.message.reply_text(f"✅ Added alert: {symbol} {operator} ₹{price}")

    except (IndexError, ValueError):
        await update.message.reply_text(
            "⚠️ Usage: /add SYMBOL >= PRICE\nExample: /add INFY.NS <= 1600"
        )

# --- /list command ---
async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not watchlist:
        await update.message.reply_text("🕸️ No active alerts yet.")
        return
    msg = "🔔 Active Alerts:\n"
    for sym, (op, val) in watchlist.items():
        msg += f"• {sym} {op} ₹{val}\n"
    await update.message.reply_text(msg)

# --- Price check logic ---
async def check_prices():
    logging.info("Running scheduled stock check...")
    for symbol, (operator, target) in list(watchlist.items()):
        try:
            await asyncio.sleep(2) # avoid rate-limit
            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if data.empty:
                logging.warning(f"{symbol}: No data found.")
                continue
            current_price = data["Close"].iloc[-1]
            logging.info(f"Checking {symbol}: {current_price} vs {operator} {target}")

            alert_condition = (
                (operator == ">=" and current_price >= target) or
                (operator == "<=" and current_price <= target)
            )

            if alert_condition:
                for chat_id in chat_ids:
                    try:
                        await app.bot.send_message(
                            chat_id=chat_id,
                            text=f"🚨 {symbol} reached ₹{current_price:.2f} ({operator} {target})"
                        )
                    except Exception as e:
                        logging.error(f"Failed to send message to chat {chat_id}: {e}")
                del watchlist[symbol]

        except Exception as e:
            logging.exception(f"Error while checking {symbol}: {e}")

# --- Scheduler Setup ---
scheduler = BackgroundScheduler()

def schedule_check_prices():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(check_prices())
        loop.close()
    except Exception as e:
        logging.exception(f"Scheduler failed to run check_prices: {e}")


scheduler.add_job(schedule_check_prices, 'interval', minutes=2)
scheduler.start()

# --- Register Commands ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", list_alerts))

# --- Flask runner (keeps Render service alive) ---
def run_flask():
    try:
        port = int(os.environ.get("PORT", 5000))
        logging.info(f"🌐 Flask server running on port {port}")
        web_app.run(host='0.0.0.0', port=port)
    except Exception as e:
        logging.exception(f"Flask server failed: {e}")

# --- Main ---
if __name__ == '__main__':
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    logging.info("🤖 Stock Alert Bot polling started...")
    try:
        app.run_polling()
    except Exception as e:
        logging.exception(f"Telegram bot stopped: {e}")