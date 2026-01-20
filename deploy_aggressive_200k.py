#!/usr/bin/env python3
"""Deploy Aggressive $200k Active Trading Portfolio"""
from order_executor import OrderExecutor
from dotenv import load_dotenv
import yfinance as yf
import time

load_dotenv()
executor = OrderExecutor(mode='alpaca')

print('='*70)
print('DEPLOYING AGGRESSIVE $200K ACTIVE TRADING PORTFOLIO')
print('Strategy: High-turnover, 15% payday targets, -8% stops')
print('='*70)

# Get current portfolio
portfolio = executor.get_portfolio_summary()
print(f'\nStarting Portfolio Value: ${portfolio["total_value"]:,.2f}')
print(f'Starting Cash: ${portfolio["cash"]:,.2f}')
print(f'\nCurrent positions: {len(portfolio["positions"])}')
for pos in portfolio['positions']:
    print(f'  {pos["ticker"]}: {pos["quantity"]} shares @ ${pos["current_price"]:.2f}')

print('\n' + '='*70)
print('PHASE 1: EXIT OLD POSITIONS')
print('='*70)

# Exit fractional positions
print('\n1. Exiting fractional AAPL...')
aapl_pos = next((p for p in portfolio['positions'] if p['ticker'] == 'AAPL'), None)
if aapl_pos and aapl_pos['quantity'] > 0:
    result = executor.execute_order('AAPL', 'SELL', aapl_pos['quantity'], 'market')
    print(f'   AAPL: Sold {aapl_pos["quantity"]} shares - {result["status"]}')
    time.sleep(1)

print('\n2. Exiting fractional NVDA...')
nvda_pos = next((p for p in portfolio['positions'] if p['ticker'] == 'NVDA'), None)
if nvda_pos and nvda_pos['quantity'] > 0:
    result = executor.execute_order('NVDA', 'SELL', nvda_pos['quantity'], 'market')
    print(f'   NVDA: Sold {nvda_pos["quantity"]} shares - {result["status"]}')
    time.sleep(1)

# Cancel any pending GOOGL limit orders
print('\n3. Canceling old GOOGL limit orders...')
try:
    orders = executor.alpaca_client.get_orders()
    googl_orders = [o for o in orders if o.symbol == 'GOOGL' and o.status in ['new', 'pending_new']]
    for order in googl_orders:
        executor.alpaca_client.cancel_order_by_id(order.id)
        print(f'   Canceled GOOGL order: {order.id}')
        time.sleep(1)
except Exception as e:
    print(f'   No GOOGL orders to cancel or error: {e}')

print('\n' + '='*70)
print('PHASE 2: CALCULATE TARGET POSITIONS')
print('='*70)

# Refresh portfolio after exits
time.sleep(2)
portfolio = executor.get_portfolio_summary()
print(f'\nCash after exits: ${portfolio["cash"]:,.2f}')

# Target allocations for $200k portfolio
TARGET_ALLOCATIONS = {
    'MU': 28000,      # HIGH CONVICTION - Explosive momentum
    'AMD': 26000,     # HIGH CONVICTION - Perfect setup
    'TSM': 24000,     # HIGH CONVICTION - Strong momentum
    'CRSP': 20000,    # HIGH CONVICTION - Biotech catalyst
    'COIN': 22000,    # HIGH CONVICTION - Crypto momentum
    'GOOGL': 12000,   # MEDIUM - Overbought but riding wave
    'MSFT': 13000,    # MEDIUM - Oversold reversal
    'MRNA': 8000,     # MEDIUM - Lottery ticket
    'DDOG': 10000,    # MEDIUM - Reversal setup
}

# Get current prices
print('\nFetching current prices...')
prices = {}
for ticker in TARGET_ALLOCATIONS.keys():
    try:
        stock = yf.Ticker(ticker)
        prices[ticker] = stock.history(period='1d')['Close'].iloc[-1]
        print(f'  {ticker}: ${prices[ticker]:.2f}')
    except Exception as e:
        print(f'  ERROR fetching {ticker}: {e}')

