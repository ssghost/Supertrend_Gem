import requests
import time
from datetime import datetime


API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
ACCOUNT_ID = "YOUR_ACCOUNT_ID"
PAIR = "BTC_USDT"  
BOT_ID = "YOUR_BOT_ID"

ATR_PERIOD = 10
FACTOR = 3.0
COMMISSION = 0.001  
SLIPPAGE = 3
START_DATE = datetime(2018, 1, 1)
END_DATE = datetime(2069, 12, 31)

def get_candles(pair, timeframe, limit):
    """Fetches candle data from 3Commas API."""
    url = f"https://api.3commas.io/public/api/v1/candles?pair={pair}&interval={timeframe}&limit={limit}"
    headers = {"APIKEY": API_KEY}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def calculate_atr(candles, period):
    """Calculates Average True Range."""
    atr = []
    for i in range(1, len(candles)):
        high = float(candles[i][2])
        low = float(candles[i][3])
        close_prev = float(candles[i - 1][4])
        tr = max(high - low, abs(high - close_prev), abs(low - close_prev))
        atr.append(tr)
    return sum(atr[-period:]) / period

def calculate_supertrend(candles, factor, atr_period):
    """Calculates Supertrend."""
    atr = calculate_atr(candles, atr_period)
    upper_band = []
    lower_band = []
    supertrend = []
    direction = 1  

    for i in range(atr_period, len(candles)):
        high = float(candles[i][2])
        low = float(candles[i][3])
        close = float(candles[i][4])
        basic_upper = (high + low) / 2 + factor * atr
        basic_lower = (high + low) / 2 - factor * atr

        if i > atr_period:
            if close > upper_band[-1]:
                upper = basic_upper
            else:
                upper = min(basic_upper, upper_band[-1])

            if close < lower_band[-1]:
                lower = basic_lower
            else:
                lower = max(basic_lower, lower_band[-1])

            if close > lower_band[-1]:
                direction = 1
            elif close < upper_band[-1]:
                direction = -1

            if direction == 1:
                st = lower
            else:
                st = upper

        else:
            upper = basic_upper
            lower = basic_lower
            st = lower # starting with uptrend.

        upper_band.append(upper)
        lower_band.append(lower)
        supertrend.append(st)

    return supertrend, direction

def check_date_range(timestamp):
    """Checks if the timestamp is within the specified date range."""
    candle_time = datetime.fromtimestamp(timestamp)
    return START_DATE <= candle_time <= END_DATE

def get_current_price(pair):
    """Gets the current price of a trading pair from 3Commas."""
    url = f"https://api.3commas.io/public/api/v1/ticker?pair={pair}"
    headers = {"APIKEY": API_KEY}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return float(response.json()[0]["last"])

def create_3commas_deal(bot_id, pair, price):
    """Creates a new deal in 3Commas."""
    url = f"https://api.3commas.io/public/api/v1/bots/{bot_id}/start_new_deal"
    headers = {"APIKEY": API_KEY, "Content-Type": "application/json"}
    data = {
        "pair": pair,
        "rate": price,
        "units": 0 
    }
    response = requests.post(url, headers=headers, json=data)
    response.raise_for_status()
    return response.json()

def get_active_deals(bot_id):
    """Gets all active deals for a given bot."""
    url = f"https://api.3commas.io/public/api/v1/bots/{bot_id}/deals/active"
    headers = {"APIKEY": API_KEY}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def close_deal(deal_id):
    """Closes a deal by deal id."""
    url = f"https://api.3commas.io/public/api/v1/deals/{deal_id}/cancel"
    headers = {"APIKEY": API_KEY}
    response = requests.post(url, headers=headers)
    response.raise_for_status()
    return response.json()

def main():
    """Main trading logic."""
    try:
        candles = get_candles(PAIR, "1m", 200) 
        if not candles or len(candles) < ATR_PERIOD + 1:
            print("Insufficient candle data.")
            return

        supertrend_values, direction = calculate_supertrend(candles, FACTOR, ATR_PERIOD)

        current_candle = get_candles(PAIR, "1m", 1)
        if not current_candle:
            print("Could not get current candle")
            return

        if not check_date_range(current_candle[0][0] / 1000):
            print("Outside of date range")
            active_deals = get_active_deals(BOT_ID)
            for deal in active_deals:
                close_deal(deal['id'])
            return

        current_price = get_current_price(PAIR)

        if direction < 0:
            try:
                deal_response = create_3commas_deal(BOT_ID, PAIR, current_price)
                print("3Commas deal created:", deal_response)
            except requests.exceptions.HTTPError as e:
                print(f"Failed to create 3Commas deal: {e}")
        elif direction > 0:
            active_deals = get_active_deals(BOT_ID)
            for deal in active_deals:
                close_deal(deal['id'])

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(60)