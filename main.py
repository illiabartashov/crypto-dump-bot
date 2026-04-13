import asyncio
from config import SYMBOLS, SCAN_INTERVAL
from telegram_bot import send_telegram_signal, send_message
from indicators import calculate_score_async


async def scan_symbol(symbol):
    try:
        result = await calculate_score_async(symbol)
        if result and result["recommendation"] == "SHORT":
            await send_telegram_signal(result)
        return result
    except Exception as e:
        print(f"Error scanning {symbol}: {e}")
        return None


async def monitor_all_symbols_async():
    print("🚀 Starting async 24/7 monitoring...")
    await send_message("🤖 Bot started and running!")

    heartbeat_timer = 0  # лічильник секунд

    while True:
        # --- Сканування всіх монет ---
        tasks = [scan_symbol(symbol) for symbol in SYMBOLS]
        results = await asyncio.gather(*tasks)

        # --- Heartbeat кожні 10 хвилин ---
        heartbeat_timer += SCAN_INTERVAL
        if heartbeat_timer >= 600:  # 600 секунд = 10 хвилин
            avg_score = sum(r["score"] for r in results if r) / max(len([r for r in results if r]), 1)

            msg = (
                f"💓 Heartbeat\n"
                f"Bot alive and scanning {len(SYMBOLS)} symbols\n"
                f"Average score: {round(avg_score, 2)}\n"
                f"Last scan OK"
            )

            print(msg)
            await send_message(msg)

            heartbeat_timer = 0

        await asyncio.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    asyncio.run(monitor_all_symbols_async())
