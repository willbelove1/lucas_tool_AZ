import streamlit as st
import logging
from modules.ui import ui
from datetime import datetime

# Configure logging
logging.basicConfig(
    filename='logs/bitcoin_log.txt',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s - %(message)s'
)

def main():
    logging.info(f"Starting CryptoTool app at {datetime.now()}")
    
    # Khởi tạo session state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'analysis_triggered' not in st.session_state:
        st.session_state.analysis_triggered = False
    if 'last_analysis_time' not in st.session_state:
        st.session_state.last_analysis_time = None
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    # UI
    ui()

if __name__ == '__main__':
    main()