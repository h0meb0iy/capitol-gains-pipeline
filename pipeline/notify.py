def send_high_signal_notifications(trades):
for trade in trades:
    ticker = trade.get('ticker', '?')
    score = trade.get('signal_score', 0)
    print(f'[Notify] High-signal trade: {ticker} (score: {score}) -- push notifications TBD')
