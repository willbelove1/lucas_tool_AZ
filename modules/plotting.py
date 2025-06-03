import matplotlib.pyplot as plt
import pandas as pd
import logging
import os

def plot_data(crypto_data: pd.DataFrame, fib_levels: dict, coin: str) -> str:
    """Vẽ biểu đồ giá và các chỉ báo, lưu vào file."""
    logging.info(f"Vẽ biểu đồ cho {coin}")
    
    try:
        # Kiểm tra dữ liệu đầu vào
        required_columns = ['price', 'rsi', 'macd', 'macd_signal', 'macd_diff', 'adx']
        if crypto_data.empty:
            logging.error(f"Dữ liệu {coin} rỗng")
            return None
        missing_columns = [col for col in required_columns if col not in crypto_data.columns]
        if missing_columns:
            logging.warning(f"Dữ liệu {coin} thiếu cột: {missing_columns}, vẽ với các cột có sẵn")
            if 'price' not in crypto_data.columns:
                logging.error(f"Thiếu cột price cho {coin}")
                return None
        
        logging.info(f"Data columns for {coin}: {crypto_data.columns.tolist()}")
        
        # Tạo figure với 4 subplot (4 hàng, 1 cột)
        fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, 1, figsize=(12, 12), sharex=True)
        
        # 1. Giá với Fibonacci
        ax1.plot(crypto_data.index, crypto_data['price'], label='Giá', color='blue')
        for level_name, level_price in fib_levels.items():
            ax1.axhline(y=level_price, linestyle='--', label=level_name, alpha=0.5, color='gray')
        ax1.set_title(f"{coin} Giá với Fibonacci")
        ax1.set_ylabel("Giá (USD)")
        ax1.legend()
        ax1.grid(True)
        
        # 2. RSI (nếu có)
        if 'rsi' in crypto_data.columns:
            ax2.plot(crypto_data.index, crypto_data['rsi'], label='RSI', color='purple')
            ax2.axhline(y=70, color='red', linestyle='--', alpha=0.5)
            ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5)
            ax2.set_title("RSI")
            ax2.set_ylabel("RSI")
            ax2.set_ylim(0, 100)
            ax2.legend()
            ax2.grid(True)
        else:
            ax2.text(0.5, 0.5, "RSI không có dữ liệu", ha='center', va='center')
        
        # 3. MACD (nếu có)
        if all(col in crypto_data.columns for col in ['macd', 'macd_signal', 'macd_diff']):
            ax3.plot(crypto_data.index, crypto_data['macd'], label='MACD', color='blue')
            ax3.plot(crypto_data.index, crypto_data['macd_signal'], label='Signal', color='orange')
            ax3.bar(crypto_data.index, crypto_data['macd_diff'], label='MACD Diff', color='gray', alpha=0.3)
            ax3.set_title("MACD")
            ax3.set_ylabel("MACD")
            ax3.legend()
            ax3.grid(True)
        else:
            ax3.text(0.5, 0.5, "MACD không có dữ liệu", ha='center', va='center')
        
        # 4. ADX (nếu có)
        if 'adx' in crypto_data.columns:
            ax4.plot(crypto_data.index, crypto_data['adx'], label='ADX', color='blue')
            ax4.axhline(y=25, color='green', linestyle='--', alpha=0.5)
            ax4.set_title("ADX")
            ax4.set_xlabel("Date")
            ax4.set_ylabel("ADX")
            ax4.set_ylim(0, 50)
            ax4.legend()
            ax4.grid(True)
        else:
            ax4.text(0.5, 0.5, "ADX không có dữ liệu", ha='center', va='center')
        
        # Điều chỉnh layout
        plt.tight_layout()
        
        chart_path = f"charts/{coin}_chart.png"
        os.makedirs("charts", exist_ok=True)
        plt.savefig(chart_path, bbox_inches='tight', dpi=100)
        plt.close()
        
        if not os.path.exists(chart_path):
            logging.error(f"Không lưu được biểu đồ tại {chart_path}")
            return None
        
        logging.info(f"Lưu biểu đồ tại {chart_path}")
        return chart_path
    
    except Exception as e:
        logging.error(f"Lỗi vẽ biểu đồ {coin}: {str(e)}")
        return None