import time
from signals import calculate_score
from telegram_bot import send_telegram_signal
from config import SYMBOLS, SCAN_INTERVAL


def monitor_all_symbols():
    print("🚀 Starting 24/7 monitoring...")

    while True:
        for symbol in SYMBOLS:
            try:
                result = calculate_score(symbol)

                score = result["score"]
                recommendation = result["recommendation"]

                # Вивід у консоль (для дебагу)
                print(f"[{symbol}] Score={score} → {recommendation}")

                # Якщо SHORT — надсилаємо сигнал
                if recommendation == "SHORT":
                    send_telegram_signal(result)

            except Exception as e:
                print(f"Error scanning {symbol}: {e}")

            # маленька пауза між монетами, щоб не ловити rate-limit
            time.sleep(0.3)

        # пауза між повними циклами
        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    monitor_all_symbols()
