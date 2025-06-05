import pandas as pd
import numpy as np
from ta.momentum import RSIIndicator
from ta.trend import MACD, ADXIndicator
from ta.volatility import BollingerBands
import streamlit as st
import logging
from datetime import datetime
from modules.api import GEMINI_API_KEY
from modules.notifications import send_telegram_message
from modules.plotting import plot_data
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json

def calculate_fibonacci_levels(df: pd.DataFrame) -> dict:
    """Tính các mức Fibonacci."""
    logging.info("Tính Fibonacci levels")
    try:
        high_price = df['high'].max()
        low_price = df['low'].min()
        diff = high_price - low_price
        levels = {
            'fib_0.0': low_price,
            'fib_0.236': low_price + diff * 0.236,
            'fib_0.382': low_price + diff * 0.382,
            'fib_0.5': low_price + diff * 0.5,
            'fib_0.618': low_price + diff * 0.618,
            'fib_0.786': low_price + diff * 0.786,
            'fib_1.0': high_price
        }
        logging.info(f"Fibonacci levels: {levels}")
        return levels
    except Exception as e:
        logging.error(f"Lỗi tính Fibonacci: {str(e)}")
        return {}

def is_near_fib_level(price: float, fib_levels: dict, tolerance: float = 0.01) -> str:
    """Kiểm tra giá gần mức Fibonacci."""
    logging.info(f"Kiểm tra Fib level cho giá {price}")
    try:
        for level_name, level_price in fib_levels.items():
            if abs(price - level_price) / price < tolerance:
                logging.info(f"Giá gần {level_name}: {level_price}")
                return level_name
        return None
    except Exception as e:
        logging.error(f"Lỗi kiểm tra Fib level: {str(e)}")
        return None

def get_support_resistance(df: pd.DataFrame, fib_levels: dict) -> tuple:
    """Lấy hỗ trợ và kháng cự."""
    logging.info("Tính hỗ trợ và kháng cự")
    try:
        support = min([fib_levels['fib_0.236'], fib_levels['fib_0.382'], fib_levels['fib_0.5']])
        resistance = max([fib_levels['fib_0.618'], fib_levels['fib_0.786'], fib_levels['fib_1.0']])
        logging.info(f"Support: {support}, Resistance: {resistance}")
        return support, resistance
    except Exception as e:
        logging.error(f"Lỗi tính hỗ trợ/kháng cự: {str(e)}")
        return 0, 0

def get_trend(latest_data: pd.Series) -> str:
    """Xác định xu hướng."""
    logging.info("Xác định xu hướng")
    try:
        macd = float(latest_data['macd']) if not pd.isna(latest_data['macd']) else 0
        macd_signal = float(latest_data['macd_signal']) if not pd.isna(latest_data['macd_signal']) else 0
        adx = float(latest_data.get('adx', 20)) if not pd.isna(latest_data.get('adx', 20)) else 20
        if macd > macd_signal and adx > 25:
            return "Tăng"
        elif macd < macd_signal and adx > 25:
            return "Giảm"
        return "Đi ngang"
    except Exception as e:
        logging.error(f"Lỗi xác định xu hướng: {str(e)}")
        return "Đi ngang"

