import aiohttp
import asyncio
import math
from async_binance import get_klines


# ============================================================
#   EMA
# ============================================================
def calculate_ema(values, period):
    if len(values) < period:
        return None

    k = 2 / (period + 1)
    ema = values[0]

    for price in values[1:]:
        ema = price * k + ema * (1 - k)

    return ema


# ============================================================
#   RSI
# ============================================================
def calculate_rsi(candles, period=14):
    if len(candles) < period + 1:
        return None

    gains = []
    losses = []

    for i in range(1, period + 1):
        diff = candles[-i]["close"] - candles[-i - 1]["close"]
        if diff >= 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))

    avg_gain = sum(gains) / period if gains else 0
    avg_loss = sum(losses) / period if losses else 0

    if avg_loss == 0:
        return 100

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


# ============================================================
#   VWAP
# ============================================================
def calculate_vwap(candles):
    if not candles:
        return None

    total_pv = 0
    total_volume = 0

    for c in candles:
        typical_price = (c["high"] + c["low"] + c["close"]) / 3
        total_pv += typical_price * c["volume"]
        total_volume += c["volume"]

    if total_volume == 0:
        return None

    return round(total_pv / total_volume, 4)


# ============================================================
#   CVD (простий варіант)
# ============================================================
def calculate_cvd(candles):
    if not candles:
        return None

    cvd = 0
    for c in candles:
        if c["close"] > c["open"]:
            cvd += c["volume"]
        else:
            cvd -= c["volume"]

    direction = "up" if cvd > 0 else "down"
    return {"value": cvd, "direction": direction}


# ============================================================
#   TREND DETECTION
# ============================================================
def detect_trend_strength(candles):
    if not candles or len(candles) < 200:
        return {"trend": "flat", "ema20": 0, "ema50": 0, "ema200": 0}

    closes = [c["close"] for c in candles]

    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)
    ema200 = calculate_ema(closes, 200)

    if ema20 is None or ema50 is None or ema200 is None:
        return {"trend": "flat", "ema20": 0, "ema50": 0, "ema200": 0}

    if ema20 > ema50 > ema200:
        trend = "up"
    elif ema20 < ema50 < ema200:
        trend = "down"
        # trend = "down"
    else:
        trend = "flat"

    return {
        "trend": trend,
        "ema20": round(ema20, 2),
        "ema50": round(ema50, 2),
        "ema200": round(ema200, 2)
    }


# ============================================================
#   OPEN INTEREST (ASYNC)
# ============================================================
async def get_open_interest_async(symbol: str, period="5m", limit=30):
    url = "https://fapi.binance.com/futures/data/openInterestHist"
    params = {"symbol": symbol, "period": period, "limit": limit}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=5) as resp:
                data = await resp.json()

                if not isinstance(data, list):
                    return None

                return [float(item["sumOpenInterest"]) for item in data]

    except Exception:
        return None


async def detect_oi_change_async(symbol: str, percent=3, period="5m", limit=30):
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


# ============================================================
#   LIQUIDATION MAGNETS
# ============================================================
def calculate_liquidation_magnets(candles, levels_count=5):
    if not candles or len(candles) < 10:
        return []

    current_price = candles[-1]["close"]
    levels = []

    for i in range(1, len(candles) - 1):
        prev_low = candles[i - 1]["low"]
        low = candles[i]["low"]
        next_low = candles[i + 1]["low"]

        if low < prev_low and low < next_low and low < current_price:
            distance_pct = round((current_price - low) / current_price * 100, 2)
            levels.append({"price": round(low, 4), "distance": distance_pct})

    levels.sort(key=lambda x: x["distance"])

    unique = []
    seen = set()

    for lvl in levels:
        if lvl["price"] not in seen:
            unique.append(lvl)
            seen.add(lvl["price"])

    return unique[:levels_count]


# ============================================================
#   SCORE ENGINE (SYNC)
# ============================================================
def calculate_score(symbol, candles, oi_data):
    score = 0

    # 1. Trend
    trend_data = detect_trend_strength(candles)
    if trend_data["trend"] == "down":
        score += 2
    elif trend_data["trend"] == "flat":
        score += 1

    # 2. RSI
    rsi = calculate_rsi(candles)
    if rsi and rsi > 70:
        score += 1

    # 3. CVD
    cvd = calculate_cvd(candles)
    if cvd and cvd["direction"] == "down":
        score += 1

    # 4. VWAP
    vwap = calculate_vwap(candles)
    if vwap and candles[-1]["close"] < vwap:
        score += 1

    # 5. Open Interest
    if oi_data["increased"]:
        score += 1

    # 6. Liquidation Magnets
    magnets = calculate_liquidation_magnets(candles)
    if magnets and magnets[0]["distance"] <= 3:
        score += 1

    recommendation = "SHORT" if score >= 6 else "NO_TRADE"

    return {
        "symbol": symbol,
        "score": score,
        "recommendation": recommendation,
        "details": {
            "trend": trend_data,
            "rsi": rsi,
            "cvd": cvd,
            "vwap": vwap,
            "open_interest": oi_data,
            "liquidation_magnets": magnets
        }
    }


# ============================================================
#   ASYNC SCORE ENGINE
# ============================================================
async def calculate_score_async(symbol):
    candles = await get_klines(symbol, interval="1m", limit=250)
    if candles is None:
        return None

    oi_data = await detect_oi_change_async(symbol)

    return calculate_score(symbol, candles, oi_data)
