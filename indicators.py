import asyncio
from async_binance import get_klines   # ми створили async get_klines у попередньому кроці

# ------------------------------
#   EMA CALCULATION
# ------------------------------
def calculate_ema(values, period):
    if len(values) < period:
        return None

    k = 2 / (period + 1)
    ema = values[0]

    for price in values[1:]:
        ema = price * k + ema * (1 - k)

    return ema


# ------------------------------
#   TREND DETECTION
# ------------------------------
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
    else:
        trend = "flat"

    return {
        "trend": trend,
        "ema20": round(ema20, 2),
        "ema50": round(ema50, 2),
        "ema200": round(ema200, 2)
    }


# ------------------------------
#   SCORE ENGINE
# ------------------------------
def calculate_score(symbol, candles):
    trend_data = detect_trend_strength(candles)

    score = 0

    if trend_data["trend"] == "down":
        score += 2
    elif trend_data["trend"] == "flat":
        score += 1

    recommendation = "NO_TRADE"
    if score >= 2:
        recommendation = "SHORT"

    return {
        "symbol": symbol,
        "score": score,
        "recommendation": recommendation,
        "details": {
            "trend": trend_data
        }
    }


# ------------------------------
#   ASYNC WRAPPER
# ------------------------------
async def calculate_score_async(symbol):
    candles = await get_klines(symbol, interval="1m", limit=250)
    if candles is None:
        return None

    return calculate_score(symbol, candles)
