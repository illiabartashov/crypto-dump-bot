import aiohttp
import asyncio

async def get_klines(symbol: str, interval="1m", limit=200, retries=5):
    """
    Асинхронне отримання свічок Binance Futures USDT-M.
    Захищено від DNS-помилок, timeouts, rate-limit.
    """
    url = "https://fapi.binance.com/fapi/v1/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}

    for attempt in range(1, retries + 1):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=5) as resp:
                    data = await resp.json()

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

    return None
