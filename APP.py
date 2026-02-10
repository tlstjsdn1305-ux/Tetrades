import streamlit as st
import urllib.request
import json
import ssl
import pandas as pd
from datetime import datetime, timedelta

# ---------------------------------------------------------
# [수정됨] API KEY를 보안 금고(secrets)에서 가져오도록 변경!
# ---------------------------------------------------------
OPENAI_API_KEY = st.secrets["OPENAI_API_KEY"]
FMP_API_KEY = st.secrets["FMP_API_KEY"]

ssl_context = ssl._create_unverified_context()

# ---------------------------------------------------------
# 1. 현재 주가 데이터 가져오기 (Quote)
# ---------------------------------------------------------
def get_stock_data(ticker):
    base_url = "https://financialmodelingprep.com/stable/quote"
    url = f"{base_url}?symbol={ticker}&apikey={FMP_API_KEY}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            if isinstance(data, list) and len(data) > 0:
                return data[0]
            return None
    except Exception as e:
        print(f"현재가 에러: {e}")
        return None

# ---------------------------------------------------------
# 1-1. 과거 데이터 가져오기 (stable 엔드포인트)
# ---------------------------------------------------------
def get_historical_data(ticker):
    base_url = "https://financialmodelingprep.com/stable/historical-price-eod/full"
    url = f"{base_url}?symbol={ticker}&apikey={FMP_API_KEY}"
    headers = {'User-Agent': 'Mozilla/5.0'}

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, context=ssl_context) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            hist_list = []
            if isinstance(data, dict) and "historical" in data:
                hist_list = data["historical"]
            elif isinstance(data, list):
                hist_list = data
                
            if hist_list and len(hist_list)