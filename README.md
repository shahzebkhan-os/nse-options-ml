# NSE Options ML Predictor

A machine learning project to predict trend direction for NSE stocks and suggest option buying strategies.

## Features

- Fetches historical data using `yfinance`.
- Calculates Technical Indicators (RSI, MACD, Bollinger Bands).
- Uses a Neural Network (MLP) to predict Bullish/Bearish direction.
- Backtests the strategy on historical data.
- Suggests Option Chains (Call/Put) based on prediction.

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the predictor:
   ```bash
   python main.py --ticker ^NSEI
   # or for a stock
   python main.py --ticker RELIANCE
   ```

3. Check `backtest_result.png` for performance graph.

## Strategy Logic

- **Bullish (>60% confidence):** Buy CE (Call Option)
- **Bearish (<40% confidence):** Buy PE (Put Option)
- **Neutral:** Wait
- Backtest simulates 2% risk per trade with estimated option leverage.
