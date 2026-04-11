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


def get_open_interest(symbol: str, period="5m", limit=30):
    """
    Отримує історію Open Interest для монети.
    period: 5m, 15m, 1h, 4h, 1d
    limit: кількість точок (максимум 500)
    Повертає список значень OI.
    """
    url = "https://fapi.binance.com/futures/data/openInterestHist"
    params = {
        "symbol": symbol,
        "period": period,
        "limit": limit
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        oi_values = [float(item["sumOpenInterest"]) for item in data]
        return oi_values

    except Exception as e:
        print(f"Error getting OI for {symbol}: {e}")
        return None

def detect_oi_increase(symbol: str, percent=3, period="5m", limit=30):
    """
    Визначає, чи Open Interest виріс на X% за останній період.
    Повертає (oi_increased: bool, change_percent: float)
    """
    oi = get_open_interest(symbol, period=period, limit=limit)
    if not oi or len(oi) < 2:
        return False, 0

    old = oi[0]
    new = oi[-1]

    change = ((new - old) / old) * 100

    if change >= percent:
        return True, round(change, 2)
    else:
        return False, round(change, 2)


def calculate_vwap(candles):
    """
    Розраховує VWAP на основі масиву свічок.
    Повертає VWAP останньої свічки.
    """
    if not candles or len(candles) == 0:
        return None

    cumulative_pv = 0
    cumulative_volume = 0

    for c in candles:
        typical_price = (c["high"] + c["low"] + c["close"]) / 3
        volume = c["volume"]

        cumulative_pv += typical_price * volume
        cumulative_volume += volume

    if cumulative_volume == 0:
        return None

    return round(cumulative_pv / cumulative_volume, 4)

def detect_vwap_deviation(symbol: str, minutes=30, threshold=1.5):
    """
    Визначає, чи ціна відірвалася від VWAP.
    threshold = 1.5 означає 1.5% вище VWAP.
    Повертає (deviation_detected: bool, deviation_percent: float)
    """
    candles = get_klines(symbol, interval="1m", limit=minutes)
    if not candles:
        return False, 0

    vwap = calculate_vwap(candles)
    last_price = candles[-1]["close"]

    deviation = ((last_price - vwap) / vwap) * 100

    if deviation >= threshold:
        return True, round(deviation, 2)
    else:
        return False, round(deviation, 2)


def calculate_cvd(candles):
    """
    Розраховує CVD (Cumulative Volume Delta) на основі напрямку свічок.
    Повертає список значень CVD.
    """
    cvd = []
    cumulative = 0

    for c in candles:
        if c["close"] > c["open"]:
            cumulative += c["volume"]  # покупці сильні
        elif c["close"] < c["open"]:
            cumulative -= c["volume"]  # продавці сильні

        cvd.append(cumulative)

    return cvd

def detect_cvd_divergence(symbol: str, minutes=30):
    """
    Визначає дивергенцію:
    - ціна росте
    - CVD падає
    Повертає (divergence_detected: bool, price_change: float, cvd_change: float)
    """
    candles = get_klines(symbol, interval="1m", limit=minutes)
    if not candles or len(candles) < 2:
        return False, 0, 0

    # Ціна
    old_price = candles[0]["close"]
    new_price = candles[-1]["close"]
    price_change = ((new_price - old_price) / old_price) * 100

    # CVD
    cvd = calculate_cvd(candles)
    old_cvd = cvd[0]
    new_cvd = cvd[-1]
    cvd_change = ((new_cvd - old_cvd) / abs(old_cvd) * 100) if old_cvd != 0 else 0

    # Дивергенція: ціна росте, CVD падає
    if price_change > 0 and cvd_change < 0:
        return True, round(price_change, 2), round(cvd_change, 2)

    return False, round(price_change, 2), round(cvd_change, 2)


def get_liquidations(symbol: str, limit=100):
    """
    Отримує останні ліквідації з Binance Futures.
    Повертає список ліквідацій з ціною та об'ємом.
    """
    url = "https://fapi.binance.com/futures/data/liquidationOrders"
    params = {
        "symbol": symbol,
        "limit": limit
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        liquidations = []
        for item in data:
            liquidations.append({
                "price": float(item["price"]),
                "qty": float(item["origQty"]),
                "side": item["side"]  # BUY = ліквідація шортів, SELL = ліквідація лонгів
            })

        return liquidations

    except Exception as e:
        print(f"Error getting liquidations for {symbol}: {e}")
        return None

def cluster_liquidations(liquidations, cluster_percent=0.2):
    """
    Групує ліквідації в кластери за ціною.
    cluster_percent = ширина кластера у %
    Повертає список кластерів: (center_price, total_volume)
    """
    if not liquidations:
        return []

    clusters = {}

    for liq in liquidations:
        price = liq["price"]
        qty = liq["qty"]

        # округляємо ціну до кластера
        cluster_key = round(price / (1 + cluster_percent / 100), 2)

        if cluster_key not in clusters:
            clusters[cluster_key] = 0

        clusters[cluster_key] += qty

    # перетворюємо в список
    result = [{"price": k, "volume": v} for k, v in clusters.items()]

    # сортуємо за об'ємом
    result.sort(key=lambda x: x["volume"], reverse=True)

    return result
def detect_liquidation_cluster(symbol: str, distance_percent=1.0):
    """
    Визначає, чи ціна знаходиться близько до великого кластера ліквідацій.
    distance_percent = максимальна дистанція до кластера у %
    Повертає (detected: bool, cluster_price: float, distance: float)
    """
    liquidations = get_liquidations(symbol)
    if not liquidations:
        return False, 0, 0

    clusters = cluster_liquidations(liquidations)
    if not clusters:
        return False, 0, 0

    # найбільший кластер
    top_cluster = clusters[0]
    cluster_price = top_cluster["price"]

    # поточна ціна
    candles = get_klines(symbol, interval="1m", limit=1)
    if not candles:
        return False, 0, 0

    price = candles[-1]["close"]

    # відстань у %
    distance = abs(price - cluster_price) / cluster_price * 100

    if distance <= distance_percent:
        return True, cluster_price, round(distance, 2)

    return False, cluster_price, round(distance, 2)
