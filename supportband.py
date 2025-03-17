import requests
import time
from datetime import datetime

API_KEY = "YOUR_API_KEY"
API_SECRET = "YOUR_API_SECRET"
ACCOUNT_ID = "YOUR_ACCOUNT_ID"  
PAIR = "BTC_USDT"  
BOT_ID = "YOUR_BOT_ID" 


EMA_LENGTH = 3528
SMA_LENGTH = 3360
EMA2_LENGTH = 350
EMA_TIMEFRAME = "1h"  
SMA_TIMEFRAME = "1h"
EMA2_TIMEFRAME = "1d"
COMMISSION = 0.001  
SLIPPAGE = 3
START_DATE = datetime(2018, 1, 1)
END_DATE = datetime(2069, 12, 30) 

def get_candles(pair, timeframe, limit):
    """Fetches candle data from 3Commas API."""
    url = f"https://api.3commas.io/public/api/v1/candles?pair={pair}&interval={timeframe}&limit={limit}"
    headers = {"APIKEY": API_KEY}
    response = requests.get(url, headers=headers)
    response.raise_for_status()  
    return response.json()

def calculate_ema(data, length):
    """Calculates Exponential Moving Average."""
    if not data:
        return None
    ema = [sum(candle[4] for candle in data[:length]) / length]
    multiplier = 2 / (length + 1)
    for i in range(length, len(data)):
        ema.append((data[i][4] - ema[-1]) * multiplier + ema[-1])
    return ema

def calculate_sma(data, length):
    """Calculates Simple Moving Average."""
    if not data:
        return None
    sma = []
    for i in range(length - 1, len(data)):
        sma.append(sum(candle[4] for candle in data[i - length + 1 : i + 1]) / length)
    return sma

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
    url = "https://api.3commas.io/public/api/v1/bots/{}/start_new_deal".format(bot_id)
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
        ema_candles = get_candles(PAIR, EMA_TIMEFRAME, EMA_LENGTH * 2) 
        sma_candles = get_candles(PAIR, SMA_TIMEFRAME, SMA_LENGTH * 2)
        ema2_candles = get_candles(PAIR, EMA2_TIMEFRAME, EMA2_LENGTH * 2)

        if not ema_candles or not sma_candles or not ema2_candles:
            print("Failed to retrieve candle data.")
            return

        ema_values = calculate_ema(ema_candles, EMA_LENGTH)
        sma_values = calculate_sma(sma_candles, SMA_LENGTH)
        ema2_values = calculate_ema(ema2_candles, EMA2_LENGTH)

        
        current_candle = get_candles(PAIR, "1m", 1) 
        if not current_candle:
            print("Could not get current candle")
            return

        if not check_date_range(current_candle[0][0]/1000): 
            print("Outside of date range")
            active_deals = get_active_deals(BOT_ID)
            for deal in active_deals:
                close_deal(deal['id'])
            return

        current_price = get_current_price(PAIR)

        if ema_values and sma_values and ema2_values:

            last_ema = ema_values[-1]
            last_sma = sma_values[-1]
            last_ema2 = ema2_values[-1]

            if last_ema > last_sma:
                print("Long signal triggered.")
                try:
                    deal_response = create_3commas_deal(BOT_ID, PAIR, current_price)
                    print("3Commas deal created:", deal_response)
                except requests.exceptions.HTTPError as e:
                    print(f"Failed to create 3Commas deal: {e}")

            else:
                print("No signal.")

    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    while True:
        main()
        time.sleep(60) 