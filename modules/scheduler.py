import schedule
import time
import logging
from datetime import datetime
from modules.notifications import send_telegram_message
import toml
from pathlib import Path

# Đọc secrets từ secrets.toml
secrets_path = Path("config/secrets.toml")
if secrets_path.exists():
    with open(secrets_path, "r") as f:
        secrets = toml.load(f).get("secrets", {})
    TELEGRAM_TOKEN = secrets.get("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = secrets.get("TELEGRAM_CHAT_ID", "")
else:
    logging.error("Không tìm thấy secrets.toml")
    TELEGRAM_TOKEN = TELEGRAM_CHAT_ID = ""

def load_schedule_config():
    """Load cấu hình lịch từ schedule_config.toml."""
    logging.info("Load schedule_config")
    config_path = Path("config/schedule_config.toml")
    try:
        if config_path.exists():
            with open(config_path, "r") as f:
                return toml.load(f).get("schedules", [])
        return []
    except Exception as e:
        logging.error(f"Lỗi load schedule_config: {str(e)}")
        return []

def save_schedule_config(config):
    """Lưu cấu hình lịch vào schedule_config.toml."""
    logging.info("Lưu schedule_config")
    config_path = Path("config/schedule_config.toml")
    try:
        with open(config_path, "w") as f:
            toml.dump({"schedules": config}, f)
        logging.info("Lưu schedule_config thành công")
    except Exception as e:
        logging.error(f"Lỗi lưu schedule_config: {str(e)}")

def auto_send_telegram(coin: str):
    """Gửi Telegram tự động."""
    logging.info(f"Tự động phân tích {coin} lúc {datetime.now()}")
    try:
        from modules.analysis import analyze_crypto
        crypto_data, fib_levels, signal_output, message, chart_path = analyze_crypto(coin)
        if message and signal_output:
            send_telegram_message(
                TELEGRAM_TOKEN,
                TELEGRAM_CHAT_ID,
                message,
                signal_output,
                chart_path
            )
            logging.info(f"Tự động gửi Telegram cho {coin} thành công")
        else:
            logging.error(f"Lỗi tự động gửi Telegram cho {coin}: Không có tín hiệu")
    except Exception as e:
        logging.error(f"Lỗi auto_send_telegram cho {coin}: {str(e)}")

def run_scheduled_tasks():
    """Thiết lập và chạy các tác vụ đã lên lịch."""
    logging.info("Thiết lập scheduler")
    try:
        schedule.clear()
        config = load_schedule_config()
        for item in config:
            time_str = item.get("time")
            coin = item.get("coin", "BTC")
            schedule.every().day.at(time_str).do(auto_send_telegram, coin=coin)
            logging.info(f"Đã lên lịch cho {coin} lúc {time_str}")
        
        schedule.run_all()  # Chạy ngay các tác vụ nếu đến giờ
        logging.info("Chạy tất cả tác vụ đã lên lịch")
    except Exception as e:
        logging.error(f"Lỗi thiết lập scheduler: {str(e)}")