from dotenv import load_dotenv
load_dotenv()

import time
from datetime import datetime
from fetch_trades import fetch_recent_trades, fetch_committees
from fetch_prices import get_current_price, get_price_on_date, get_company_info
from signal_score import calculate_signal_score
from signal_reason import generate_signal_reason
from upsert import upsert_politician, upsert_trade, update_politician_performance
from notify import send_high_signal_notifications

PRICE_CACHE = {}


def parse_trade_size(trade_size_str):
    try:
        usd = float(trade_size_str or 0)
        if usd <= 15000:
            return (1001, 15000)
        elif usd <= 50000:
            return (15001, 50000)
        elif usd <= 100000:
            return (50001, 100000)
        elif usd <= 250000:
            return (100001, 250000)
        elif usd <= 500000:
            return (250001, 500000)
        elif usd <= 1000000:
            return (500001, 1000000)
        else:
            return (1000001, 5000000)
    except (ValueError, TypeError):
        return (0, 0)


def make_politician_id(raw):
    bio_id = raw.get('BioGuideID', '')
    if bio_id:
        return bio_id
    name = raw.get('Name', 'unknown')
    return name.lower().replace(' ', '_').replace('.', '').replace(',', '')


def compute_delay_days(trade_date_str, report_date_str):
    try:
        td = datetime.strptime(trade_date_str, '%Y-%m-%d')
        rd = datetime.strptime(report_date_str, '%Y-%m-%d')
        return (rd - td).days
    except (ValueError, TypeError):
        return None


def infer_chamber(raw):
    chamber = raw.get('Chamber', '')
    if not chamber:
        return None
    if 'sen' in chamber.lower():
        return 'Senate'
    if 'rep' in chamber.lower() or 'house' in chamber.lower():
        return 'House'
    return chamber


def normalize_party(raw):
    party = raw.get('Party', '')
    if not party:
        return None
    if 'democrat' in party.lower():
        return 'Democrat'
    if 'republican' in party.lower():
        return 'Republican'
    if 'independent' in party.lower():
        return 'Independent'
    return party


def get_cached_price(ticker, date=None):
    key = f"{ticker}_{date}" if date else f"{ticker}_current"
    if key in PRICE_CACHE:
        return PRICE_CACHE[key]
    if date:
        price = get_price_on_date(ticker, date)
    else:
        price = get_current_price(ticker)
    PRICE_CACHE[key] = price
    return price


def get_cached_company(ticker):
    key = f"company_{ticker}"
    if key in PRICE_CACHE:
        return PRICE_CACHE[key]
    info = get_company_info(ticker)
    PRICE_CACHE[key] = info
    return info


def run_pipeline(max_trades=None):
    print('[Pipeline] Starting...')

    committees_map = fetch_committees()
    trades = fetch_recent_trades(days=30)

    if not trades:
        print('[Pipeline] No new trades found. Exiting.')
        return

    if max_trades:
        trades = trades[:max_trades]

    seen_politicians = set()
    new_high_signal = []
    processed = 0
    errors = 0

    for raw in trades:
        try:
            politician_name = raw.get('Name', 'Unknown')
            ticker = raw.get('Ticker', '').upper().strip()
            if not ticker or ticker == '--' or len(ticker) > 10:
                continue

            politician_id = make_politician_id(raw)
            committees = committees_map.get(politician_name, [])
            trade_date = raw.get('Traded', '')
            report_date = raw.get('Filed', '')

            if politician_id not in seen_politicians:
                seen_politicians.add(politician_id)
                district = raw.get('District')
                if district:
                    try:
                        district = str(int(float(district)))
                    except (ValueError, TypeError):
                        pass
                politician_data = {
                    'id': politician_id,
                    'name': politician_name,
                    'party': normalize_party(raw),
                    'chamber': infer_chamber(raw),
                    'state': raw.get('State'),
                    'district': district,
                    'committees': committees if committees else None,
                    'is_active': True,
                }
                upsert_politician(politician_data)

            company = get_cached_company(ticker)
            price_at_trade = get_cached_price(ticker, trade_date) if trade_date else None
            price_current = get_cached_price(ticker)

            return_pct = None
            if price_at_trade and price_current and price_at_trade > 0:
                return_pct = round((price_current - price_at_trade) / price_at_trade * 100, 2)

            amount_low, amount_high = parse_trade_size(raw.get('Trade_Size_USD'))
            delay_days = compute_delay_days(trade_date, report_date)

            trade_type = raw.get('Transaction', '')
            if 'purchase' in trade_type.lower() or 'buy' in trade_type.lower():
                trade_type = 'Buy'
            elif 'sale' in trade_type.lower() or 'sell' in trade_type.lower():
                trade_type = 'Sale'
            elif 'exchange' in trade_type.lower():
                trade_type = 'Exchange'

            trade = {
                'politician_id': politician_id,
                'ticker': ticker,
                'company_name': company['name'],
                'sector': company['sector'],
                'trade_type': trade_type,
                'amount_low': amount_low,
                'amount_high': amount_high,
                'trade_date': trade_date if trade_date else None,
                'disclosure_date': report_date if report_date else None,
                'disclosure_delay_days': delay_days,
                'price_at_trade': price_at_trade,
                'price_current': price_current,
                'return_pct': return_pct,
                'politician_name': politician_name,
            }

            trade['signal_score'] = calculate_signal_score(trade, committees)

            if trade['signal_score'] >= 50:
                trade['signal_reason'] = generate_signal_reason(trade, committees, trade['signal_score'])
            else:
                trade['signal_reason'] = f"Trade in {company['sector'] or 'this sector'} by {politician_name}."

            db_trade = {k: v for k, v in trade.items() if k != 'politician_name'}
            saved = upsert_trade(db_trade)

            if saved and trade['signal_score'] >= 75:
                new_high_signal.append(saved)

            processed += 1
            if processed % 25 == 0:
                print(f'[Pipeline] Processed {processed}/{len(trades)} trades...')

        except Exception as e:
            errors += 1
            print(f'[Pipeline] Error processing trade for {raw.get("Name","?")}/{raw.get("Ticker","?")}: {e}')
            continue

    print(f'[Pipeline] Processed {processed} trades ({errors} errors)')

    print('[Pipeline] Recalculating leaderboard...')
    update_politician_performance()

    if new_high_signal:
        send_high_signal_notifications(new_high_signal)
        print(f'[Pipeline] {len(new_high_signal)} high-signal trades flagged')

    print(f'[Pipeline] Done. {processed} trades written to Supabase.')


if __name__ == '__main__':
    import sys
    max_trades = int(sys.argv[1]) if len(sys.argv) > 1 else None
    run_pipeline(max_trades=max_trades)
