import os
from openai import OpenAI

client = None

def get_client():
global client
if client is None:
    client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
return client

def generate_signal_reason(trade, committees, score):
if score < 50:
    sector = trade.get('sector') or 'this sector'
    return f"Trade in {sector} by {trade.get('politician_name', 'Unknown')}."

prompt = f"""A US Congress member made a stock trade. Write a single sentence (max 20 words)
explaining why this trade is notable. Be specific. No speculation. No financial advice.

Politician: {trade.get('politician_name', 'Unknown')}
Committees: {', '.join(committees[:3]) if committees else 'None'}
Stock: {trade.get('ticker', '')} ({trade.get('company_name', '')})
Sector: {trade.get('sector', 'Unknown')}
Trade type: {trade.get('trade_type', '')}
Amount:  - 
Delay: {trade.get('disclosure_delay_days', 0)} days between trade and disclosure
Signal Score: {score}/100"""

try:
    resp = get_client().chat.completions.create(
        model='gpt-4o-mini',
        messages=[{'role': 'user', 'content': prompt}],
        max_tokens=60,
    )
    return resp.choices[0].message.content.strip()
except Exception as e:
    print(f'[OpenAI] Error generating reason: {e}')
    sector = trade.get('sector') or 'this sector'
    return f"High-signal trade in {sector} by {trade.get('politician_name', 'Unknown')}."
