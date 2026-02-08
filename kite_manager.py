import os
import requests
import pandas as pd
from kiteconnect import KiteConnect

class KiteDataManager:
    def __init__(self, api_key=None, api_secret=None):
        self.api_key = api_key or os.getenv('KITE_API_KEY')
        self.api_secret = api_secret or os.getenv('KITE_API_SECRET')
        self.access_token = os.getenv('KITE_ACCESS_TOKEN')
        
        if not self.api_key:
            print("Warning: KITE_API_KEY not found in environment.")
            return
            
        self.kite = KiteConnect(api_key=self.api_key)
        
        if self.access_token:
            self.kite.set_access_token(self.access_token)
            print("Kite initialized with Access Token.")
        else:
            print(f"Login URL: {self.kite.login_url()}")
            
    def generate_session(self, request_token):
        """Generates access token from request token"""
        try:
            data = self.kite.generate_session(request_token, api_secret=self.api_secret)
            self.access_token = data["access_token"]
            self.kite.set_access_token(self.access_token)
            print(f"Success! Access Token: {self.access_token}")
            print("(Save this to your environment or .env file to avoid logging in again)")
            return self.access_token
        except Exception as e:
            print(f"Error generating session: {e}")
            return None

    def fetch_historical_data(self, instrument_token, from_date, to_date, interval="day"):
        """
        Fetches historical data from Kite.
        interval: minute, day, 3minute, 5minute...
        """
        try:
            data = self.kite.historical_data(instrument_token, from_date, to_date, interval)
            df = pd.DataFrame(data)
            if not df.empty:
                df.set_index("date", inplace=True)
                df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"}, inplace=True)
            return df
        except Exception as e:
            print(f"Error fetching Kite data: {e}")
            return pd.DataFrame()

    def get_quote(self, symbol):
        """Get real-time quote for a symbol (e.g., 'NSE:RELIANCE')"""
        try:
            quote = self.kite.quote(symbol)
            return quote[symbol]
        except Exception as e:
            print(f"Error fetching quote: {e}")
            return None

    def get_instruments(self, exchange="NFO"):
        """Get list of instruments to find tokens"""
        try:
            return self.kite.instruments(exchange)
        except Exception as e:
            print(f"Error fetching instruments: {e}")
            return []

    def get_option_quote(self, symbol, strike, type="CE", expiry=None):
        """
        Finds the option symbol and fetches quote.
        symbol: NIFTY, BANKNIFTY
        strike: 22000
        type: CE or PE
        """
        # 1. Fetch all NFO instruments
        instruments = self.get_instruments("NFO")
        if not instruments: return None
        
        # 2. Filter for symbol and strike
        # Note: Kite instruments are a list of dicts.
        # We need to find the nearest expiry if not provided.
        
        candidates = [
            i for i in instruments 
            if i['name'] == symbol and i['strike'] == float(strike) and i['instrument_type'] == type
        ]
        
        if not candidates:
            print(f"No option found for {symbol} {strike} {type}")
            return None
            
        # Sort by expiry to get the nearest one (current month)
        candidates.sort(key=lambda x: x['expiry'])
        nearest_option = candidates[0]
        tradingsymbol = nearest_option['tradingsymbol']
        
        # 3. Get Quote
        quote = self.get_quote(f"NFO:{tradingsymbol}")
        if quote:
            return {
                'symbol': tradingsymbol,
                'price': quote['last_price'],
                'oi': quote['oi']
            }
        return None
