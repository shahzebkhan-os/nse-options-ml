from nse_scraper import NSEScraper
import json

def test_scraper():
    scraper = NSEScraper()
    print("Fetching NIFTY option chain...")
    data = scraper.fetch_option_chain("NIFTY")
    
    if data:
        print("Success! Keys:", data.keys())
        if 'records' in data:
            print("Expiry Dates:", data['records']['expiryDates'][:3])
            spot = data['records']['underlyingValue']
            print(f"Underlying Spot: {spot}")
            
            atm = scraper.get_atm_strike(data, spot)
            print(f"Calculated ATM: {atm}")
            
            df = scraper.parse_chain(data)
            row = df[df['Strike'] == atm]
            print("ATM Data Row:")
            print(row)
    else:
        print("Failed to fetch data.")

if __name__ == "__main__":
    test_scraper()