def get_gemini_recommendation(latest_data: pd.Series, fib_level: str, support: float, resistance: float, coin: str) -> dict:
    """Lấy khuyến nghị từ Gemini API."""
    logging.info(f"Gọi Gemini API cho {coin}")
    if not GEMINI_API_KEY:
        logging.warning("Thiếu GEMINI_API_KEY, không gọi được Gemini")
        # Fallback strategy
        trend = get_trend(latest_data)
        rsi = float(latest_data['rsi']) if not pd.isna(latest_data['rsi']) else 50.0
        price = float(latest_data['price']) if not pd.isna(latest_data['price']) else 0.0
        strategy = "Giữ"
        target = []
        if trend == "Tăng" and rsi < 70:
            strategy = "Nên Mua vì giá đang tăng và chưa vào vùng quá mua."
            target = [resistance + 0.1 * (resistance - support), resistance + 0.2 * (resistance - support)]
        elif trend == "Giảm" and rsi > 30:
            strategy = "Nên Bán vì giá đang giảm và chưa vào vùng quá bán."
            target = [support - 0.1 * (resistance - support), support - 0.2 * (resistance - support)]
        return {
            "strategy": [
                {
                    "trend": f"Thị trường đang {trend.lower()}",
                    "strategy": strategy,
                    "target": target
                }
            ]
        }
    
    try:
        price = float(latest_data['price']) if not pd.isna(latest_data['price']) else 0.0
        rsi = float(latest_data['rsi']) if not pd.isna(latest_data['rsi']) and isinstance(latest_data['rsi'], (int, float)) else 0.0
        macd = float(latest_data['macd']) if not pd.isna(latest_data['macd']) and isinstance(latest_data['macd'], (int, float)) else 0.0
        macd_signal = float(latest_data['macd_signal']) if not pd.isna(latest_data['macd_signal']) and isinstance(latest_data['macd_signal'], (int, float)) else 0.0
        bb_high = float(latest_data['bb_high']) if not pd.isna(latest_data['bb_high']) and isinstance(latest_data['bb_high'], (int, float)) else 0.0
        bb_low = float(latest_data['bb_low']) if not pd.isna(latest_data['bb_low']) and isinstance(latest_data['bb_low'], (int, float)) else 0.0
        adx = float(latest_data.get('adx', 20)) if not pd.isna(latest_data.get('adx', 20)) and isinstance(latest_data.get('adx', 20), (int, float)) else 20.0
        
        logging.info(f"Dữ liệu Gemini: price={price}, rsi={rsi}, macd={macd}, macd_signal={macd_signal}, adx={adx}")
        
        prompt = (
            f"Bạn là một chuyên gia giao dịch tiền mã hóa (crypto trading expert), nhiệm vụ là phân tích dữ liệu kỹ thuật và đưa ra nhận định, chiến lược đơn giản, dễ hiểu, phù hợp cho người mới bắt đầu (entry-level trader).\n\n"
            f"Dữ liệu kỹ thuật của đồng {coin} như sau:\n"
            f"- Giá hiện tại: ${price:,.2f}\n"
            f"- **RSI (Relative Strength Index)**: {rsi:.1f} → mức quá bán nếu <30, quá mua nếu >70\n"
            f"- **MACD**: {macd:.0f}, **Signal**: {macd_signal:.0f} → cho thấy động lượng tăng/giảm giá\n"
            f"- **Bollinger Bands**: Dải trên {bb_high:,.0f}, dải dưới {bb_low:,.0f} → giúp nhận biết biến động giá\n"
            f"- **ADX (Average Directional Index)**: {adx:.1f} → trên 25 là xu hướng rõ ràng, dưới 20 là yếu hoặc đi ngang\n"
            f"- **Fibonacci mức gần nhất**: {fib_level or 'không xác định'} → hỗ trợ xác định vùng bật lại hoặc đảo chiều\n"
            f"- **Vùng hỗ trợ**: {support:.0f}, **vùng kháng cự**: {resistance:.0f} → các mốc giá quan trọng có thể bật lên hoặc bị chặn lại\n\n"
            f"Hãy phân tích bằng tiếng Việt rõ ràng, dễ hiểu, chia thành 3 phần:\n"
            f"1. **Nhận định xu hướng hiện tại**: Ví dụ thị trường đang tăng, giảm hay đi ngang? Dựa vào các chỉ số kỹ thuật trên.\n"
            f"2. **Chiến lược gợi ý đơn giản**: Nên MUA, BÁN hay GIỮ? Giải thích ngắn gọn và dễ hiểu lý do để người mới có thể làm theo.\n"
            f"3. **Mục tiêu giá (nếu có)**: Nếu mua thì kỳ vọng bán ở giá nào? Nếu bán thì nên chờ mua lại ở đâu?\n\n"
            f"Lưu ý: Tránh dùng quá nhiều thuật ngữ phức tạp. Hướng dẫn phải thân thiện, dễ hành động, giống như bạn đang cố giúp một người bạn mới học giao dịch.\n"
            f"Trả về JSON với format:\n"
            f"{{\n"
            f"    \"strategy\": [\n"
            f"        {{\n"
            f"            \"trend\": \"string\",\n"
            f"            \"strategy\": \"string\",\n"
            f"            \"target\": [number, number]\n"
            f"        }}\n"
            f"    ]\n"
            f"}}"
        )
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount("https://", HTTPAdapter(max_retries=retries))
        response = session.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={GEMINI_API_KEY}",
            json=payload, headers=headers, timeout=5
        )
        response.raise_for_status()
        result = response.json()
        content = result["candidates"][0]["content"]["parts"][0]["text"]
        logging.info(f"Gemini API trả về cho {coin}: {content}")
        gem_result = json.loads(content)
        
        # Fallback nếu Gemini trả về rỗng
        if not gem_result.get('strategy') or len(gem_result['strategy']) == 0:
            logging.warning(f"Gemini API trả về rỗng cho {coin}, dùng chiến lược mặc định")
            trend = get_trend(latest_data)
            strategy = "Giữ"
            target = []
            if trend == "Tăng" and rsi < 70:
                strategy = "Nên Mua vì giá đang tăng và chưa vào vùng quá mua."
                target = [resistance + 0.1 * (resistance - support), resistance + 0.2 * (resistance - support)]
            elif trend == "Giảm" and rsi > 30:
                strategy = "Nên Bán vì giá đang giảm và chưa vào vùng quá bán."
                target = [support - 0.1 * (resistance - support), support - 0.2 * (resistance - support)]
            return {
                "strategy": [
                    {
                        "trend": f"Thị trường đang {trend.lower()}",
                        "strategy": strategy,
                        "target": target
                    }
                ]
            }
        
        return gem_result
    except Exception as e:
        logging.error(f"Lỗi Gemini API cho {coin}: {str(e)}")
        # Fallback strategy
        trend = get_trend(latest_data)
        rsi = float(latest_data['rsi']) if not pd.isna(latest_data['rsi']) else 50.0
        price = float(latest_data['price']) if not pd.isna(latest_data['price']) else 0.0
        strategy = "Giữ"
        target = []
        if trend == "Tăng" and rsi < 70:
            strategy = "Nên Mua vì giá đang tăng và chưa vào vùng quá mua."
            target = [resistance + 0.1 * (resistance - support), resistance + 0.2 * (resistance - support)]
        elif trend == "Giảm" and rsi > 30:
            strategy = "Nên Bán vì giá đang giảm và chưa vào vùng quá bán."
            target = [support - 0.1 * (resistance - support), support - 0.2 * (resistance - support)]
        return {
            "strategy": [
                {
                    "trend": f"Thị trường đang {trend.lower()}",
                    "strategy": strategy,
                    "target": target
                }
            ]
        }

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Tính các chỉ báo kỹ thuật."""
    logging.info("Tính chỉ báo kỹ thuật")
    try:
        if not all(col in df.columns for col in ['price', 'high', 'low']):
            logging.error("Thiếu cột price, high, hoặc low trong DataFrame")
            return df
        
        # RSI
        df['rsi'] = RSIIndicator(close=df['price'], window=14).rsi().fillna(0)
        
        # MACD
        macd = MACD(close=df['price'])
        df['macd'] = macd.macd().fillna(0)
        df['macd_signal'] = macd.macd_signal().fillna(0)
        df['macd_diff'] = macd.macd_diff().fillna(0)
        
        # Bollinger Bands
        bb = BollingerBands(close=df['price'], window=20)
        df['bb_high'] = bb.bollinger_hband().fillna(0)
        df['bb_low'] = bb.bollinger_lband().fillna(0)
        df['bb_mid'] = bb.bollinger_mavg().fillna(0)
        
        # ADX
        adx = ADXIndicator(high=df['high'], low=df['low'], close=df['price'], window=14)
        df['adx'] = adx.adx().fillna(20)
        
        # Chuyển đổi kiểu dữ liệu
        for col in ['rsi', 'macd', 'macd_signal', 'macd_diff', 'bb_high', 'bb_low', 'bb_mid', 'adx']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        
        logging.info(f"Các cột chỉ báo: {df[['rsi', 'macd', 'macd_signal', 'adx']].tail(1).to_dict()}")
        return df
    except Exception as e:
        logging.error(f"Lỗi tính chỉ báo: {str(e)}")
        return df

def generate_signals(df: pd.DataFrame, fib_levels: dict, coin: str) -> tuple:
    """Tạo tín hiệu giao dịch."""
    logging.info(f"Tạo tín hiệu cho {coin}")
    try:
        df = df.copy()
        df['signal'] = 'Hold'
        df['rsi_signal_str'] = df['rsi'].apply(lambda x: 'Sell' if float(x) > 70 else 'Buy' if float(x) < 30 else 'Hold')
        df['macd_signal_str'] = df.apply(lambda x: 'Buy' if float(x['macd']) > float(x['macd_signal']) else 'Sell' if float(x['macd']) < float(x['macd_signal']) else 'Hold', axis=1)
        df['bb_signal_str'] = df.apply(lambda x: 'Sell' if float(x['price']) > float(x['bb_high']) else 'Buy' if float(x['price']) < float(x['bb_low']) else 'Hold', axis=1)
        df['fib_signal_str'] = 'Hold'
        
        for index, row in df.iterrows():
            fib_level = is_near_fib_level(row['price'], fib_levels)
            if fib_level in ['fib_0.236', 'fib_0.382', 'fib_0.5']:
                df.at[index, 'fib_signal_str'] = 'Buy'
            elif fib_level in ['fib_0.618', 'fib_0.786', 'fib_1.0']:
                df.at[index, 'fib_signal_str'] = 'Sell'
        
        latest = df.iloc[-1]
        logging.info(f"Latest data: {latest[['price', 'rsi', 'macd', 'macd_signal', 'adx']].to_dict()}")
        
        fib_level = is_near_fib_level(latest['price'], fib_levels)
        support, resistance = get_support_resistance(df, fib_levels)
        gem_result = get_gemini_recommendation(latest, fib_level, support, resistance, coin)
        
        if 'gemini_signal' not in df.columns:
            df['gemini_signal'] = ''
        if 'gemini_reason' not in df.columns:
            df['gemini_reason'] = ''
        
        last_index = df.index[-1]
        gemini_signal = json.dumps(gem_result, ensure_ascii=False, indent=2) if gem_result.get('strategy') else 'No strategy'
        gemini_reason = 'AI Strategy'
        df.at[last_index, 'gemini_signal'] = gemini_signal
        df.at[last_index, 'gemini_reason'] = gemini_reason
        
        df['buy_signal_count'] = (
            (df['rsi_signal_str'] == 'Buy').astype(int) +
            (df['macd_signal_str'] == 'Buy').astype(int) +
            (df['bb_signal_str'] == 'Buy').astype(int) +
            (df['fib_signal_str'] == 'Buy').astype(int)
        )
        df['sell_signal_count'] = (
            (df['rsi_signal_str'] == 'Sell').astype(int) +
            (df['macd_signal_str'] == 'Sell').astype(int) +
            (df['bb_signal_str'] == 'Sell').astype(int) +
            (df['fib_signal_str'] == 'Sell').astype(int)
        )
        
        df.loc[(df['buy_signal_count'] > 0), 'signal'] = 'Long'
        df.loc[(df['sell_signal_count'] > 0) & (df['adx'] > 20), 'signal'] = 'Short'
        
        logging.info(f"Buy signals: {df['buy_signal_count'].tail(1).to_dict()}, Sell signals: ${df['sell_signal_count'].tail(1).to_dict()}")
        logging.info(f"Tín hiệu {coin}: {df[['signal']].tail().to_dict()}")
        return df, gem_result
    except Exception as e:
        logging.error(f"Lỗi tạo tín hiệu {coin}: {str(e)}")
        return df, {'strategy': []}

def get_latest_signal(df: pd.DataFrame, fib_levels: dict, coin: str) -> tuple:
    """In tín hiệu mới nhất."""
    logging.info(f"In tín hiệu cho {coin}")
    try:
        latest = df.iloc[-1]
        logging.info(f"Latest data: {latest[['price', 'rsi', 'macd', 'macd_signal', 'adx', 'signal']].to_dict()}")
        
        fib_level = is_near_fib_level(latest['price'], fib_levels)
        signal_vn = 'Mua' if latest['signal'] == 'Long' else 'Bán' if latest['signal'] == 'Short' else 'Giữ'
        
        price = float(latest['price']) if not pd.isna(latest['price']) and isinstance(latest['price'], (int, float)) else 0.0
        rsi = float(latest['rsi']) if not pd.isna(latest['rsi']) and isinstance(latest['rsi'], (int, float)) else 0.0
        macd = float(latest['macd']) if not pd.isna(latest['macd']) and isinstance(latest['macd'], (int, float)) else 0.0
        macd_signal = float(latest['macd_signal']) if not pd.isna(latest['macd_signal']) and isinstance(latest['macd_signal'], (int, float)) else 0.0
        bb_high = float(latest['bb_high']) if not pd.isna(latest['bb_high']) and isinstance(latest['bb_high'], (int, float)) else 0.0
        bb_low = float(latest['bb_low']) if not pd.isna(latest['bb_low']) and isinstance(latest['bb_low'], (int, float)) else 0.0
        adx = float(latest.get('adx', 20)) if not pd.isna(latest.get('adx', 20)) and isinstance(latest.get('adx', 20), (int, float)) else 20.0

        output = (
            f"### Phân định {coin}\n"
            f"- **Tín hiệu**: {signal_vn}\n"
            f"- **Giá**: ${price:,.2f}\n"
            f"- **RSI**: {rsi:.1f}\n"
            f"- **MACD**: {macd:.0f}, Signal: ${macd_signal:.2f}\n"
            f"- **BB**: ${bb_high:,.4f}/${bb_low:,.4f}\n"
            f"- **ADX**: ${adx:.2f}\n"
            f"- **Fib**: {fib_level or 'N/A'}\n"
        )

        support, resistance = get_support_resistance(df, fib_levels)
        gem_result = get_gemini_recommendation(latest, fib_level, support, resistance, coin)

        strategy_output = "\n### AI Strategy\n"
        strategy_output += f"Chiến lược từ Gemini AI:\n"
        strategy_output += json.dumps(gem_result, ensure_ascii=False, indent=4)

        logging.info(f"Tín hiệu {coin}: {strategy_output}")
        return output, strategy_output, gem_result
    except Exception as e:
        logging.error(f"Error in get_latest_signal for {coin}: {str(e)}")
        return "", "", {'strategy': []}

def analyze_crypto(coin: str, days: int = 30) -> dict:
    """Phân tích dữ liệu crypto và trả về kết quả."""
    from modules.api import fetch_crypto_data, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
    logging.info(f"Starting analysis for {coin} at {datetime.now()}")
    try:
        crypto_data = fetch_crypto_data(coin, days=days)
        if crypto_data.empty:
            message = f"*Lỗi Crypto Tool*\nNo data found for {coin}."
            logging.error(message)
            st.error(message)
            return None, None, None, None, None
            
        fib_levels = calculate_fibonacci_levels(crypto_data)
        crypto_data = calculate_indicators(crypto_data)
        crypto_data, gem_result = generate_signals(crypto_data, fib_levels, coin)
        
        if not isinstance(crypto_data.index, pd.RangeIndex):
            logging.warning(f"Invalid index type for {coin} DataFrame, resetting index")
            crypto_data = crypto_data.reset_index()
            
        logging.info(f"Crypto data columns after signals: {crypto_data.columns.tolist()}")
        if 'signal' not in crypto_data.columns:
            logging.error("Missing 'signal' column in crypto_data")
            return None, None, None, None, None
            
        signal_output, strategy_output, gem_result = get_latest_signal(crypto_data, fib_levels, coin)
        chart_path = plot_data(crypto_data, fib_levels, coin)
        
        latest = crypto_data.iloc[-1]
        logging.info(f"Final latest data for {coin}: {latest[['price', 'rsi', 'macd', 'macd_signal', 'adx', 'signal']].to_dict()}")
        
        fib_level = is_near_fib_level(latest['price'], fib_levels)
        signal_vn = 'Mua' if latest['signal'] == 'Long' else 'Bán' if latest['signal'] == 'Short' else 'Giữ'
        
        price = float(latest['price']) if not pd.isna(latest['price']) and isinstance(latest['price'], (int, float)) else 0.0
        rsi = float(latest['rsi']) if not pd.isna(latest['rsi']) and isinstance(latest['rsi'], (int, float)) else 0.0
        macd = float(latest['macd']) if not pd.isna(latest['macd']) and isinstance(latest['macd'], (int, float)) else 0.0
        macd_signal = float(latest['macd_signal']) if not pd.isna(latest['macd_signal']) and isinstance(latest['macd_signal'], (int, float)) else 0.0
        bb_high = float(latest['bb_high']) if not pd.isna(latest['bb_high']) and isinstance(latest['bb_high'], (int, float)) else 0.0
        bb_low = float(latest['bb_low']) if not pd.isna(latest['bb_low']) and isinstance(latest['bb_low'], (int, float)) else 0.0
        adx = float(latest.get('adx', 20)) if not pd.isna(latest.get('adx', 20)) and isinstance(latest.get('adx', 20), (int, float)) else 20.0

        message = (
            f"{coin} Signal\n"
            f"Tín hiệu: {signal_vn}\n"
            f"Giá: ${price:,.2f}\n"
            f"RSI: {rsi:.1f}\n"
            f"MACD: {macd:.0f}, Signal: {macd_signal:.0f}\n"
            f"BB: ${bb_high:,.0f}/${bb_low:,.0f}\n"
            f"ADX: {adx:.2f}\n"
            f"Fib: {fib_level or 'N/A'}\n"
            f"AI: {latest.get('gemini_signal', 'N/A')[:50]}\n"
            f"Lý do: {latest.get('gemini_reason', 'N/A')}"
        )

        if st.session_state.get('analysis_triggered', False):
            try:
                logging.info("Sending Telegram notification")
                send_telegram_message(
                    TELEGRAM_TOKEN,
                    TELEGRAM_CHAT_ID,
                    message,
                    signal_output + strategy_output,
                    chart_path
                )
                logging.info("Telegram message sent successfully")
            except Exception as e:
                logging.error(f"Error sending Telegram message: {str(e)}")
        
        logging.info(f"Analysis for {coin} completed")
        return crypto_data, fib_levels, signal_output + strategy_output, message, chart_path
    except Exception as e:
        logging.error(f"Error analyzing {coin}: {str(e)}")
        st.error(f"Error analyzing: {str(e)}")
        return None, None, None, None, None