# Calculate target shares
print('\nTarget positions:')
targets = {}
total_target_value = 0
for ticker, allocation in TARGET_ALLOCATIONS.items():
    if ticker in prices:
        target_shares = allocation / prices[ticker]
        targets[ticker] = target_shares
        total_target_value += allocation
        print(f'  {ticker}: {target_shares:.2f} shares @ ${prices[ticker]:.2f} = ${allocation:,.0f}')

target_cash = 200000 - total_target_value
print(f'\nTotal deployment: ${total_target_value:,.0f}')
print(f'Target cash buffer: ${target_cash:,.0f}')

print('\n' + '='*70)
print('PHASE 3: ADJUST EXISTING POSITIONS')
print('='*70)

# Check current AMD position
amd_current = next((p['quantity'] for p in portfolio['positions'] if p['ticker'] == 'AMD'), 0)
if amd_current > 0:
    amd_target = targets.get('AMD', 0)
    amd_diff = amd_target - amd_current
    if abs(amd_diff) > 0.1:  # Only adjust if difference is meaningful
        action = 'BUY' if amd_diff > 0 else 'SELL'
        qty = abs(amd_diff)
        print(f'\nAMD: Current {amd_current:.2f} shares, Target {amd_target:.2f}')
        print(f'  {action} {qty:.2f} shares')
        result = executor.execute_order('AMD', action, qty, 'market')
        print(f'  Result: {result["status"]}')
        time.sleep(1)
    else:
        print(f'\nAMD: Already at target ({amd_current:.2f} shares)')
        targets.pop('AMD', None)  # Remove from new entries
else:
    print('\nAMD: Will enter as new position')

# Check current TSM position
tsm_current = next((p['quantity'] for p in portfolio['positions'] if p['ticker'] == 'TSM'), 0)
if tsm_current > 0:
    tsm_target = targets.get('TSM', 0)
    tsm_diff = tsm_target - tsm_current
    if abs(tsm_diff) > 0.1:
        action = 'BUY' if tsm_diff > 0 else 'SELL'
        qty = abs(tsm_diff)
        print(f'\nTSM: Current {tsm_current:.2f} shares, Target {tsm_target:.2f}')
        print(f'  {action} {qty:.2f} shares')
        result = executor.execute_order('TSM', action, qty, 'market')
        print(f'  Result: {result["status"]}')
        time.sleep(1)
    else:
        print(f'\nTSM: Already at target ({tsm_current:.2f} shares)')
        targets.pop('TSM', None)
else:
    print('\nTSM: Will enter as new position')

print('\n' + '='*70)
print('PHASE 4: ENTER NEW POSITIONS')
print('='*70)

# Enter new positions (those not already held)
new_positions = ['MU', 'CRSP', 'COIN', 'GOOGL', 'MSFT', 'MRNA', 'DDOG']

for ticker in new_positions:
    if ticker in targets:
        qty = targets[ticker]
        print(f'\n{ticker}: Buying {qty:.2f} shares @ ${prices[ticker]:.2f}')
        result = executor.execute_order(ticker, 'BUY', qty, 'market')
        print(f'  Result: {result["status"]}')
        time.sleep(1)

print('\n' + '='*70)
print('DEPLOYMENT COMPLETE')
print('='*70)

# Final summary
time.sleep(3)
portfolio = executor.get_portfolio_summary()
print(f'\nFinal Portfolio Value: ${portfolio["total_value"]:,.2f}')
print(f'Cash: ${portfolio["cash"]:,.2f}')
print(f'Positions: {len(portfolio["positions"])}')
print('\nAll positions:')
for pos in sorted(portfolio['positions'], key=lambda x: x['market_value'], reverse=True):
    pct = (pos['market_value'] / portfolio['total_value']) * 100
    print(f'  {pos["ticker"]}: {pos["quantity"]:.2f} shares @ ${pos["current_price"]:.2f} = ${pos["market_value"]:,.2f} ({pct:.1f}%)')

print('\n' + '='*70)
print('ACTIVE TRADING RULES:')
print('  - Profit target: +15% (sell 50%, let 50% run)')
print('  - Hard stops: -8% on all positions (NORMAL VIX)')
print('  - Monitor every 5 minutes for exits/redeployment')
print('  - Cash buffer: $35k for dip-buying opportunities')
print('='*70)
