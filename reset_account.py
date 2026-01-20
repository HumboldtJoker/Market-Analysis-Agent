#!/usr/bin/env python3
"""Reset Alpaca paper account - liquidate all positions"""
from order_executor import OrderExecutor
from dotenv import load_dotenv
import time

load_dotenv()
executor = OrderExecutor(mode='alpaca')

print('='*70)
print('RESETTING ALPACA PAPER ACCOUNT - LIQUIDATING ALL POSITIONS')
print('='*70)

# Get current state
account = executor.alpaca_client.get_account()
print(f'\nCurrent Account:')
print(f'  Equity: ${float(account.equity):,.2f}')
print(f'  Cash: ${float(account.cash):,.2f}')
print(f'  Buying Power: ${float(account.buying_power):,.2f}')

positions = executor.alpaca_client.get_all_positions()
print(f'\nCurrent Positions: {len(positions)}')
for pos in positions:
    print(f'  {pos.symbol}: {pos.qty} shares @ ${pos.current_price} = ${float(pos.market_value):,.2f}')

print('\n' + '='*70)
print('LIQUIDATING ALL POSITIONS')
print('='*70)

# Close all positions
for pos in positions:
    print(f'\nClosing {pos.symbol}: {pos.qty} shares')
    try:
        result = executor.execute_order(pos.symbol, 'SELL', float(pos.qty), 'market')
        print(f'  Result: {result["status"]}')
        time.sleep(1)
    except Exception as e:
        print(f'  ERROR: {e}')

# Wait for settlements
print('\nWaiting 5 seconds for settlements...')
time.sleep(5)

# Final state
account = executor.alpaca_client.get_account()
positions = executor.alpaca_client.get_all_positions()

print('\n' + '='*70)
print('ACCOUNT RESET COMPLETE')
print('='*70)
print(f'\nFinal Account:')
print(f'  Equity: ${float(account.equity):,.2f}')
print(f'  Cash: ${float(account.cash):,.2f}')
print(f'  Positions: {len(positions)}')

if len(positions) > 0:
    print('\n⚠️  WARNING: Some positions remain:')
    for pos in positions:
        print(f'  {pos.symbol}: {pos.qty} shares')
else:
    print('\n✅ All positions closed successfully')
