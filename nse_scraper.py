import requests
import json
import pandas as pd
import time

class NSEScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Initialize session with home page to get cookies
        try:
            self.session.get("https://www.nseindia.com", timeout=10)
        except:
            print("Warning: NSE Homepage connection failed. Scraper might be blocked.")

    def fetch_option_chain(self, symbol="NIFTY"):
        """
        Fetches live option chain data from NSE for a given symbol.
        Symbol: 'NIFTY', 'BANKNIFTY', or Stock Ticker (e.g. 'RELIANCE')
        """
        # Determine URL
        if symbol in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        else:
            url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
            
        try:
            response = self.session.get(url, timeout=10)
            if response.status_code == 401:
                # Refresh cookies
                self.session.get("https://www.nseindia.com", timeout=5)
                response = self.session.get(url, timeout=10)
                
            if response.status_code != 200:
                print(f"Failed to fetch Option Chain: {response.status_code}")
                return None
                
            data = response.json()
            return data
        except Exception as e:
            print(f"Error fetching NSE Option Chain: {e}")
            return None

    def get_atm_strike(self, option_data, spot_price):
        """Finds ATM strike based on spot price from option chain data"""
        if not option_data:
            return None
            
        strikes = [x['strikePrice'] for x in option_data['records']['data'] if x['expiryDate'] == option_data['records']['expiryDates'][0]]
        strikes = sorted(list(set(strikes)))
        
        # Find closest strike
        atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
        return atm_strike

    def parse_chain(self, data, expiry_date=None):
        """Parses the complex JSON into a simple DataFrame"""
        if not data: return None
        
        records = data['records']['data']
        # If no expiry specified, pick the first one (near month)
        if not expiry_date:
            expiry_date = data['records']['expiryDates'][0]
            
        # Filter by expiry
        filtered = [x for x in records if x['expiryDate'] == expiry_date]
        
        rows = []
        for item in filtered:
            row = {'Strike': item['strikePrice']}
            if 'CE' in item:
                row['CE_LTP'] = item['CE']['lastPrice']
                row['CE_OI'] = item['CE']['openInterest']
                row['CE_IV'] = item['CE']['impliedVolatility']
            if 'PE' in item:
                row['PE_LTP'] = item['PE']['lastPrice']
                row['PE_OI'] = item['PE']['openInterest']
                row['PE_IV'] = item['PE']['impliedVolatility']
            rows.append(row)
            
        return pd.DataFrame(rows)
