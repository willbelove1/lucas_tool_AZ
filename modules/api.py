import pandas as pd
import requests
import logging
from datetime import datetime, timedelta
import os
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# API keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your_gemini_api_key")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7244322730:AAHRDYtejK2DHP4fzh4d67oZQ46ZNaH_MVY")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "-1002672318636")

def fetch_crypto_data(coin: str, days: int = 30) -> pd.DataFrame:
    """Lấy dữ liệu crypto từ CoinGecko."""
    logging.info(f"Fetching data for {coin}, days={days}")
    
    coin_map = {
        "BTC": "bitcoin",
        "SUI": "sui",
        "BNB": "binancecoin",
        "ETH": "ethereum",
        "ADA": "cardano",
        "SOL": "solana",
        "Pi": "pi-network"
    }
    
    coin_id = coin_map.get(coin, coin.lower())
    
    try:
        time.sleep(1)  # Tránh giới hạn API
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": days,
            "interval": "daily"
        }
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        response = session.get(url, params=params, timeout=10)
        response.raise_for_status()
        logging.info(f"Response status for {coin}: {response.status_code}, keys: {response.json().keys()}")
        data = response.json()
        
        if not data.get("prices"):
            logging.error(f"No price data for {coin_id}")
            return pd.DataFrame()
        
        prices = data["prices"]
        df = pd.DataFrame(prices, columns=["timestamp", "price"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df["high"] = df["price"] * 1.01
        df["low"] = df["price"] * 0.99
        df.set_index("timestamp", inplace=True)
        
        logging.info(f"Fetched {len(df)} rows for {coin} with columns: {df.columns.tolist()}")
        return df
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Lỗi lấy dữ liệu {coin}: {str(e)}")
        return pd.DataFrame()