import streamlit as st
import pandas as pd
import logging
from datetime import datetime, time
from modules.analysis import analyze_crypto
from modules.backtest import run_backtest
from modules.notifications import test_telegram
from modules.api import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
import os
from streamlit_autorefresh import st_autorefresh

def ui():
    """Render UI for CryptoTool."""
    logging.info("Rendering UI")
    
    st.title("Crypto Tool")
    
    # Auto-refresh mỗi phút để kiểm tra giờ
    st_autorefresh(interval=60*1000, key="time_checker")
    
    # Bảng đăng nhập
    if not st.session_state.get('logged_in', False):
        st.subheader("Đăng nhập")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            if username == "admin" and password == "admin":
                st.session_state.logged_in = True
                st.success("Đăng nhập thành công!")
                logging.info("Login successful")
                st.rerun()
            else:
                st.error("Invalid username or password")
                logging.error("Login failed")
        return
    
    # Sidebar
    st.sidebar.header("Crypto Tool")
    coins = ["BTC", "SUI", "BNB", "ETH", "ADA", "SOL", "Pi"]
    coin = st.sidebar.selectbox("Select Coin", coins, key="coin_select")
    days = st.sidebar.slider("Days", 1, 60, 30, key="days_slider")
    
    # Hẹn giờ
    st.sidebar.subheader("Hẹn giờ phân tích")
    if 'scheduled_times' not in st.session_state:
        st.session_state.scheduled_times = []
    
    new_time = st.sidebar.time_input("Chọn giờ", value=time(8, 0), key="new_time")
    if st.sidebar.button("Thêm giờ"):
        if new_time not in st.session_state.scheduled_times:
            st.session_state.scheduled_times.append(new_time)
            logging.info(f"Thêm khung giờ: {new_time}")
    
    # Hiển thị danh sách giờ đã chọn
    if st.session_state.scheduled_times:
        st.sidebar.write("Khung giờ đã chọn:")
        for i, t in enumerate(st.session_state.scheduled_times):
            cols = st.sidebar.columns([3, 1])
            cols[0].write(f"{t.hour:02d}:{t.minute:02d}")
            if cols[1].button("X", key=f"remove_time_{i}"):
                st.session_state.scheduled_times.pop(i)
                st.rerun()
    
    if st.sidebar.button("Lưu hẹn giờ"):
        st.session_state.scheduled_enabled = bool(st.session_state.scheduled_times)
        logging.info(f"Lưu hẹn giờ: {st.session_state.scheduled_times}, enabled={st.session_state.scheduled_enabled}")
        st.sidebar.success("Đã lưu hẹn giờ!")
    
    # Kiểm tra khung giờ
    if st.session_state.get('scheduled_enabled', False):
        now = datetime.now().time()
        scheduled_times = st.session_state.get('scheduled_times', [])
        for sched_time in scheduled_times:
            if now.hour == sched_time.hour and now.minute == sched_time.minute:
                logging.info(f"Chạy phân tích theo lịch cho {coin} tại {sched_time}")
                result = analyze_crypto(coin, days=days)
                crypto_data, fib_levels, signal_output, message, chart_path = result
                if crypto_data is not None and not crypto_data.empty:
                    st.session_state.analysis_result = result
                    st.session_state.chart_path = chart_path
                    logging.info(f"Phân tích theo lịch {coin} hoàn tất")
                else:
                    logging.error(f"Phân tích theo lịch {coin} thất bại: Empty data")
    
    # Lưu coin và ngày
    st.session_state.selected_coin = coin
    st.session_state.days = days
    
    # Phân tích thủ công
    if st.button("Run Analysis", key="run_analysis"):
        logging.info(f"Run Analysis button clicked for {coin}")
        st.session_state.analysis_triggered = True
        st.session_state.last_analysis_time = datetime.now()
        
        with st.spinner("Đang phân tích..."):
            result = analyze_crypto(coin, days=days)
            crypto_data, fib_levels, signal_output, message, chart_path = result
            
            if crypto_data is None or crypto_data.empty:
                st.error(f"Không thể phân tích {coin}. Không có dữ liệu hoặc lỗi API.")
                logging.error(f"Analysis failed for {coin}: Empty data")
                return
            
            st.session_state.analysis_result = result
            st.session_state.chart_path = chart_path
            
            st.write(signal_output, unsafe_allow_html=True)
            if chart_path and os.path.exists(chart_path):
                st.image(chart_path, caption=f"{coin} Chart")
            else:
                st.warning(f"Không tìm thấy biểu đồ cho {coin}. Kiểm tra log để biết thêm chi tiết.")
                logging.warning(f"No chart at {chart_path}")
    
    # Hiển thị kết quả nếu đã phân tích
    if st.session_state.get('analysis_result'):
        st.write(st.session_state.analysis_result[2], unsafe_allow_html=True)
        chart_path = st.session_state.get('chart_path')
        if chart_path and os.path.exists(chart_path):
            st.image(chart_path, caption=f"{st.session_state.selected_coin} Chart")
        else:
            st.warning(f"Không tìm thấy biểu đồ cho {st.session_state.selected_coin}. Kiểm tra log để biết thêm chi tiết.")
            logging.warning(f"No chart at {chart_path}")
    
    # Backtest
    if st.button("Run Backtest", key="run_backtest"):
        if st.session_state.get('analysis_result') and st.session_state.analysis_result[0] is not None:
            crypto_data = st.session_state.analysis_result[0]
            logging.info(f"Running backtest with columns: {crypto_data.columns.tolist()}")
            backtest_result = run_backtest(crypto_data)
            if backtest_result:
                st.subheader("Backtest Results")
                st.write(f"Total Profit: ${backtest_result['total_profit']:,.2f}")
                st.write(f"Number of Trades: {backtest_result['num_trades']}")
                st.write(f"Win Rate: {backtest_result['win_rate']:.2f}%")
                st.write(f"Final Balance: ${backtest_result['final_balance']:,.2f}")
                logging.info("Backtest displayed")
            else:
                st.error("Backtest failed")
                logging.error("Backtest returned None")
        else:
            st.error("No data to backtest. Run analysis first.")
            logging.error("No backtest data")
    
    # Test Telegram
    if st.button("Test Telegram", key="test_telegram"):
        try:
            test_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)
            st.success("Telegram test OK")
            logging.info("Telegram test successful")
        except Exception as e:
            st.error(f"Telegram test failed: {str(e)}")
            logging.error(f"Telegram test failed: {str(e)}")

if __name__ == "__main__":
    ui()