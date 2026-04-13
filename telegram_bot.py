import aiohttp
from config import TELEGRAM_TOKEN, CHAT_ID


async def send_message(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text
    }

    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, data=payload)
    except Exception as e:
        print(f"Telegram error: {e}")


async def send_telegram_signal(result):
    symbol = result["symbol"]
    score = result["score"]
    trend = result["details"]["trend"]["trend"]

    rsi = result["details"]["rsi"]
    cvd = result["details"]["cvd"]
    vwap = result["details"]["vwap"]
    oi = result["details"]["open_interest"]
    magnets = result["details"]["liquidation_magnets"]

    # -----------------------------
    #   Формування повідомлення
    # -----------------------------
    text = f"🔥 SHORT SIGNAL DETECTED 🔥\n\n"
    text += f"Symbol: {symbol}\n"
    text += f"Score: {score}/10\n"
    text += f"Trend: {trend}\n\n"

    # --- Indicators ---
    text += "📊 Indicators:\n"
    text += f"• RSI: {rsi}\n"
    text += f"• CVD: {cvd['direction']} ({round(cvd['value'], 2)})\n"
    text += f"• VWAP: {vwap}\n"
    text += f"• OI Change: {oi['change']}% ({'UP' if oi['increased'] else 'DOWN'})\n\n"

    # --- Liquidation Magnets ---
    text += "📉 Liquidation Zones:\n"
    if magnets:
        for z in magnets:
            text += f"• {z['price']} ({z['distance']}%)\n"
    else:
        text += "No liquidation magnets detected\n"

    # Надсилання
    await send_message(text)
