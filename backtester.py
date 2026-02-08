import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

class Backtester:
    def __init__(self, df, predictions, threshold=0.6):
        self.df = df
        self.predictions = predictions.flatten()
        self.threshold = threshold  # Confidence threshold to take a trade
        
    def run(self, initial_capital=100000):
        capital = initial_capital
        position = 0
        trades = []
        equity_curve = [initial_capital]
        
        # Simple Logic: 
        # Pred > threshold -> Buy Call (Simulate Long Stock for simplicity)
        # Pred < (1-threshold) -> Buy Put (Simulate Short Stock)
        # Exit EOD (Day trading logic)
        
        print(f"\nRunning Backtest with Threshold {self.threshold}...")
        
        success_trades = 0
        total_trades_taken = 0
        
        for i in range(len(self.df) - 1): # -1 because we compare with next day
            confidence = self.predictions[i]
            
            # Data for the day
            current_close = self.df['Close'].iloc[i]
            next_close = self.df['Close'].iloc[i+1]
            date = self.df.index[i]
            
            pnl = 0
            trade_type = None
            
            if confidence > self.threshold:
                # Signal: BUY CALL (Long)
                trade_type = "CALL"
                change = (next_close - current_close) / current_close
                # Option Simulation: Options move ~0.5 delta of stock. 
                # If stock moves 1%, option might move ~20-50% depending on expiry.
                # Simplified: Risk 2% of capital per trade. Reward is proportional to stock move * leverage.
                # Let's assume 10x leverage for Options.
                pnl = (capital * 0.02) * (change * 100 * 5) # 5x leverage factor rough approx
                
                # Cap loss at risk amount
                if pnl < -(capital * 0.02):
                    pnl = -(capital * 0.02)
                    
            elif confidence < (1 - self.threshold):
                 # Signal: BUY PUT (Short)
                trade_type = "PUT"
                change = (current_close - next_close) / current_close # Inverse
                pnl = (capital * 0.02) * (change * 100 * 5)
                
                if pnl < -(capital * 0.02):
                    pnl = -(capital * 0.02)
            
            if trade_type:
                total_trades_taken += 1
                if pnl > 0:
                    success_trades += 1
                
                capital += pnl
                trades.append({
                    'Date': date,
                    'Type': trade_type,
                    'Confidence': round(confidence, 2),
                    'PnL': round(pnl, 2),
                    'Capital': round(capital, 2)
                })
        
        equity_curve.extend([t['Capital'] for t in trades])
        
        results = pd.DataFrame(trades)
        win_rate = (success_trades / total_trades_taken * 100) if total_trades_taken > 0 else 0
        
        return results, capital, win_rate

    def plot_equity(self, results):
        if results.empty:
            print("No trades taken.")
            return
            
        plt.figure(figsize=(12, 6))
        plt.plot(pd.to_datetime(results['Date']), results['Capital'])
        plt.title('Backtest Equity Curve')
        plt.xlabel('Date')
        plt.ylabel('Capital')
        plt.grid(True)
        plt.savefig('backtest_result.png')
        print("Backtest chart saved to backtest_result.png")
