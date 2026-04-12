import requests
from config import TELEGRAM_TOKEN, CHAT_ID


def send_telegram_signal(result):
    symbol = result["symbol"]
    score = result["score"]
    trend = result["details"]["trend"]["trend"]

    magnets = result["details"]["liquidation_magnets"]

    text = f"🔥 SHORT SIGNAL DETECTED 🔥\n\n"
    text += f"Symbol: {symbol}\n"
    text += f"Score: {score}/10\n"
    text += f"Trend: {trend}\n\n"
    text += "📉 Liquidation Zones:\n"

    for z in magnets:
        text += f"• {z['price']} ({z['distance']}%)\n"

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}

    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram error: {e}")
