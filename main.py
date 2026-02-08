import pandas as pd
import numpy as np
import argparse
from data_processor import fetch_data, add_indicators
from model import StockPredictor
from backtester import Backtester
from nse_scraper import NSEScraper
from kite_manager import KiteDataManager

def suggest_option_chain(ticker, prediction, current_price, source="yfinance"):
    """
    Suggests an option strike based on prediction and Live Data.
    """
    sentiment = "NEUTRAL"
    suggestion = "WAIT"
    atm_strike = round(current_price / 100) * 100 # Rough ATM approximation
    
    # Try to get live Option Chain from NSE Scraper for better details
    scraper = NSEScraper()
    # Clean ticker for NSE (remove ^ or .NS)
    nse_symbol = ticker.replace('.NS', '').replace('^', '').replace('NSEI', 'NIFTY').replace('NSEBANK', 'BANKNIFTY')
    if nse_symbol == 'NIFTY50': nse_symbol = 'NIFTY' # Common alias fix
    
    print(f"Fetching Live Option Chain for {nse_symbol}...")
    chain_data = scraper.fetch_option_chain(nse_symbol)
    
    real_atm = None
    ce_price = 0
    pe_price = 0
    
    if chain_data:
        real_atm = scraper.get_atm_strike(chain_data, current_price)
        df_chain = scraper.parse_chain(chain_data)
        if not df_chain.empty and real_atm:
            row = df_chain[df_chain['Strike'] == real_atm]
            if not row.empty:
                ce_price = row.iloc[0]['CE_LTP']
                pe_price = row.iloc[0]['PE_LTP']
                print(f"Live ATM Strike: {real_atm} | CE: ₹{ce_price} | PE: ₹{pe_price}")
                atm_strike = real_atm

    if prediction > 0.6:
        sentiment = "BULLISH"
        suggestion = f"BUY {nse_symbol} {atm_strike} CE @ ~₹{ce_price} (Target: +30%, SL: -15%)"
    elif prediction < 0.4:
        sentiment = "BEARISH"
        suggestion = f"BUY {nse_symbol} {atm_strike} PE @ ~₹{pe_price} (Target: +30%, SL: -15%)"
        
    print(f"\n--- AI SUGGESTION FOR {ticker} ---")
    print(f"Current Spot Price: {current_price:.2f}")
    print(f"Model Confidence (Bullish): {prediction:.2%}")
    print(f"Market Sentiment: {sentiment}")
    print(f"Action: {suggestion}")
    print("-" * 30)

def main():
    parser = argparse.ArgumentParser(description="NSE Options ML Predictor")
    parser.add_argument("--ticker", type=str, default="^NSEI", help="Ticker symbol (e.g., ^NSEI, ^NSEBANK, RELIANCE.NS)")
    parser.add_argument("--kite", action="store_true", help="Use Kite Connect for data (requires env vars)")
    parser.add_argument("--token", type=str, help="Kite Request Token (if login needed)")
    args = parser.parse_args()
    
    ticker = args.ticker
    
    # 1. Fetch Data (Kite or Yahoo)
    df = None
    if args.kite:
        kite = KiteDataManager()
        if args.token:
            kite.generate_session(args.token)
        
        # NOTE: To use Kite fully, you need the instrument token for the symbol.
        # This is a simplified lookup for demo.
        # For Nifty 50, token is 256265. For BankNifty: 260105.
        token_map = {'^NSEI': 256265, '^NSEBANK': 260105} 
        inst_token = token_map.get(ticker)
        
        if inst_token and kite.access_token:
            print("Fetching data from Kite...")
            # Fetch last 2 years
            from datetime import datetime, timedelta
            to_date = datetime.now()
            from_date = to_date - timedelta(days=730)
            df = kite.fetch_historical_data(inst_token, from_date, to_date)
    
    if df is None or df.empty:
        if args.kite: print("Kite fetch failed or token missing. Falling back to yfinance.")
        try:
            df = fetch_data(ticker)
            print(f"Data fetched: {len(df)} records")
        except Exception as e:
            print(f"Error: {e}")
            return

    # 2. Add Indicators
    df = add_indicators(df)
    print(f"Indicators added. Data shape: {df.shape}")

    # 3. Prepare Data for ML
    feature_cols = ['RSI', 'MACD', 'MACD_SIGNAL', 'BB_UPPER', 'BB_LOWER', 'EMA_50', 'EMA_200']
    
    predictor = StockPredictor()
    X, y, scaler = predictor.prepare_data(df, feature_cols)
    
    # Split Data (Time-series split is better, but random split for demo)
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    # 4. Train Model
    print("Training Neural Network...")
    predictor.build_model()
    predictor.train(X_train, y_train)
    
    # 5. Evaluate/Predict
    accuracy = predictor.model.score(X_test, y_test)
    print(f"\nTest Accuracy: {accuracy:.2%}")
    
    predictions = predictor.predict(X_test)
    
    # 6. Suggest for Latest Data (Tomorrow's prediction)
    last_row = df.iloc[[-1]][feature_cols].values
    last_row_scaled = scaler.transform(last_row)
    
    next_day_pred = predictor.predict(last_row_scaled)[0]
    current_price = df['Close'].iloc[-1]
    
    suggest_option_chain(ticker, next_day_pred, current_price)
    
    # 7. Backtest
    backtest_df = df.iloc[split:].copy()
    if len(backtest_df) != len(predictions):
        backtest_df = backtest_df.iloc[:len(predictions)]
        
    backtester = Backtester(backtest_df, predictions)
    results, final_capital, win_rate = backtester.run()
    
    print(f"\nBacktest Results:")
    print(f"Initial Capital: 100,000")
    print(f"Final Capital: {final_capital:.2f}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total Trades: {len(results)}")
    
    if not results.empty:
        backtester.plot_equity(results)

if __name__ == "__main__":
    main()
