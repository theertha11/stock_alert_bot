from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Define a simple command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #await update.message.reply_text("Hello! I'm your bot 👋")
    await update.message.reply_text("I'm not your Bot. Now Fuck off..! 👋")

# Main entry
app = ApplicationBuilder().token("8286321526:AAHV5f8RKBq-oDGPK2BQkAucueBRbPfp1WI").build()

app.add_handler(CommandHandler("start", start))

print("Bot running...")
app.run_polling()



#-------------------------------------------------------------------------------------#
#The code which failed the first deployment, before binding to a port

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import asyncio
import os

# --- Global Storage for Simplicity ---
watchlist = {} # Example: {'TCS.NS': 4200.0}

#BOT_TOKEN = "8286321526:AAHV5f8RKBq-oDGPK2BQkAucueBRbPfp1WI"
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = ApplicationBuilder().token(BOT_TOKEN).build()

# --- Command: /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await asyncio.sleep(2) # 2-second delay to avoid rate-limit
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        if data.empty:
            print(f"{symbol}: No data found, possibly delisted.")
            continue
        current_price = data["Close"].iloc[-1]
        print(f"Checking {symbol}: {current_price} vs {target}")
        if current_price >= target:
            for chat in app.chat_data.keys():
                await app.bot.send_message(
                    chat_id=chat,
                    text=f"🚨 {symbol} reached ₹{current_price:.2f} (Target ₹{target})"
                )
            del watchlist[symbol] # Remove after alert

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