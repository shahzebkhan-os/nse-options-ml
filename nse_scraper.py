import requests
import json
import pandas as pd
import time

from curl_cffi import requests
import json
import pandas as pd
import time

class NSEScraper:
    def __init__(self):
        self.headers = {
            'authority': 'www.nseindia.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-US,en;q=0.9',
            'cache-control': 'max-age=0',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        self.session = requests.Session(impersonate="chrome120")
        self.session.headers.update(self.headers)
        self._refresh_cookies()

    def _refresh_cookies(self):
        try:
            # NSE requires visiting the homepage first to set cookies
            self.session.get("https://www.nseindia.com", timeout=10)
        except Exception as e:
            pass

    def fetch_option_chain(self, symbol="NIFTY"):
        if symbol in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        else:
            url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
            
        try:
            # API headers must match what a browser sends for XHR
            # IMPERSONATE ONLY: Do NOT set explicit headers that clash with impersonation
            # curl_cffi handles the TLS fingerprint and basic headers.
            # We just add specific ones if needed.
            
            # First request might fail or be redirected, so we try with fresh cookies if needed
            response = self.session.get(url, timeout=10)
            
            if response.status_code == 401:
                self._refresh_cookies()
                response = self.session.get(url, timeout=10)
                
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
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
