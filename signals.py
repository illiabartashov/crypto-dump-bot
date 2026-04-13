import requests
import time

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


import aiohttp
import asyncio
import ssl


async def get_klines(symbol: str, interval="1m", limit=200, retries=5):
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}

    # 🔒 Вимикаємо SSL‑перевірку (macOS fix)
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5, ssl=ssl_context) as resp:

                    # Binance інколи повертає HTML або пусту відповідь → ловимо
                    try:
                        data = await resp.json()
                    except:
                        print(f"Binance returned non‑JSON for {symbol} (attempt {attempt}/{retries})")
                        await asyncio.sleep(0.3)
                        continue

                    # Якщо Binance повернув помилку
                    if not isinstance(data, list):
                        print(f"Invalid klines format for {symbol}: {data}")
                        await asyncio.sleep(0.3)
                        continue

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
            print(f"Error getting klines for {symbol}: {e} (attempt {attempt}/{retries})")
            await asyncio.sleep(0.3)

    # Якщо після всіх спроб нічого не вийшло
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

def detect_rsi_overbought(symbol: str, period=14, threshold=70):
    """
    Визначає, чи RSI знаходиться в зоні перекупленості.
    threshold = 70 → класичний рівень
    Повертає (overbought: bool, rsi_value: float)
    """
    candles = get_klines(symbol, interval="1m", limit=period + 1)
    if not candles or len(candles) < period:
        return False, 0

    closes = [c["close"] for c in candles]

    # Розрахунок RSI
    gains = []
    losses = []

    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        if diff > 0:
            gains.append(diff)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(diff))

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    rsi = round(rsi, 2)

    return (rsi >= threshold), rsi


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
def detect_funding_extreme(symbol: str, threshold=0.01):
    """
    Визначає, чи funding rate перегрітий.
    threshold = 0.01 → 1%
    Повертає (extreme: bool, funding_value: float)
    """
    url = "https://fapi.binance.com/fapi/v1/premiumIndex"
    params = {"symbol": symbol}

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()

        funding = float(data["lastFundingRate"])

        # якщо funding > 1% → перегрів лонгів
        if funding >= threshold:
            return True, round(funding * 100, 4)

        return False, round(funding * 100, 4)

    except Exception as e:
        print(f"Funding error for {symbol}: {e}")
        return False, 0


import aiohttp
import asyncio


async def get_open_interest_async(symbol: str, period="5m", limit=30):
    """
    Отримує історію Open Interest (async).
    Повертає список значень OI або None.
    """
    url = "https://fapi.binance.com/futures/data/openInterestHist"
    params = {
        "symbol": symbol,
        "period": period,
        "limit": limit
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=5) as resp:
                data = await resp.json()

                if not isinstance(data, list):
                    return None

                oi_values = [float(item["sumOpenInterest"]) for item in data]
                return oi_values

    except Exception as e:
        print(f"Error getting OI for {symbol}: {e}")
        return None



async def detect_oi_change_async(symbol: str, percent=3, period="5m", limit=30):
    """
    Визначає зміну Open Interest.
    Повертає словник:
    {
        "increased": True/False,
        "change": float
    }
    """
    oi = await get_open_interest_async(symbol, period=period, limit=limit)

    if not oi or len(oi) < 2:
        return {"increased": False, "change": 0}

    old = oi[0]
    new = oi[-1]

    change = ((new - old) / old) * 100

    return {
        "increased": change >= percent,
        "change": round(change, 2)
    }

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


def get_oi_history(symbol: str, period="5m", limit=288):
    url = "https://fapi.binance.com/futures/data/openInterestHist"
    params = {"symbol": symbol, "period": period, "limit": limit}

    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        return [float(i["sumOpenInterest"]) for i in data]
    except:
        return []

def build_liquidation_heatmap(symbol: str, period="5m", limit=288):
    candles = get_klines(symbol, interval=period, limit=limit)
    oi = get_oi_history(symbol, period=period, limit=limit)

    if not candles or not oi or len(candles) != len(oi):
        return []

    heatmap = []

    for i in range(1, len(oi)):
        delta = oi[i] - oi[i-1]

        if delta > 0:  # відкрилися нові позиції → потенційні ліквідації
            heatmap.append({
                "price": candles[i]["close"],
                "oi_added": delta
            })

    return heatmap

def cluster_heatmap_zones(heatmap, cluster_percent=1.0):
    clusters = {}

    for h in heatmap:
        price = h["price"]
        oi_added = h["oi_added"]

        cluster_key = round(price / (1 + cluster_percent / 100), 2)

        if cluster_key not in clusters:
            clusters[cluster_key] = 0

        clusters[cluster_key] += oi_added

    result = [{"price": k, "oi": v} for k, v in clusters.items()]
    result.sort(key=lambda x: x["oi"], reverse=True)

    return result

