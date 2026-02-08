import pandas as pd
import numpy as np
import argparse
from data_processor import fetch_data, add_indicators
from model import StockPredictor
from backtester import Backtester
from nse_scraper import NSEScraper
from kite_manager import KiteDataManager

def suggest_option_chain(ticker, prediction, current_price, kite=None):
    """
    Suggests an option strike based on prediction and Live Data.
    """
    sentiment = "NEUTRAL"
    suggestion = "WAIT"
    atm_strike = round(current_price / 50) * 50 # ATM approximation (Nifty is 50, BankNifty 100)
    if 'BANK' in ticker: atm_strike = round(current_price / 100) * 100
    
    nse_symbol = ticker.replace('.NS', '').replace('^', '').replace('NSEI', 'NIFTY').replace('NSEBANK', 'BANKNIFTY')
    if nse_symbol == 'NIFTY50': nse_symbol = 'NIFTY'
    
    ce_price = 0
    pe_price = 0
    source = "Estimation"
    
    # 1. Try Kite (Best)
    if kite and kite.access_token:
        print(f"Fetching Option Prices from Kite for {nse_symbol} {atm_strike}...")
        ce_quote = kite.get_option_quote(nse_symbol, atm_strike, "CE")
        pe_quote = kite.get_option_quote(nse_symbol, atm_strike, "PE")
        
        if ce_quote: ce_price = ce_quote['price']
        if pe_quote: pe_price = pe_quote['price']
        source = "Kite API"
        
    # 2. Try NSE Scraper (Fallback)
    if ce_price == 0:
        scraper = NSEScraper()
        print(f"Fetching Live Option Chain for {nse_symbol} (Scraper)...")
        chain_data = scraper.fetch_option_chain(nse_symbol)
        
        if chain_data:
            real_atm = scraper.get_atm_strike(chain_data, current_price)
            df_chain = scraper.parse_chain(chain_data)
            if not df_chain.empty and real_atm:
                row = df_chain[df_chain['Strike'] == real_atm]
                if not row.empty:
                    ce_price = row.iloc[0]['CE_LTP']
                    pe_price = row.iloc[0]['PE_LTP']
                    atm_strike = real_atm
                    source = "NSE Live"

    # 3. Fallback to Estimation
    if ce_price == 0:
        ce_price = current_price * 0.005 # ~0.5% premium estimate
        pe_price = current_price * 0.005
        source = "Estimated (Data Unavailable)"

    if prediction > 0.6:
        sentiment = "BULLISH"
        suggestion = f"BUY {nse_symbol} {atm_strike} CE @ ~₹{ce_price:.2f} (Target: +30%, SL: -15%)"
    elif prediction < 0.4:
        sentiment = "BEARISH"
        suggestion = f"BUY {nse_symbol} {atm_strike} PE @ ~₹{pe_price:.2f} (Target: +30%, SL: -15%)"
        
    print(f"\n--- AI SUGGESTION FOR {ticker} ---")
    print(f"Current Spot Price: {current_price:.2f}")
    print(f"Model Confidence (Bullish): {prediction:.2%}")
    print(f"Market Sentiment: {sentiment}")
    print(f"Data Source: {source}")
    print(f"Action: {suggestion}")
    print("-" * 30)

