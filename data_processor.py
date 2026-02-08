import yfinance as yf
import pandas as pd
import numpy as np

def fetch_data(ticker, period="10y", interval="1d"):
    """
    Fetches historical data for a given NSE ticker.
    Adds '.NS' suffix if missing.
    """
    if not ticker.endswith(".NS") and not ticker.startswith("^"):
        ticker = f"{ticker}.NS"
    
    print(f"Fetching data for {ticker}...")
    df = yf.download(ticker, period=period, interval=interval, progress=False)
    
    if df.empty:
        raise ValueError(f"No data found for {ticker}")
        
    return df

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def add_indicators(df):
    """
    Adds technical indicators to the dataframe using pandas.
    """
    # Ensure MultiIndex columns are handled
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # Calculate indicators on 'Close'
    close = df['Close']
    
    # RSI
    df['RSI'] = calculate_rsi(close)
    
    # EMA
    df['EMA_12'] = close.ewm(span=12, adjust=False).mean()
    df['EMA_26'] = close.ewm(span=26, adjust=False).mean()
    df['EMA_50'] = close.ewm(span=50, adjust=False).mean()
    df['EMA_200'] = close.ewm(span=200, adjust=False).mean()
    
    # MACD
    df['MACD'] = df['EMA_12'] - df['EMA_26']
    df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # Bollinger Bands
    df['SMA_20'] = close.rolling(window=20).mean()
    df['STD_20'] = close.rolling(window=20).std()
    df['BB_UPPER'] = df['SMA_20'] + (df['STD_20'] * 2)
    df['BB_LOWER'] = df['SMA_20'] - (df['STD_20'] * 2)
    
    # Target: 1 if next day Close > current day Close (Bullish), else 0
    df['Target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, 0)
    
    # Drop NaNs created by rolling windows
    df.dropna(inplace=True)
    
    return df
