from datetime import datetime

COMMITTEE_SECTORS = {
'Financial Services': ['Finance', 'Banking', 'Insurance'],
'Armed Services': ['Defense', 'Aerospace'],
'Energy and Commerce': ['Energy', 'Technology', 'Healthcare', 'Telecom'],
'Science, Space, and Technology': ['Technology', 'Semiconductors'],
'Agriculture': ['Agriculture', 'Food'],
'Transportation': ['Airlines', 'Logistics', 'Auto'],
'Appropriations': ['Defense', 'Energy', 'Healthcare', 'Finance'],
'Ways and Means': ['Finance', 'Insurance', 'Tax'],
'Commerce, Science, and Transportation': ['Technology', 'Telecom', 'Airlines'],
'Banking, Housing, and Urban Affairs': ['Finance', 'Banking', 'Real Estate'],
'Health, Education, Labor, and Pensions': ['Healthcare', 'Pharmaceutical'],
'Judiciary': ['Technology', 'Telecom'],
}

def score_committee_overlap(committees, sector):
if not sector or not committees:
    return 0
for committee, sectors in COMMITTEE_SECTORS.items():
    if any(committee.lower() in c.lower() for c in committees):
        if any(s.lower() in sector.lower() for s in sectors):
            return 40
return 0

def score_trade_size(amount_low, amount_high):
mid = (amount_low + amount_high) / 2
if mid >= 1_000_000:
    return 25
if mid >= 500_000:
    return 20
if mid >= 250_000:
    return 15
if mid >= 100_000:
    return 10
return 5

def score_disclosure_delay(trade_date, disclosure_date):
try:
    td = datetime.strptime(trade_date, '%Y-%m-%d')
    dd = datetime.strptime(disclosure_date, '%Y-%m-%d')
    delay = (dd - td).days
    if delay >= 45:
        return 20
    if delay >= 30:
        return 15
    if delay >= 14:
        return 10
    if delay >= 7:
        return 5
except (ValueError, TypeError):
    pass
return 0

def score_legislative_timing(trade_date, sector):
active_sectors = ['Technology', 'Defense', 'Healthcare', 'Finance', 'Energy']
if sector and any(s.lower() in sector.lower() for s in active_sectors):
    return 10
return 0

def calculate_signal_score(trade, committees):
sector = trade.get('sector', '') or ''
score = 0
score += score_committee_overlap(committees, sector)
score += score_trade_size(trade.get('amount_low', 0), trade.get('amount_high', 0))
score += score_disclosure_delay(trade.get('trade_date', ''), trade.get('disclosure_date', ''))
score += score_legislative_timing(trade.get('trade_date', ''), sector)
return min(score, 100)
