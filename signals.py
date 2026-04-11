import requests


# ============================
# 1. Отримання списку ф'ючерсних монет
# ============================
def get_futures_symbols():
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    data = requests.get(url).json()

    symbols = []
    for s in data["symbols"]:
        if s["contractType"] == "PERPETUAL" and s["status"] == "TRADING":
            symbols.append(s["symbol"])

    return symbols


# ============================
# 2. Отримання поточної ціни монети
# ============================
def get_price(symbol: str) -> float:
    """
    Повертає поточну ціну ф'ючерсного контракту Binance USDT-M.
    """
    url = "https://fapi.binance.com/fapi/v1/ticker/price"
    params = {"symbol": symbol}

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return float(data["price"])
    except Exception as e:
        print(f"Error getting price for {symbol}: {e}")
        return None


def get_klines(symbol: str, interval="1m", limit=200):
    """
    Отримує історичні свічки Binance Futures USDT-M.
    interval: 1m, 3m, 5m, 15m, 1h, 4h, 1d ...
    limit: кількість свічок (максимум 1500)
    """
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        # Перетворюємо сирі дані у зручний формат
        candles = []
        for c in data:
            candles.append({
                "open_time": c[0],
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4]),
                "volume": float(c[5]),
                "close_time": c[6]
            })

        return candles

    except Exception as e:
        print(f"Error getting klines for {symbol}: {e}")
        return None


def calculate_rsi(candles, period=14):
    """
    Розраховує RSI на основі масиву свічок (close prices).
    Повертає RSI останньої свічки.
    """
    if len(candles) < period + 1:
        return None  # недостатньо даних

    # Витягуємо ціни закриття
    closes = [c["close"] for c in candles]

    gains = []
    losses = []

    # Рахуємо зміни між свічками
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))

    # Середні значення
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    # Якщо немає втрат → RSI = 100
    if avg_loss == 0:
        return 100

    # RS та RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)


def detect_pump(symbol: str, percent=5, minutes=5):
    """
    Визначає, чи монета виросла на X% за останні Y хвилин.
    Повертає (pump_detected: bool, change_percent: float)
    """
    # Кількість свічок = кількість хвилин
    candles = get_klines(symbol, interval="1m", limit=minutes + 1)
    if not candles or len(candles) < minutes + 1:
        return False, 0

    old_price = candles[0]["close"]
    new_price = candles[-1]["close"]

    change = ((new_price - old_price) / old_price) * 100

    if change >= percent:
        return True, round(change, 2)
    else:
        return False, round(change, 2)


def detect_volume_spike(symbol: str, multiplier=2, minutes=20):
    """
    Визначає, чи є об'єм останньої свічки більшим за середній у X разів.
    multiplier: у скільки разів об'єм має бути більшим (2 = spike x2)
    minutes: скільки свічок брати для середнього (20 = останні 20 хвилин)
    Повертає (spike_detected: bool, ratio: float)
    """
    candles = get_klines(symbol, interval="1m", limit=minutes + 1)
    if not candles or len(candles) < minutes + 1:
        return False, 0

    # Обʼєм останньої свічки
    last_volume = candles[-1]["volume"]

    # Середній обʼєм попередніх свічок
    volumes = [c["volume"] for c in candles[:-1]]
    avg_volume = sum(volumes) / len(volumes)

    if avg_volume == 0:
        return False, 0

    ratio = last_volume / avg_volume

    if ratio >= multiplier:
        return True, round(ratio, 2)
    else:
        return False, round(ratio, 2)


def get_funding_rate(symbol: str) -> float:
    """
    Отримує funding rate для ф'ючерсного контракту Binance USDT-M.
    Повертає funding rate у відсотках (наприклад 0.015 = 0.015%)
    """
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    params = {"symbol": symbol}

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return float(data["lastFundingRate"]) * 100  # переводимо у %
    except Exception as e:
        print(f"Error getting funding rate for {symbol}: {e}")
        return None


def detect_high_funding(symbol: str, threshold=0.03):
    """
    Визначає, чи funding rate вище заданого порогу.
    threshold = 0.03 означає 0.03% (стандартний перегрів)
    Повертає (high_funding: bool, funding_rate: float)
    """
    fr = get_funding_rate(symbol)
    if fr is None:
        return False, 0

    if fr >= threshold:
        return True, round(fr, 4)
    else:
        return False, round(fr, 4)
if __name__ == "__main__":
    high, fr = detect_high_funding("BTCUSDT", threshold=0.03)
    print("High Funding:", high, "Funding Rate:", fr, "%")