def analyze_ticker(ticker, kite=None):
    """
    Runs the full analysis pipeline for a single ticker.
    Returns a dict of results.
    """
    print(f"\n{'='*40}")
    print(f"ANALYZING: {ticker}")
    print(f"{'='*40}")
    
    # 1. Fetch Data
    df = None
    if kite and kite.access_token:
        # Kite logic (simplified for single ticker flow)
        token_map = {'^NSEI': 256265, '^NSEBANK': 260105}
        inst_token = token_map.get(ticker)
        if inst_token:
            from datetime import datetime, timedelta
            to_date = datetime.now()
            from_date = to_date - timedelta(days=3650) # 10 years
            df = kite.fetch_historical_data(inst_token, from_date, to_date)
            
    if df is None or df.empty:
        try:
            df = fetch_data(ticker)
        except Exception as e:
            print(f"Skipping {ticker}: {e}")
            return None

    if len(df) < 200:
        print(f"Not enough data for {ticker}")
        return None

    # 2. Add Indicators
    df = add_indicators(df)

    # 3. Prepare Data
    feature_cols = ['RSI', 'MACD', 'MACD_SIGNAL', 'BB_UPPER', 'BB_LOWER', 'EMA_50', 'EMA_200']
    predictor = StockPredictor()
    X, y, scaler = predictor.prepare_data(df, feature_cols)
    
    # Split
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    # 4. Train
    # print("Training Model...")
    predictor.build_model()
    predictor.train(X_train, y_train)
    
    # 5. Predict Next Move
    accuracy = predictor.model.score(X_test, y_test)
    
    last_row = df.iloc[[-1]][feature_cols].values
    last_row_scaled = scaler.transform(last_row)
    prediction = predictor.predict(last_row_scaled)[0]
    
    current_price = df['Close'].iloc[-1]
    
    # 6. Suggestion Logic (Silent return)
    sentiment = "NEUTRAL"
    if prediction > 0.6: sentiment = "BULLISH"
    elif prediction < 0.4: sentiment = "BEARISH"
    
    return {
        "Ticker": ticker,
        "Price": current_price,
        "Sentiment": sentiment,
        "Confidence": prediction,
        "Accuracy": accuracy
    }

def main():
    parser = argparse.ArgumentParser(description="NSE Options ML Predictor")
    parser.add_argument("--ticker", type=str, default="^NSEI", help="Ticker symbol")
    parser.add_argument("--scan_nifty", action="store_true", help="Scan all Nifty 50 stocks")
    parser.add_argument("--kite", action="store_true", help="Use Kite Connect")
    parser.add_argument("--token", type=str, help="Kite Request Token")
    args = parser.parse_args()
    
    kite_manager = None
    if args.kite:
        kite_manager = KiteDataManager()
        if args.token:
            kite_manager.generate_session(args.token)

    if args.scan_nifty:
        # Top 10-15 weights in Nifty 50 for demo (Scanning 50 takes time)
        nifty_50 = [
            "RELIANCE.NS", "HDFCBANK.NS", "ICICIBANK.NS", "INFY.NS", "ITC.NS",
            "TCS.NS", "LT.NS", "AXISBANK.NS", "KOTAKBANK.NS", "SBIN.NS",
            "BHARTIARTL.NS", "BAJFINANCE.NS", "ASIANPAINT.NS", "MARUTI.NS", "TITAN.NS"
        ]
        
        results = []
        for stock in nifty_50:
            res = analyze_ticker(stock, kite=kite_manager)
            if res: results.append(res)
            
        # Display Summary
        print(f"\n{'='*60}")
        print(f"NIFTY 50 SCAN RESULTS (Top Picks)")
        print(f"{'='*60}")
        print(f"{'Ticker':<15} {'Price':<10} {'Sentiment':<10} {'Conf %':<10} {'Model Acc':<10}")
        print("-" * 60)
        
        # Sort by Confidence (High to Low)
        results.sort(key=lambda x: abs(x['Confidence'] - 0.5), reverse=True)
        
        for r in results:
            print(f"{r['Ticker']:<15} {r['Price']:<10.2f} {r['Sentiment']:<10} {r['Confidence']:<10.2%} {r['Accuracy']:<10.2%}")
            
    else:
        # Single Ticker Mode (Old Logic wrapped)
        res = analyze_ticker(args.ticker, kite=kite_manager)
        if res:
            suggest_option_chain(res['Ticker'], res['Confidence'], res['Price'], kite=kite_manager)
            # Re-run backtest for the chart
            df = fetch_data(args.ticker)
            df = add_indicators(df)
            predictor = StockPredictor()
            feature_cols = ['RSI', 'MACD', 'MACD_SIGNAL', 'BB_UPPER', 'BB_LOWER', 'EMA_50', 'EMA_200']
            X, _, _ = predictor.prepare_data(df, feature_cols)
            # Retrain for backtest logic... (simplified here, in reality we reuse the model)
            # For backtest display, we need the prediction array on test set
            # ... skipping re-implementation of backtest in scan mode to keep code clean ...
            print("\nDone.")

if __name__ == "__main__":
    main()
