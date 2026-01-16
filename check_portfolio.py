#!/usr/bin/env python3
"""Quick portfolio status check"""
from order_executor import OrderExecutor
from dotenv import load_dotenv
import json

load_dotenv()
executor = OrderExecutor(mode='live')
portfolio = executor.get_portfolio_summary()

print('=' * 70)
print('PORTFOLIO STATUS - 2026-01-15 (Day 3)')
print('=' * 70)
print(f'Total Value: ${portfolio["total_value"]:,.2f}')
print(f'Cash: ${portfolio["cash"]:,.2f}')
equity = portfolio["total_value"] - portfolio["cash"]
print(f'Equity: ${equity:,.2f}')
pl = portfolio["total_unrealized_pl"]
pl_pct = (pl / 100000) * 100
print(f'Total P&L: ${pl:+,.2f} ({pl_pct:+.2f}%)')
print()
print('POSITIONS:')
for pos in portfolio['positions']:
    pl_pct = pos['unrealized_pl_percent']
    status = '+' if pl_pct >= 0 else '-'
    print(f'  {status} {pos["ticker"]}: {pos["quantity"]} shares @ ${pos["current_price"]:.2f}')
    print(f'     Entry: ${pos["avg_cost"]:.2f} | P&L: ${pos["unrealized_pl"]:+.2f} ({pl_pct:+.2f}%)')
print('=' * 70)
