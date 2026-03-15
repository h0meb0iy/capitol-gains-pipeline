import requests
import os

POLYGON_KEY = os.getenv('POLYGON_API_KEY')
BASE = 'https://api.polygon.io'

def get_current_price(ticker):
url = f'{BASE}/v2/last/trade/{ticker}?apiKey={POLYGON_KEY}'
try:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()['results']['p']
except Exception:
    return None

def get_price_on_date(ticker, date):
url = f'{BASE}/v1/open-close/{ticker}/{date}?adjusted=true&apiKey={POLYGON_KEY}'
try:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json().get('close')
except Exception:
    return None

def get_company_info(ticker):
url = f'{BASE}/v3/reference/tickers/{ticker}?apiKey={POLYGON_KEY}'
try:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    res = r.json()['results']
    return {'name': res.get('name', ticker), 'sector': res.get('sic_description')}
except Exception:
    return {'name': ticker, 'sector': None}
