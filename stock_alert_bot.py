from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.background import BackgroundScheduler
import yfinance as yf
import asyncio
import re
import os

# --- Global Storage ---
# Structure: {chat_id: {symbol: {"target": float, "operator": ">=" or "<="}}}
watchlist = {}

BOT_TOKEN = os.getenv("BOT_TOKEN")
app = ApplicationBuilder().token(BOT_TOKEN).build()


# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📈 Welcome to Stock Alert Bot!\n\n"
        "Use /add <symbol> <operator> <price>\n"
        "Example:\n"
        " /add TCS.NS >= 4200\n"
        " /add INFY.NS <= 1600\n\n"
        "I’ll alert you when the condition is met!"
    )


# --- /add ---
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Join full text (to support spaces)
        text = " ".join(context.args)
        # Pattern like SYMBOL >= PRICE or SYMBOL <= PRICE
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


# --- /list ---
async def list_alerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id not in watchlist or not watchlist[chat_id]:
        await update.message.reply_text("🕸️ No active alerts yet.")
        return

    msg = "🔔 Active Alerts:\n"
    for sym, info in watchlist[chat_id].items():
        msg += f"• {sym} {info['operator']} ₹{info['target']}\n"
    await update.message.reply_text(msg)


# --- Price Check ---
async def check_prices():
    for chat_id, stocks in list(watchlist.items()):
        for symbol, info in list(stocks.items()):
            target = info["target"]
            operator = info["operator"]

            ticker = yf.Ticker(symbol)
            data = ticker.history(period="1d")
            if data.empty:
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

        if not watchlist[chat_id]:
            del watchlist[chat_id]


# --- Scheduler Setup ---
scheduler = BackgroundScheduler()
scheduler.add_job(lambda: asyncio.run(check_prices()), "interval", minutes=2)
scheduler.start()


# --- Register Commands ---
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("add", add))
app.add_handler(CommandHandler("list", list_alerts))

print("🤖 Stock Alert Bot running...")
app.run_polling()