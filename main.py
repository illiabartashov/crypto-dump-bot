import asyncio
from config import SYMBOLS, SCAN_INTERVAL
from telegram_bot import send_telegram_signal
from indicators import calculate_score_async   # <-- важливо

async def scan_symbol(symbol):
    try:
        result = await calculate_score_async(symbol)
        if result and result["recommendation"] == "SHORT":
            send_telegram_signal(result)
    except Exception as e:
        print(f"Error scanning {symbol}: {e}")

async def monitor_all_symbols_async():
    print("🚀 Starting async 24/7 monitoring...")

    while True:
        tasks = [scan_symbol(symbol) for symbol in SYMBOLS]
        await asyncio.gather(*tasks)

        await asyncio.sleep(SCAN_INTERVAL)

if __name__ == "__main__":
    asyncio.run(monitor_all_symbols_async())
