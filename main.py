import pandas as pd
import numpy as np
from data_processor import fetch_data, add_indicators
from model import StockPredictor
from backtester import Backtester
from sklearn.model_selection import train_test_split
import argparse

def suggest_option_chain(ticker, prediction, current_price):
    """
    Suggests an option strike based on prediction.
    """
    # Simple logic: ATM +/- 1 Strike
    # NIFTY usually has 50 point strikes, Stocks vary.
    # We will just suggest "ATM Call" or "ATM Put" generally.
    
    sentiment = "NEUTRAL"
    suggestion = "WAIT"
    
    if prediction > 0.6:
        sentiment = "BULLISH"
        suggestion = f"BUY {ticker} CE (Call Option) near {current_price} Strike"
    elif prediction < 0.4:
        sentiment = "BEARISH"
        suggestion = f"BUY {ticker} PE (Put Option) near {current_price} Strike"
        
    print(f"\n--- AI SUGGESTION FOR {ticker} ---")
    print(f"Current Price: {current_price:.2f}")
    print(f"Model Confidence (Bullish): {prediction:.2%}")
    print(f"Market Sentiment: {sentiment}")
    print(f"Option Strategy: {suggestion}")
    print("-" * 30)

def main():
    parser = argparse.ArgumentParser(description="NSE Options ML Predictor")
    parser.add_argument("--ticker", type=str, default="^NSEI", help="Ticker symbol (e.g., ^NSEI for Nifty 50, RELIANCE.NS)")
    args = parser.parse_args()
    
    ticker = args.ticker
    
    # 1. Fetch Data
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
    # Using last 20% for testing/backtesting
    split = int(len(X) * 0.8)
    X_train, X_test = X[:split], X[split:]
    y_train, y_test = y[:split], y[split:]
    
    # 4. Train Model
    print("Training Neural Network...")
    predictor.build_model((X_train.shape[1], X_train.shape[2]))
    predictor.train(X_train, y_train, epochs=20) # Low epochs for speed demo
    
    # 5. Evaluate/Predict
    loss, accuracy = predictor.model.evaluate(X_test, y_test, verbose=0)
    print(f"\nTest Accuracy: {accuracy:.2%}")
    
    predictions = predictor.predict(X_test)
    
    # 6. Suggest for Latest Data (Tomorrow's prediction)
    last_row = df.iloc[[-1]][feature_cols].values
    last_row_scaled = scaler.transform(last_row)
    last_row_reshaped = np.reshape(last_row_scaled, (1, 1, len(feature_cols)))
    
    next_day_pred = predictor.predict(last_row_reshaped)[0][0]
    current_price = df['Close'].iloc[-1]
    
    suggest_option_chain(ticker, next_day_pred, current_price)
    
    # 7. Backtest
    backtest_df = df.iloc[split:].copy() # Align with X_test
    # Need to align lengths perfectly
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
