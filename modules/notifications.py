import requests
import logging
from typing import Optional
import os

def send_telegram_message(
    token: str,
    chat_id: str,
    message: str,
    signal_output: str,
    chart_path: Optional[str] = None
) -> None:
    """Gửi tin nhắn Telegram với văn bản và hình ảnh tùy chọn."""
    logging.info("Gửi tin nhắn Telegram")
    try:
        if not token or not chat_id:
            raise ValueError("Thiếu TELEGRAM_TOKEN hoặc TELEGRAM_CHAT_ID")
        
        # Thoát ký tự đặc biệt cho MarkdownV2
        def escape_markdown(text: str) -> str:
            escape_chars = r'_*[]()~`>#+=|{}.!-'
            for char in escape_chars:
                text = text.replace(char, f'\\{char}')
            text = text.replace('$', r'\$')
            return text
        
        # Tạo tin nhắn, giữ nguyên ký tự tiếng Việt
        full_message = f"{message}\n\n{signal_output}"
        full_message = escape_markdown(full_message)
        logging.info(f"Full Telegram message: {full_message}")
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": full_message[:4096],
            "parse_mode": "MarkdownV2"
        }
        
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code != 200:
            logging.error(f"Telegram API trả về: {response.text}")
            response.raise_for_status()
        logging.info("Gửi tin nhắn Telegram thành công")
        
        if chart_path and os.path.exists(chart_path):
            logging.info(f"Gửi hình ảnh {chart_path} qua Telegram")
            with open(chart_path, 'rb') as image_file:
                url = f"https://api.telegram.org/bot{token}/sendPhoto"
                caption = escape_markdown(f"Biểu đồ cho {message.split()[0]}")[:1024]
                files = {"photo": image_file}
                payload = {
                    "chat_id": chat_id.strip(),
                    "caption": caption,
                    "parse_mode": "MarkdownV2"
                }
                response = requests.post(url, files=files, data=payload, timeout=10)
                if response.status_code != 200:
                    logging.error(f"Telegram API trả về (photo): {response.text}")
                    response.raise_for_status()
                logging.info("Gửi hình ảnh Telegram thành công")
    except Exception as e:
        logging.error(f"Lỗi gửi Telegram: {str(e)}")
        raise

def test_telegram(token: str, chat_id: str) -> None:
    """Kiểm tra kết nối Telegram bằng tin nhắn test."""
    logging.info("Test Telegram")
    try:
        if not token or not chat_id:
            raise ValueError("Thiếu TELEGRAM_TOKEN hoặc TELEGRAM_CHAT_ID")
        
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": "Test message from Crypto Tool!"
        }
        logging.info(f"Test Telegram payload: {payload}")
        response = requests.post(url, json=payload, timeout=5)
        if response.status_code != 200:
            logging.error(f"Telegram API trả về: {response.text}")
            response.raise_for_status()
        logging.info("Test Telegram thành công")
    except Exception as e:
        logging.error(f"Lỗi test Telegram: {str(e)}")
        raise