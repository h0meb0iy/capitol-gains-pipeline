import requests
import os
from datetime import datetime, timedelta

QUIVER_KEY = os.getenv('QUIVER_API_KEY')
BASE = 'https://api.quiverquant.com/beta'
HEADERS = {'Authorization': f'Token {QUIVER_KEY}'}


def fetch_recent_trades(days=30):
    resp = requests.get(f'{BASE}/bulk/congresstrading', headers=HEADERS, timeout=120)
    resp.raise_for_status()
    all_trades = resp.json()

    cutoff = datetime.now() - timedelta(days=days)
    recent = []
    for t in all_trades:
        try:
            filed_date = datetime.strptime(t.get('Filed', '') or '', '%Y-%m-%d')
            if filed_date >= cutoff:
                recent.append(t)
        except (ValueError, TypeError):
            continue

    print(f'[Quiver] Fetched {len(recent)} trades from last {days} days (total API: {len(all_trades)})')
    return recent


def fetch_committees():
    try:
        resp = requests.get(f'{BASE}/bulk/congresscommittees', headers=HEADERS, timeout=30)
        resp.raise_for_status()
        raw = resp.json()

        committees_map = {}
        for entry in raw:
            name = entry.get('Name', entry.get('Representative', ''))
            committee = entry.get('Committee', '')
            if name and committee:
                if name not in committees_map:
                    committees_map[name] = []
                if committee not in committees_map[name]:
                    committees_map[name].append(committee)

        print(f'[Quiver] Fetched committees for {len(committees_map)} politicians')
        return committees_map
    except Exception as e:
        print(f'[Quiver] Committees endpoint unavailable ({e}), continuing without committee data')
        return {}
