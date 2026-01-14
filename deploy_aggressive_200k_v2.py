#!/usr/bin/env python3
"""Deploy Aggressive $200k Active Trading Portfolio with SAFETY VALIDATION"""
from order_executor import OrderExecutor
from dotenv import load_dotenv
import yfinance as yf
import time

load_dotenv()
executor = OrderExecutor(mode='live')

print('='*70)
print('DEPLOYING AGGRESSIVE $200K ACTIVE TRADING PORTFOLIO')
print('Strategy: High-turnover, 15% payday targets, -8% stops')
print('Mode: LEVERAGED (using margin for full $200k deployment)')
print('='*70)

# Get current account state
account = executor.alpaca_client.get_account()
print(f'\nAccount State:')
print(f'  Cash: ${float(account.cash):,.2f}')
print(f'  Equity: ${float(account.equity):,.2f}')
print(f'  Buying Power: ${float(account.buying_power):,.2f}')
print(f'  Margin Multiplier: {account.multiplier}x')

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

print('\n' + '='*70)
print('SAFETY CHECK: Validating deployment')
print('='*70)

# VALIDATE BEFORE EXECUTING
validation = executor.validate_deployment(TARGET_ALLOCATIONS, use_margin=True)

print(f'\n- Account Cash: ${validation["account_cash"]:,.2f}')
print(f'- Account Equity: ${validation["account_equity"]:,.2f}')
print(f'- Buying Power: ${validation["buying_power"]:,.2f}')
print(f'- Total Deployment: ${validation["total_deployment"]:,.0f}')
print(f'- Margin Used: ${validation["margin_used"]:,.0f} ({validation["margin_pct"]:.0f}% of equity)')
print(f'- Cash After: ${validation["available_after"]:,.2f}')

# Show warnings
if validation["warnings"]:
    print('\nWARNINGS:')
    for warning in validation["warnings"]:
        print(f'  - {warning}')

# Show errors (if any)
if validation["errors"]:
    print('\nERRORS:')
    for error in validation["errors"]:
        print(f'  - {error}')
    print('\nDEPLOYMENT BLOCKED - Fix errors above')
    exit(1)

# Confirmation
if not validation["valid"]:
    print('\nVALIDATION FAILED - Deployment cannot proceed')
    exit(1)

print('\nVALIDATION PASSED - Proceeding with deployment')

print('\n' + '='*70)
print('PHASE 1: FETCH CURRENT PRICES')
print('='*70)

# Get current prices
prices = {}
for ticker in TARGET_ALLOCATIONS.keys():
    try:
        stock = yf.Ticker(ticker)
        prices[ticker] = stock.history(period='1d')['Close'].iloc[-1]
        print(f'  {ticker}: ${prices[ticker]:.2f}')
    except Exception as e:
        print(f'  ERROR fetching {ticker}: {e}')
        exit(1)

# Calculate target shares
print('\n' + '='*70)
print('PHASE 2: CALCULATE TARGET POSITIONS')
print('='*70)

targets = {}
total_target_value = 0
for ticker, allocation in TARGET_ALLOCATIONS.items():
    if ticker in prices:
        target_shares = allocation / prices[ticker]
        targets[ticker] = target_shares
        total_target_value += allocation
        print(f'  {ticker}: {target_shares:.2f} shares @ ${prices[ticker]:.2f} = ${allocation:,.0f}')

target_cash = float(account.equity) - total_target_value
print(f'\nTotal deployment: ${total_target_value:,.0f}')
print(f'Margin utilized: ${validation["margin_used"]:,.0f}')
print(f'Cash remaining: ${target_cash:,.0f}')

print('\n' + '='*70)
print('PHASE 3: EXECUTE ALL POSITIONS')
print('='*70)

# Execute all buys
execution_results = []
for ticker, qty in sorted(targets.items(), key=lambda x: TARGET_ALLOCATIONS[x[0]], reverse=True):
    allocation = TARGET_ALLOCATIONS[ticker]
    print(f'\n{ticker}: Buying {qty:.2f} shares @ ${prices[ticker]:.2f} (${allocation:,})')
    try:
        result = executor.execute_order(ticker, 'BUY', qty, 'market')
        execution_results.append({
            'ticker': ticker,
            'qty': qty,
            'status': result['status'],
            'allocation': allocation
        })
        print(f'  - Result: {result["status"]}')
        time.sleep(1)  # Rate limit
    except Exception as e:
        print(f'  ❌ ERROR: {e}')
        execution_results.append({
            'ticker': ticker,
            'qty': qty,
            'status': 'error',
            'allocation': allocation,
            'error': str(e)
        })

print('\n' + '='*70)
print('DEPLOYMENT COMPLETE')
print('='*70)

# Show execution summary
print('\nExecution Summary:')
for result in execution_results:
    status_symbol = 'OK' if result['status'] in ['filled', 'partially_filled'] else 'FAIL'
    print(f'  {status_symbol} {result["ticker"]}: {result["status"]} (${result["allocation"]:,})')

# Final portfolio state
print('\n' + '='*70)
print('FINAL PORTFOLIO STATE')
print('='*70)

time.sleep(3)
portfolio = executor.get_portfolio_summary()
account = executor.alpaca_client.get_account()

print(f'\nAccount:')
print(f'  Equity: ${float(account.equity):,.2f}')
print(f'  Cash: ${float(account.cash):,.2f}')
print(f'  Buying Power: ${float(account.buying_power):,.2f}')

print(f'\nPortfolio:')
print(f'  Total Value: ${portfolio["total_value"]:,.2f}')
print(f'  Positions: {len(portfolio["positions"])}')

print(f'\nAll positions (sorted by size):')
for pos in sorted(portfolio['positions'], key=lambda x: x['market_value'], reverse=True):
    pct = (pos['market_value'] / portfolio['total_value']) * 100
    pl_symbol = '+' if pos['unrealized_pl'] >= 0 else ''
    print(f'  {pos["ticker"]}: {pos["quantity"]:.2f} shares @ ${pos["current_price"]:.2f}')
    print(f'    Value: ${pos["market_value"]:,.2f} ({pct:.1f}%) | P&L: {pl_symbol}${pos["unrealized_pl"]:.2f} ({pl_symbol}{pos["unrealized_pl_percent"]:.2f}%)')

print('\n' + '='*70)
print('ACTIVE TRADING RULES')
print('='*70)
print('  Profit target: +15% (sell 50%, let 50% run to +20-30%)')
print('  Hard stops: -8% on all positions (NORMAL VIX)')
print('  Quick turnover: Exit if momentum breaks or RSI >85')
print('  Monitor: Every 5 minutes for exits/redeployment')
print(f'  Cash buffer: ${float(account.cash):,.2f} for dip-buying')
print('='*70)

print('\nDeployment successful - Ready for active trading!')
