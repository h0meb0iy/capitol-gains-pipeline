import os
from supabase import create_client
from collections import defaultdict

sb = None

def get_client():
global sb
if sb is None:
    sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
return sb

def upsert_politician(politician):
existing = get_client().table('politicians').select('id').eq('id', politician['id']).execute().data
if existing:
    get_client().table('politicians').update(politician).eq('id', politician['id']).execute()
else:
    get_client().table('politicians').insert(politician).execute()

def upsert_trade(trade):
query = get_client().table('trades').select('id') \
    .eq('politician_id', trade['politician_id']) \
    .eq('ticker', trade['ticker']) \
    .eq('trade_type', trade['trade_type'])

if trade.get('trade_date'):
    query = query.eq('trade_date', trade['trade_date'])

existing = query.execute().data

if existing:
    result = get_client().table('trades').update(trade).eq('id', existing[0]['id']).execute()
else:
    result = get_client().table('trades').insert(trade).execute()

return result.data[0] if result.data else None

def update_politician_performance():
trades = get_client().table('trades').select('*').not_.is_('return_pct', 'null').execute().data

if not trades:
    print('[Supabase] No trades with return data for performance calc')
    return

by_politician = defaultdict(list)
for t in trades:
    if t.get('politician_id'):
        by_politician[t['politician_id']].append(t)

rows = []
for pol_id, pol_trades in by_politician.items():
    returns = [t['return_pct'] for t in pol_trades if t.get('return_pct') is not None]
    if not returns:
        continue
    avg_return = sum(returns) / len(returns)
    win_rate = len([r for r in returns if r > 0]) / len(returns) * 100
    rows.append({
        'politician_id': pol_id,
        'period': 'YTD',
        'return_pct': round(avg_return, 2),
        'trade_count': len(pol_trades),
        'win_rate': round(win_rate, 2),
    })

rows.sort(key=lambda x: x['return_pct'], reverse=True)
for i, row in enumerate(rows):
    row['rank'] = i + 1

for row in rows:
    existing = get_client().table('politician_performance').select('id') \
        .eq('politician_id', row['politician_id']) \
        .eq('period', row['period']).execute().data
    if existing:
        get_client().table('politician_performance').update(row).eq('id', existing[0]['id']).execute()
    else:
        get_client().table('politician_performance').insert(row).execute()

print(f'[Supabase] Updated performance for {len(rows)} politicians')
