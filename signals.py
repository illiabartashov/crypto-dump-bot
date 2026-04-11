import requests

def get_futures_symbols():
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    data = requests.get(url).json()

    symbols = []
    for s in data["symbols"]:
        if s["contractType"] == "PERPETUAL" and s["status"] == "TRADING":
            symbols.append(s["symbol"])

    return symbols

symbols = get_futures_symbols()
print(symbols)
