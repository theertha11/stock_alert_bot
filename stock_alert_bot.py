from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import asyncio
import re
import os
import threading
from flask import Flask

# --- Flask app to bind a port (for Render) ---
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "🟢 Stock Alert Bot is running on Render!"

# --- Global Storage ---
# Structure: {chat_id: {symbol: {"target": float, "operator": ">=" or "<="}}}
watchlist = {}

BOT_TOKEN = os.getenv("BOT_TOKEN")  # BOT_TOKEN should be set in Render environment
app = ApplicationBuilder().token(BOT_TOKEN).build()


# --- /start command ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📈 Welcome to Stock Alert Bot!\n\n"
        "Use /add <symbol> <operator> <price>\n"
        "Example:\n"
        "  /add TCS.NS >= 4200\n"
        "  /add INFY.NS <= 1600\n\n"
        "I’ll alert you when the condition is met!"
    )


# --- /add command ---
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Join text and parse with regex
        text = " ".join(context.args)
        match = re.match(r"^([A-Za-z0-9\.\-]+)\s*(>=|<=)\s*(\d+(\.\d+)?)$", text)
        if not match:
            raise ValueError("Invalid format")

        symbol = match.group(1).upper()
        operator = match.group(2)
        target = float(match.group(3))
        chat_id = update.message.chat_id

        if chat_id not in watchlist:
            watchlist[chat_id] = {}

        watchlist[chat_id][symbol] = {"target": target, "operator": operator}

        await update.message.reply_text(
            f"✅ Added alert for {symbol}: {operator} ₹{target}"
        )
    except Exception:
        await update.message.reply_text(
            "⚠️ Usage: /add SYMBOL >= PRICE or /add SYMBOL <= PRICE\n"
            "Example: /add TCS.NS >= 4200"
        )


# --- /list command ---
async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in watchlist or not watchlist[chat_id]:
        await update.message.reply_text("🕸️ No active alerts yet.")
        return

    msg = "🔔 Active Alerts:\n"
    for sym, info in watchlist[chat_id].items():
        msg += f"• {sym} {info['operator']} ₹{info['target']}\n"
    await update.message.reply_text(msg)


# --- Price checking logic ---
async def check_prices():
    for chat_id, stocks in list(watchlist.items()):
        for symbol, info in list(stocks.items()):
            target = info["target"]
            operator = info["operator"]

            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d")
                if data.empty:
                    print(f"{symbol}: No data found (maybe delisted)")
                    continue

                current_price = data["Close"].iloc[-1]
                print(f"Checking {symbol}: {current_price} {operator} {target}")

                alert_triggered = (
                    (operator == ">=" and current_price >= target)
                    or (operator == "<=" and current_price <= target)
                )

                if alert_triggered:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=(
                            f"🚨 {symbol} reached ₹{current_price:.2f} "
                            f"({operator} ₹{target})"
                        ),
                    )
                    del watchlist[chat_id][symbol]
            except Exception as e:
                print(f"Error checking {symbol}: {e}")

        if not watchlist[chat_id]:
            del watchlist[chat_id]


# --- Scheduler setup ---
scheduler = BackgroundScheduler()

def schedule_check_prices():
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    asyncio.run_coroutine_threadsafe(check_prices(), loop)

scheduler.add_job(schedule_check_prices, "interval", minutes=2)
scheduler.start()


# --- Register commands ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", list_alerts))


# --- Run Flask in background thread ---
def run_flask():
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Flask server running on port {port}")
    web_app.run(host="0.0.0.0", port=port)


# --- Main entry point ---
if __name__ == "__main__":
    # Run Flask server on background thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # Start Telegram bot polling
    print("🤖 Stock Alert Bot polling started...")
    app.run_polling()