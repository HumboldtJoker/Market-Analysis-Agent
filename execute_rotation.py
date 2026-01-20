#!/usr/bin/env python3
"""Execute portfolio rotation based on sector scan analysis"""
from order_executor import OrderExecutor
from dotenv import load_dotenv
import time

load_dotenv()
executor = OrderExecutor(mode='alpaca')

print('=' * 70)
print('EXECUTING PORTFOLIO ROTATION')
print('=' * 70)
print()

# Get current portfolio
portfolio = executor.get_portfolio_summary()
cash = portfolio['cash']
total_value = portfolio['total_value']

print(f'Starting Portfolio Value: ${total_value:,.2f}')
print(f'Starting Cash: ${cash:,.2f}')
print()

# Phase 1: EXIT POSITIONS
print('PHASE 1: EXITING WEAK POSITIONS')
print('-' * 70)

# 1. Exit SOFI 100%
print('\n1. Exiting SOFI 100% (beta 2.48 extreme risk, STRONG SELL)...')
sofi_position = next((p for p in portfolio['positions'] if p['ticker'] == 'SOFI'), None)
if sofi_position:
    sofi_qty = sofi_position['quantity']
    result = executor.execute_order('SOFI', 'SELL', sofi_qty, 'market')
    print(f"   SOFI: Sold {sofi_qty} shares - {result['status']}")
    if result['status'] == 'FILLED':
        print(f"   Fill Price: ${result.get('fill_price', 'N/A')}")
else:
    print('   SOFI: No position found')

time.sleep(1)

# 2. Exit SNAP 100%
print('\n2. Exiting SNAP 100% (worst performer -4.56%, STRONG SELL)...')
snap_position = next((p for p in portfolio['positions'] if p['ticker'] == 'SNAP'), None)
if snap_position:
    snap_qty = snap_position['quantity']
    result = executor.execute_order('SNAP', 'SELL', snap_qty, 'market')
    print(f"   SNAP: Sold {snap_qty} shares - {result['status']}")
    if result['status'] == 'FILLED':
        print(f"   Fill Price: ${result.get('fill_price', 'N/A')}")
else:
    print('   SNAP: No position found')

time.sleep(1)

# 3. Trim NVDA 50%
print('\n3. Trimming NVDA 50% (100% bearish signals)...')
nvda_position = next((p for p in portfolio['positions'] if p['ticker'] == 'NVDA'), None)
if nvda_position:
    nvda_qty = nvda_position['quantity']
    trim_qty = nvda_qty * 0.5
    result = executor.execute_order('NVDA', 'SELL', trim_qty, 'market')
    print(f"   NVDA: Sold {trim_qty:.4f} shares (50% trim) - {result['status']}")
    if result['status'] == 'FILLED':
        print(f"   Fill Price: ${result.get('fill_price', 'N/A')}")
        print(f"   Remaining: {nvda_qty - trim_qty:.4f} shares")
else:
    print('   NVDA: No position found')

time.sleep(2)

# Get updated portfolio after exits
portfolio = executor.get_portfolio_summary()
cash_after_exits = portfolio['cash']
print()
print(f'Cash After Exits: ${cash_after_exits:,.2f}')
print()

# Phase 2: ENTER NEW POSITIONS
print('PHASE 2: ENTERING SUPERIOR POSITIONS')
print('-' * 70)

# Calculate position sizes (35% AMD, 30% TSM)
amd_allocation = total_value * 0.35
tsm_allocation = total_value * 0.30

# 4. Enter AMD 35%
print(f'\n4. Entering AMD 35% allocation (~${amd_allocation:,.2f})...')
# Get current AMD price
import yfinance as yf
amd_ticker = yf.Ticker('AMD')
amd_price = amd_ticker.history(period='1d')['Close'].iloc[-1]
amd_qty = amd_allocation / amd_price

result = executor.execute_order('AMD', 'BUY', amd_qty, 'market')
print(f"   AMD: Bought {amd_qty:.4f} shares @ ~${amd_price:.2f} - {result['status']}")
if result['status'] == 'FILLED':
    print(f"   Fill Price: ${result.get('fill_price', 'N/A')}")
    print(f"   Rationale: 100% STRONG BUY, bullish MACD crossover")

time.sleep(2)

# 5. Enter TSM 30%
print(f'\n5. Entering TSM 30% allocation (~${tsm_allocation:,.2f})...')
tsm_ticker = yf.Ticker('TSM')
tsm_price = tsm_ticker.history(period='1d')['Close'].iloc[-1]
tsm_qty = tsm_allocation / tsm_price

result = executor.execute_order('TSM', 'BUY', tsm_qty, 'market')
print(f"   TSM: Bought {tsm_qty:.4f} shares @ ~${tsm_price:.2f} - {result['status']}")
if result['status'] == 'FILLED':
    print(f"   Fill Price: ${result.get('fill_price', 'N/A')}")
    print(f"   Rationale: 75% STRONG BUY, buy the dip (-1.62% today)")

time.sleep(2)

# 6. Set GOOGL limit order (will wait for pullback to $325-330)
print(f'\n6. Setting GOOGL limit order (25% allocation, wait for pullback)...')
googl_allocation = total_value * 0.25
googl_limit_price = 327.50  # Mid-point of $325-330 target
googl_qty = googl_allocation / googl_limit_price

result = executor.execute_order('GOOGL', 'BUY', googl_qty, 'limit', limit_price=googl_limit_price)
print(f"   GOOGL: Limit order for {googl_qty:.4f} shares @ ${googl_limit_price:.2f} - {result['status']}")
print(f"   Order will fill when GOOGL drops from ${334.11:.2f} to ${googl_limit_price:.2f}")
print(f"   Rationale: 75% STRONG BUY, but RSI 82 overbought - wait for cooldown")

print()
print('=' * 70)
print('ROTATION COMPLETE')
print('=' * 70)

# Final portfolio summary
portfolio = executor.get_portfolio_summary()
print(f'\nFinal Portfolio Value: ${portfolio["total_value"]:,.2f}')
print(f'Final Cash: ${portfolio["cash"]:,.2f}')
print(f'Final P&L: ${portfolio["total_unrealized_pl"]:+,.2f}')
print()
print('New Positions:')
for pos in portfolio['positions']:
    print(f'  {pos["ticker"]}: {pos["quantity"]} shares @ ${pos["current_price"]:.2f} ({pos["unrealized_pl_percent"]:+.2f}%)')

print()
print('Expected Improvements:')
print('  - Beta: 1.85 -> 1.41 (-24% risk reduction)')
print('  - Volatility: 50.8% -> 39.5% (-22%)')
print('  - Sharpe Ratio: 0.57 -> 1.58 (+177%)')
print('  - Technical Signals: 88% bearish -> 94% bullish')
print()
print('Next: GOOGL limit order will auto-fill when price drops to $327.50')