def get_top_liquidation_magnets(symbol: str, distance_percent=3.0, top_n=3):
    """
    Повертає топ‑3 ліквідаційні магнітні зони:
    - price: рівень зони
    - oi: сила зони (скільки OI додано)
    - distance: відстань до поточної ціни у %
    - is_magnet: чи зона в межах distance_percent
    """
    heatmap = build_liquidation_heatmap(symbol)
    clusters = cluster_heatmap_zones(heatmap)

    if not clusters:
        return []

    # беремо топ‑N зон
    clusters = clusters[:top_n]

    # поточна ціна
    candles = get_klines(symbol, interval="1m", limit=1)
    price = candles[-1]["close"]

    result = []

    for cl in clusters:
        cluster_price = cl["price"]
        oi = cl["oi"]

        distance = abs(price - cluster_price) / cluster_price * 100
        is_magnet = distance <= distance_percent

        result.append({
            "price": cluster_price,
            "oi": round(oi, 2),
            "distance": round(distance, 2),
            "is_magnet": is_magnet
        })

    return result

def calculate_ema(values, period):
    """
    Розрахунок EMA вручну (без бібліотек).
    """
    if len(values) < period:
        return None

    k = 2 / (period + 1)
    ema = values[0]

    for price in values[1:]:
        ema = price * k + ema * (1 - k)

    return ema


def detect_trend_strength(symbol: str):
    candles = get_klines(symbol, interval="1m", limit=250)
    if not candles or len(candles) < 200:
        return "flat", 0, 0, 0

    closes = [c["close"] for c in candles]

    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)
    ema200 = calculate_ema(closes, 200)

    # Якщо хоч одна EMA не порахувалась — тренд нейтральний
    if ema20 is None or ema50 is None or ema200 is None:
        return "flat", ema20 or 0, ema50 or 0, ema200 or 0

    # Логіка тренду
    if ema20 > ema50 > ema200:
        trend = "up"
    elif ema20 < ema50 < ema200:
        trend = "down"
    else:
        trend = "flat"

    return trend, round(ema20, 2), round(ema50, 2), round(ema200, 2)


async def calculate_score(symbol: str):
    score = 0
    details = {}

    trend, ema20, ema50, ema200 = detect_trend_strength(symbol)
    details["trend"] = {
        "trend": trend,
        "ema20": ema20,
        "ema50": ema50,
        "ema200": ema200
    }

    # Ваги тренду
    if trend == "down":
        score += 2
    elif trend == "flat":
        score += 1
    # якщо trend == "up" → score += 0


    # 1) Pump
    pump_detected, pump_change = detect_pump(symbol)
    details["pump"] = {"detected": pump_detected, "change_percent": pump_change}
    if pump_detected:
        score += 2

    # 2) Volume Spike
    vol_spike, vol_ratio = detect_volume_spike(symbol)
    details["volume_spike"] = {"detected": vol_spike, "ratio": vol_ratio}
    if vol_spike:
        score += 1

    # 3) Funding
    funding_extreme, funding_value = detect_funding_extreme(symbol)
    details["funding"] = {"extreme": funding_extreme, "value": funding_value}
    if funding_extreme:
        score += 1

    # 4) Open Interest
    oi_up, oi_change = detect_oi_increase(symbol, percent=3)
    details["open_interest"] = {"increased": oi_up, "change_percent": oi_change}
    if oi_up:
        score += 1

    # 5) VWAP
    vwap_dev, vwap_pct = detect_vwap_deviation(symbol, minutes=30, threshold=1.5)
    details["vwap"] = {"deviation": vwap_dev, "percent": vwap_pct}
    if vwap_dev:
        score += 1

    # 6) CVD Divergence
    cvd_div, price_chg, cvd_chg = detect_cvd_divergence(symbol, minutes=30)
    details["cvd_divergence"] = {
        "divergence": cvd_div,
        "price_change": price_chg,
        "cvd_change": cvd_chg
    }
    if cvd_div:
        score += 2

    # 7) Liquidation Heatmap (топ‑3)
    magnets = get_top_liquidation_magnets(symbol, distance_percent=3.0, top_n=3)
    details["liquidation_magnets"] = magnets

    any_magnet_near = any(z["is_magnet"] for z in magnets) if magnets else False
    if any_magnet_near:
        score += 2

    # 8) RSI
    rsi_overbought, rsi_value = detect_rsi_overbought(symbol)
    details["rsi"] = {"overbought": rsi_overbought, "value": rsi_value}
    if rsi_overbought:
        score += 1

    # Рекомендація
    recommendation = evaluate_recommendation(score)

    return {
        "symbol": symbol,
        "score": score,
        "recommendation": recommendation,
        "details": details
    }
def evaluate_recommendation(score: int) -> str:
    if score >= 6:
        return "SHORT"
    elif 3 <= score < 6:
        return "WATCH"
    else:
        return "NO_TRADE"

def scan_symbols(symbols: list):
    results = []
    for s in symbols:
        res = calculate_score(s)
        results.append(res)
    return results
result = calculate_score("BTCUSDT")
print(result)
