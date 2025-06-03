import pandas as pd
import numpy as np
import logging
from typing import Optional, Dict, Any

def run_backtest(df: pd.DataFrame, initial_balance: float = 10000) -> Optional[Dict[str, Any]]:
    """Chạy backtest chiến lược giao dịch."""
    logging.info("Bắt đầu backtest")
    try:
        if df.empty:
            logging.warning("DataFrame rỗng, không thể backtest")
            return None

        required_columns = ['price', 'signal']
        if not all(col in df.columns for col in required_columns):
            missing_cols = [col for col in required_columns if col not in df.columns]
            logging.error(f"Thiếu cột: {missing_cols}")
            return None

        if len(df) < 5:
            logging.warning(f"Dữ liệu quá ít ({len(df)} hàng), cần ít nhất 5 hàng để backtest")
            return None

        balance = initial_balance
        position = 0
        trades = []
        entry_price = 0

        for index, row in df.iterrows():
            price = row['price']
            signal = row['signal']

            if signal == 'Long' and position == 0:
                position = balance / price
                entry_price = price
                balance = 0
                trades.append({
                    'entry_time': index,
                    'entry_price': entry_price,
                    'type': 'Long',
                    'balance': balance,
                    'position': position
                })
                logging.info(f"Mở Long tại {index}, giá {entry_price}")

            elif signal == 'Short' and position > 0:
                balance = position * price
                profit = (price - entry_price) * position
                position = 0
                trades.append({
                    'exit_time': index,
                    'exit_price': price,
                    'profit': profit,
                    'balance': balance,
                    'position': position
                })
                logging.info(f"Đóng Long tại {index}, giá {price}, lợi nhuận {profit}")

        if position > 0:
            balance = position * df['price'].iloc[-1]
            trades.append({
                'exit_time': df.index[-1],
                'exit_price': df['price'].iloc[-1],
                'profit': (df['price'].iloc[-1] - entry_price) * position,
                'balance': balance,
                'position': position
            })

        total_profit = balance - initial_balance
        num_trades = len([t for t in trades if 'profit' in t])
        win_trades = len([t for t in trades if 'profit' in t and t['profit'] > 0])
        win_rate = (win_trades / num_trades * 100) if num_trades > 0 else 0

        result = {
            'total_profit': total_profit,
            'num_trades': num_trades,
            'win_rate': win_rate,
            'final_balance': balance,
            'trades': trades
        }

        logging.info(f"Kết quả backtest: {result}")
        return result

    except Exception as e:
        logging.error(f"Lỗi backtest: {str(e)}")
        return None