import requests
import json
import pandas as pd
import time

class NSEScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self._refresh_cookies()

    def _refresh_cookies(self):
        try:
            # NSE requires visiting the homepage first to set cookies
            self.session.get("https://www.nseindia.com", timeout=10)
        except:
            pass

    def fetch_option_chain(self, symbol="NIFTY"):
        if symbol in ['NIFTY', 'BANKNIFTY', 'FINNIFTY']:
            url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
        else:
            url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
            
        try:
            # API requests need slightly different headers (JSON)
            api_headers = self.headers.copy()
            api_headers.update({
                'Accept': '*/*',
                'Referer': f'https://www.nseindia.com/get-quote/derivatives?symbol={symbol}',
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-origin',
            })
            
            response = self.session.get(url, headers=api_headers, timeout=10)
            
            if response.status_code == 401:
                self._refresh_cookies()
                response = self.session.get(url, headers=api_headers, timeout=10)
                
            if response.status_code == 200:
                return response.json()
            return None
        except:
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
