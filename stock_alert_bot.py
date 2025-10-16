from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import asyncio
import os

# --- Global Storage ---
watchlist = {} # Example: {'chat_id': {'TCS.NS': 4200.0}}

BOT_TOKEN = os.getenv("BOT_TOKEN")
app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Command: /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in watchlist:
        watchlist[chat_id] = {}
    await update.message.reply_text(
        "📈 Welcome to Stock Alert Bot!\n\n"
        "Use /add <symbol> <price> to set an alert.\n"
        "Example: /add TCS.NS 4200\n\n"
        "I’ll notify you when it reaches that price!"
    )

# --- Command: /add ---
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in watchlist:
        watchlist[chat_id] = {}

    try:
        symbol = context.args[0].upper()
        price = float(context.args[1])
        watchlist[chat_id][symbol] = price
        await update.message.reply_text(f"✅ Added alert: {symbol} → ₹{price}")
    except (IndexError, ValueError):
        await update.message.reply_text("⚠️ Usage: /add SYMBOL PRICE\nExample: /add INFY.NS 1600")

# --- Command: /list ---
async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if chat_id not in watchlist or not watchlist[chat_id]:
        await update.message.reply_text("🕸️ No active alerts yet.")
        return
    msg = "🔔 Active Alerts:\n"
    for sym, val in watchlist[chat_id].items():
        msg += f"• {sym} → ₹{val}\n"
    await update.message.reply_text(msg)

# --- Price Check Logic ---
async def check_prices():
    for chat_id, alerts in list(watchlist.items()):
        for symbol, target in list(alerts.items()):
            try:
                ticker = yf.Ticker(symbol)
                data = ticker.history(period="1d", interval="1m")
                if data.empty:
                    continue
                current_price = data["Close"].iloc[-1]
                print(f"Checking {symbol}: {current_price} vs {target}")
                if current_price >= target:
                    await app.bot.send_message(
                        chat_id=chat_id,
                        text=f"🚨 {symbol} reached ₹{current_price:.2f} (Target ₹{target})"
                    )
                    del watchlist[chat_id][symbol] # Remove after alert
            except Exception as e:
                print(f"Error checking {symbol}: {e}")

# --- Scheduler Setup ---
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: asyncio.run(check_prices()), 'interval', minutes=2)
scheduler.start()

# --- Register Commands ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", list_alerts))

print("🤖 Stock Alert Bot running...")
app.run_polling()