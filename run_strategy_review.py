#!/usr/bin/env python3
"""
Strategy Review Execution Script
Follows the protocol defined in skills/strategy-review.md
"""

import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Import unified API
from autoinvestor_api import (
    get_portfolio,
    get_technicals,
    get_macro_regime,
    get_sentiment,
    get_correlation,
    get_sectors,
    execute_order,
    get_market_status
)

def load_alert():
    """Load the pending alert file"""
    alert_files = [
        ('scheduled_review_needed.json', 'SCHEDULED'),
        ('strategy_review_needed.json', 'VIX_ALERT')
    ]

    for filename, alert_type in alert_files:
        path = Path(filename)
        if path.exists():
            with open(path) as f:
                alert = json.load(f)
            if alert.get('status') == 'pending':
                print(f"\n{'='*70}")
                print(f"Processing {alert_type}: {alert.get('reason', 'Review needed')}")
                print(f"{'='*70}\n")
                return filename, alert, alert_type

    return None, None, None

def load_thresholds():
    """Load thresholds.json for strategy parameters"""
    with open('thresholds.json') as f:
        return json.load(f)

def normalize_portfolio(portfolio):
    """
    Normalize portfolio data to have consistent field names.
    Handles both API format (shares, price, entry) and alert format (quantity, current_price, avg_cost).
    """
    normalized = portfolio.copy()

    # Normalize positions
    if 'positions' in normalized:
        for pos in normalized['positions']:
            # Normalize quantity field
            if 'shares' in pos and 'quantity' not in pos:
                pos['quantity'] = pos['shares']
            elif 'quantity' in pos and 'shares' not in pos:
                pos['shares'] = pos['quantity']

            # Normalize price field
            if 'price' in pos and 'current_price' not in pos:
                pos['current_price'] = pos['price']
            elif 'current_price' in pos and 'price' not in pos:
                pos['price'] = pos['current_price']

            # Normalize entry field
            if 'entry' in pos and 'avg_cost' not in pos:
                pos['avg_cost'] = pos['entry']
            elif 'avg_cost' in pos and 'entry' not in pos:
                pos['entry'] = pos['avg_cost']

            # Calculate market_value if missing
            if 'market_value' not in pos:
                qty = pos.get('quantity', pos.get('shares', 0))
                price = pos.get('current_price', pos.get('price', 0))
                pos['market_value'] = qty * price

    return normalized

def analyze_portfolio_health(portfolio):
    """Run correlation and sector analysis"""
    print("\n--- PORTFOLIO HEALTH CHECK ---")

    tickers = [p['ticker'] for p in portfolio['positions']]

    # Correlation analysis
    correlation = get_correlation(tickers)
    print(f"\nDiversification: {correlation['assessment']} (score: {correlation['diversification_score']}/100)")
    print(f"Avg correlation: {correlation['avg_correlation']:.3f}")

    if correlation.get('high_correlation_pairs'):
        print("\n[!] High correlation pairs:")
        for pair in correlation['high_correlation_pairs']:
            print(f"  - {pair['pair']}: {pair['correlation']:.3f}")

    # Sector analysis
    sectors = get_sectors(tickers)
    print(f"\nSector diversity: {sectors['assessment']}")
    print(f"Largest sector: {sectors['largest_sector']} ({sectors['largest_sector_pct']:.1f}%)")

    if sectors.get('concentration_risks'):
        print("\n[!] Concentration risks:")
        for risk in sectors['concentration_risks']:
            print(f"  - {risk['sector']}: {risk['exposure']:.1f}%")

    return correlation, sectors

def check_capital_management(portfolio, thresholds):
    """Check if capital rules are being followed"""
    print("\n--- CAPITAL MANAGEMENT CHECK ---")

    capital_rules = thresholds.get('capital_management', {})
    reserve_pct = capital_rules.get('opportunity_reserve_pct', 0.15)
    max_margin_pct = capital_rules.get('max_margin_pct', 0.10)

    cash = portfolio.get('cash', 0)
    total_value = portfolio.get('total_value', 0)
    cash_pct = (cash / total_value * 100) if total_value > 0 else 0

    required_reserve = total_value * reserve_pct
    margin_used = max(0, -cash)  # Negative cash = margin
    margin_pct = (margin_used / total_value * 100) if total_value > 0 else 0

    print(f"\nCash: ${cash:,.2f} ({cash_pct:.1f}% of portfolio)")
    print(f"Required reserve (15%): ${required_reserve:,.2f}")

    issues = []

    if cash < 0:
        print(f"\n[!] ON MARGIN: ${abs(cash):,.2f} ({margin_pct:.1f}% of portfolio)")
        print(f"  Max allowed: {max_margin_pct*100:.0f}%")
        if margin_pct > max_margin_pct * 100:
            issues.append(f"Margin usage {margin_pct:.1f}% exceeds max {max_margin_pct*100:.0f}%")
        issues.append("Priority: Clear margin before new positions")
    elif cash < required_reserve:
        shortage = required_reserve - cash
        print(f"\n[!] Below reserve target by ${shortage:,.2f}")
        issues.append("Build cash reserve before new positions")
    else:
        surplus = cash - required_reserve
        print(f"\n[OK] Adequate reserve (+${surplus:,.2f} available for deployment)")

    return {
        'cash': cash,
        'cash_pct': cash_pct,
        'on_margin': cash < 0,
        'margin_amount': margin_used,
        'margin_pct': margin_pct,
        'reserve_met': cash >= required_reserve,
        'available_to_deploy': max(0, cash - required_reserve),
        'issues': issues
    }

def check_watchlist_opportunities(thresholds, portfolio):
    """Check watchlist for entry opportunities"""
    print("\n--- WATCHLIST SCAN ---")

    watchlist = thresholds.get('watchlist', {})
    candidates = watchlist.get('candidates', {})
    scan_universe = watchlist.get('scan_universe', [])

    print(f"\nScanning {len(scan_universe)} tickers for opportunities...")

    # Get current positions to avoid duplicates
    current_tickers = [p['ticker'] for p in portfolio['positions']]

    opportunities = []

    for ticker in scan_universe:
        if ticker in current_tickers:
            continue  # Skip positions we already own

        try:
            tech = get_technicals(ticker)
            signal = tech.get('signal', 'N/A')
            rsi = tech.get('rsi', 0)
            price = tech.get('price', 0)

            # Look for STRONG BUY with healthy RSI
            if signal == 'STRONG BUY' and rsi < 70:
                opportunities.append({
                    'ticker': ticker,
                    'signal': signal,
                    'rsi': rsi,
                    'price': price,
                    'confidence': tech.get('confidence', 0)
                })
        except Exception as e:
            continue  # Skip on error

    if opportunities:
        print(f"\n[OK] Found {len(opportunities)} opportunities:")
        for opp in opportunities[:5]:  # Show top 5
            print(f"  - {opp['ticker']}: {opp['signal']} (RSI: {opp['rsi']:.0f}, ${opp['price']:.2f})")
    else:
        print("\nNo new opportunities meeting criteria (STRONG BUY + RSI < 70)")

    return opportunities

def scan_short_candidates(thresholds, portfolio):
    """Scan for short-selling opportunities in bearish sectors"""
    print("\n--- SHORT-SELLING SCAN ---")

    short_config = thresholds.get('short_selling', {})

    if not short_config.get('enabled', False):
        print("\nShort selling is disabled")
        return []

    test_mode = short_config.get('test_mode', {})
    if test_mode.get('enabled', False):
        print(f"\n[TEST MODE] Allocation: ${test_mode.get('test_allocation_usd', 0):,.0f}")
        print(f"Purpose: {test_mode.get('purpose', 'Learning')}")

    sector_scan = short_config.get('sector_scan', {})
    example_tickers = sector_scan.get('example_tickers', [])
    rules = short_config.get('rules', {})

    max_position_size = rules.get('max_position_size_usd', 1000)

    print(f"\nScanning {len(example_tickers)} bearish sector tickers...")
    print(f"Looking for: Below 50-day SMA, RSI < 40, bearish MACD, weak fundamentals")

    # Get current short positions
    current_shorts = [p for p in portfolio['positions'] if p.get('quantity', 0) < 0]
    current_short_tickers = [p['ticker'] for p in current_shorts]

    # Calculate current short exposure
    total_value = portfolio.get('total_value', 0)
    short_exposure = sum(abs(p.get('market_value', 0)) for p in current_shorts)
    short_exposure_pct = (short_exposure / total_value * 100) if total_value > 0 else 0

    print(f"\nCurrent short exposure: ${short_exposure:,.2f} ({short_exposure_pct:.1f}% of portfolio)")

    short_candidates = []

    for ticker in example_tickers:
        if ticker in current_short_tickers:
            continue  # Already short this ticker

        try:
            tech = get_technicals(ticker)
            signal = tech.get('signal', 'N/A')
            rsi = tech.get('rsi', 50)
            price = tech.get('price', 0)
            sma_50 = tech.get('sma50', 0)

            # Short criteria: SELL/STRONG SELL signal + RSI < 40 + below 50-day SMA
            is_bearish_signal = signal in ['SELL', 'STRONG SELL']
            is_weak_rsi = rsi < 40
            is_below_sma = price < sma_50 if sma_50 > 0 else False

            if is_bearish_signal and is_weak_rsi and is_below_sma:
                short_candidates.append({
                    'ticker': ticker,
                    'signal': signal,
                    'rsi': rsi,
                    'price': price,
                    'sma_50': sma_50,
                    'below_sma_pct': ((price - sma_50) / sma_50 * 100) if sma_50 > 0 else 0,
                    'score': (40 - rsi) + abs((price - sma_50) / sma_50 * 100)  # Higher score = weaker stock
                })
        except Exception as e:
            continue  # Skip on error

    # Sort by score (weakest first)
    short_candidates.sort(key=lambda x: x['score'], reverse=True)

    if short_candidates:
        print(f"\n[OK] Found {len(short_candidates)} short candidates:")
        for i, cand in enumerate(short_candidates[:3], 1):  # Show top 3
            print(f"  {i}. {cand['ticker']}: {cand['signal']} (RSI: {cand['rsi']:.0f}, "
                  f"${cand['price']:.2f}, {cand['below_sma_pct']:.1f}% below 50-SMA)")
    else:
        print("\nNo short candidates meeting criteria (SELL/STRONG SELL + RSI < 40 + below 50-SMA)")

    return short_candidates

def analyze_positions(portfolio, thresholds):
    """Analyze each position for stop-loss or profit protection triggers"""
    print("\n--- POSITION ANALYSIS ---")

    stop_losses = thresholds.get('position_stop_losses', {})
    profit_protections = thresholds.get('profit_protection', {})
    default_stop = thresholds.get('default_stop_loss', 0.20)

    issues = []

    for pos in portfolio['positions']:
        ticker = pos['ticker']
        unrealized_pl_pct = pos.get('pnl_pct', 0)

        print(f"\n{ticker}:")
        print(f"  P&L: {unrealized_pl_pct:+.2f}%")

        # Check stop-loss
        if ticker in stop_losses:
            threshold = stop_losses[ticker]['threshold']
            if unrealized_pl_pct <= -threshold * 100:
                issues.append(f"{ticker} hit stop-loss ({unrealized_pl_pct:+.2f}% <= -{threshold*100:.0f}%)")
                print(f"  [!] STOP-LOSS TRIGGERED")
        elif unrealized_pl_pct <= -default_stop * 100:
            issues.append(f"{ticker} hit default stop-loss ({unrealized_pl_pct:+.2f}%)")
            print(f"  [!] DEFAULT STOP-LOSS TRIGGERED")

        # Check profit protection
        if ticker in profit_protections:
            protection = profit_protections[ticker]
            current_price = pos.get('price', 0)
            position_type = protection.get('position_type', 'long')

            if position_type == 'short':
                # For shorts, check max_price (stop loss when price goes up)
                if 'max_price' in protection:
                    max_price = protection['max_price']
                    if current_price > max_price:
                        issues.append(f"{ticker} SHORT above stop-loss (${current_price:.2f} > ${max_price:.2f})")
                        print(f"  [!] SHORT STOP-LOSS TRIGGERED")
            else:
                # For longs, check min_price (stop loss when price goes down)
                if 'min_price' in protection:
                    min_price = protection['min_price']
                    if current_price < min_price:
                        issues.append(f"{ticker} below profit protection (${current_price:.2f} < ${min_price:.2f})")
                        print(f"  [!] PROFIT PROTECTION TRIGGERED")

        # Get technicals
        try:
            tech = get_technicals(ticker)
            signal = tech.get('signal', 'N/A')
            rsi = tech.get('rsi', 0)
            print(f"  Signal: {signal}, RSI: {rsi:.0f}")

            if rsi > 85:
                issues.append(f"{ticker} extremely overbought (RSI {rsi:.0f})")
                print(f"  [!] EXTREMELY OVERBOUGHT")
        except:
            pass

    return issues

def make_decision(alert, portfolio, capital_mgmt, opportunities, short_candidates, position_issues, correlation, sectors):
    """Decide on action based on analysis"""
    print("\n" + "="*70)
    print("STRATEGIC DECISION")
    print("="*70)

    # Check for urgent issues
    if position_issues:
        print("\n[!] URGENT ISSUES DETECTED:")
        for issue in position_issues:
            print(f"  - {issue}")
        return "DEFENSIVE", "Address urgent position issues", None

    # Check capital management
    if capital_mgmt['on_margin']:
        print("\n[INFO] ON MARGIN - Priority: clear margin before new positions")
        return "HOLD", "Clear margin first", None

    if not capital_mgmt['reserve_met']:
        print("\n[INFO] Below reserve target - avoid new positions")
        return "HOLD", "Build reserve", None

    # Check if we have deployable capital
    available = capital_mgmt['available_to_deploy']

    if available < 1000:
        print(f"\n[INFO] Limited deployable capital (${available:.2f})")
        # But we can still consider shorts which don't require cash (only margin)
        if short_candidates:
            print(f"\n[OK] {len(short_candidates)} short candidates available")
            return "SHORT", "Execute short trades (test mode)", short_candidates
        return "HOLD", "Insufficient capital for new positions", None

    # Prioritize long opportunities, but also consider shorts
    actions = []
    if opportunities:
        print(f"\n[OK] {len(opportunities)} long opportunities available")
        print(f"[OK] ${available:,.2f} available to deploy")
        actions.append(("LONG", opportunities))

    if short_candidates:
        print(f"\n[OK] {len(short_candidates)} short candidates available")
        actions.append(("SHORT", short_candidates))

    if actions:
        return "MIXED", f"Execute both long and short trades", actions

    print("\n[OK] Portfolio healthy, no urgent actions needed")
    return "HOLD", "Portfolio in good shape", None

def execute_decision(decision, reason, data, capital_mgmt, portfolio, thresholds):
    """Execute the decided action"""
    print(f"\nDecision: {decision}")
    print(f"Reason: {reason}")

    trades = []

    # Handle MIXED decision (both longs and shorts)
    if decision == "MIXED" and data:
        for action_type, candidates in data:
            if action_type == "LONG":
                trades.extend(execute_long_trades(candidates, capital_mgmt, portfolio))
            elif action_type == "SHORT":
                trades.extend(execute_short_trades(candidates, portfolio, thresholds))

    # Handle SHORT-only decision
    elif decision == "SHORT" and data:
        trades.extend(execute_short_trades(data, portfolio, thresholds))

    # Handle legacy REDEPLOY decision (backwards compat)
    elif decision == "REDEPLOY" and data:
        trades.extend(execute_long_trades(data, capital_mgmt, portfolio))

    return trades

def execute_long_trades(opportunities, capital_mgmt, portfolio):
    """Execute long (BUY) trades"""
    trades = []
    available = capital_mgmt['available_to_deploy']

    # Pick top opportunity
    top_opp = opportunities[0]
    ticker = top_opp['ticker']
    price = top_opp['price']

    # Calculate quantity (use ~90% of available to keep buffer)
    deploy_amount = available * 0.9
    quantity = int(deploy_amount / price)

    if quantity > 0:
        print(f"\n[TRADE] Executing: BUY {quantity} shares of {ticker} @ ${price:.2f}")
        print(f"   Deploy amount: ${quantity * price:,.2f}")

        # Check correlation impact before executing
        current_tickers = [p['ticker'] for p in portfolio['positions'] if p.get('quantity', 0) > 0]
        if current_tickers:
            test_correlation = get_correlation(current_tickers + [ticker])

            print(f"\n   Pre-trade correlation check:")
            print(f"   Current avg correlation: {get_correlation(current_tickers)['avg_correlation']:.3f}")
            print(f"   After adding {ticker}: {test_correlation['avg_correlation']:.3f}")

            if test_correlation['avg_correlation'] > 0.75:
                print(f"   [!] WARNING: Adding {ticker} would push correlation above 0.75")
                print(f"   Skipping trade to maintain diversification")
                return trades

        try:
            result = execute_order(
                ticker=ticker,
                action='BUY',
                quantity=quantity,
                order_type='market',
                mode='alpaca'
            )

            if result.get('success'):
                print(f"   [OK] Trade executed successfully")
                trades.append({
                    'ticker': ticker,
                    'action': 'BUY',
                    'quantity': quantity,
                    'price': price
                })
            else:
                print(f"   [ERROR] Trade failed: {result.get('error')}")
        except Exception as e:
            print(f"   [ERROR] Trade failed: {str(e)}")

    return trades

def execute_short_trades(short_candidates, portfolio, thresholds):
    """Execute short (SHORT) trades"""
    trades = []

    short_config = thresholds.get('short_selling', {})
    test_mode = short_config.get('test_mode', {})
    rules = short_config.get('rules', {})

    max_position_size = rules.get('max_position_size_usd', 1000)
    max_total_positions = rules.get('max_total_short_positions', 2)
    test_allocation = test_mode.get('test_allocation_usd', 2500)

    # Calculate current short exposure
    current_shorts = [p for p in portfolio['positions'] if p.get('quantity', 0) < 0]
    current_short_tickers = [p['ticker'] for p in current_shorts]
    current_short_count = len(current_shorts)
    short_exposure = sum(abs(p.get('market_value', 0)) for p in current_shorts)

    remaining_allocation = test_allocation - short_exposure

    print(f"\n[SHORT TRADES]")
    print(f"   Max short positions: {max_total_positions}")
    print(f"   Current short positions: {current_short_count}")
    print(f"   Test allocation: ${test_allocation:,.0f}")
    print(f"   Current short exposure: ${short_exposure:,.2f}")
    print(f"   Remaining allocation: ${remaining_allocation:,.2f}")

    # HARD BLOCK: Check if at maximum short positions
    if current_short_count >= max_total_positions:
        print(f"\n   [HARD BLOCK] Already at maximum short positions ({current_short_count}/{max_total_positions})")
        print(f"   NO NEW SHORTS ALLOWED. Only managing existing shorts.")
        return trades

    # Calculate how many new shorts we can open
    max_new_shorts = max_total_positions - current_short_count

    # Execute up to max_new_shorts trades
    for i, candidate in enumerate(short_candidates[:max_new_shorts]):
        if remaining_allocation < 500:  # Need at least $500 to short
            print(f"\n   Insufficient allocation remaining")
            break

        ticker = candidate['ticker']
        price = candidate['price']

        # SAFETY CHECK: Don't add to existing short positions
        if ticker in current_short_tickers:
            print(f"\n   [SKIP] Already have short position in {ticker} - not stacking")
            continue

        # Calculate quantity based on max position size
        position_size = min(max_position_size, remaining_allocation)
        quantity = int(position_size / price)

        if quantity > 0:
            print(f"\n[TRADE {i+1}] Executing: SHORT {quantity} shares of {ticker} @ ${price:.2f}")
            print(f"   Position size: ${quantity * price:,.2f}")
            print(f"   Reason: {candidate['signal']}, RSI {candidate['rsi']:.0f}, "
                  f"{candidate['below_sma_pct']:.1f}% below 50-SMA")

            try:
                result = execute_order(
                    ticker=ticker,
                    action='SHORT',
                    quantity=quantity,
                    order_type='market',
                    mode='alpaca'
                )

                if result.get('success'):
                    print(f"   [OK] Short trade executed successfully")
                    trades.append({
                        'ticker': ticker,
                        'action': 'SHORT',
                        'quantity': quantity,
                        'price': price
                    })
                    remaining_allocation -= quantity * price
                else:
                    print(f"   [ERROR] Trade failed: {result.get('error')}")
            except Exception as e:
                print(f"   [ERROR] Trade failed: {str(e)}")

    return trades

def update_alert(filename, alert, decision, reason, trades):
    """Mark alert as completed and log results"""
    alert['status'] = 'completed'
    alert['completed_at'] = datetime.now().isoformat()
    alert['decision'] = f"{decision}: {reason}"
    alert['executed_trades'] = trades

    with open(filename, 'w') as f:
        json.dump(alert, f, indent=2)

    print(f"\n[OK] Alert updated: {filename}")

def main():
    """Main execution flow"""
    print("\n" + "="*70)
    print("STRATEGY REVIEW EXECUTION")
    print("="*70)

    # Step 1: Load alert
    filename, alert, alert_type = load_alert()
    if not alert:
        print("\nNo pending alerts found")
        return

    # Step 2: Load thresholds
    thresholds = load_thresholds()

    # Step 3: Get current portfolio
    print("\n--- LOADING PORTFOLIO ---")
    portfolio = get_portfolio(mode='alpaca')
    portfolio = normalize_portfolio(portfolio)  # Ensure consistent field names
    print(f"\nPortfolio Value: ${portfolio['total_value']:,.2f}")
    print(f"Cash: ${portfolio['cash']:,.2f}")
    print(f"Positions: {portfolio['num_positions']}")
    print(f"Total P&L: ${portfolio.get('pnl', 0):,.2f} ({portfolio.get('pnl_pct', 0):+.2f}%)")

    # Step 4: Portfolio health check
    correlation, sectors = analyze_portfolio_health(portfolio)

    # Step 5: Capital management check
    capital_mgmt = check_capital_management(portfolio, thresholds)

    # Step 6: Analyze current positions
    position_issues = analyze_positions(portfolio, thresholds)

    # Step 7: Check watchlist
    opportunities = check_watchlist_opportunities(thresholds, portfolio)

    # Step 7b: Scan for short candidates
    short_candidates = scan_short_candidates(thresholds, portfolio)

    # Step 8: Make decision
    decision, reason, data = make_decision(
        alert, portfolio, capital_mgmt, opportunities, short_candidates,
        position_issues, correlation, sectors
    )

    # Step 9: Execute
    trades = execute_decision(decision, reason, data, capital_mgmt, portfolio, thresholds)

    # Step 10: Update alert
    update_alert(filename, alert, decision, reason, trades)

    # Final summary
    print("\n" + "="*70)
    print("STRATEGY REVIEW COMPLETE")
    print("="*70)
    print(f"\nTrigger: {alert_type}")
    print(f"Decision: {decision}")
    print(f"Actions: {len(trades)} trades executed")
    print(f"Portfolio Value: ${portfolio['total_value']:,.2f}")

    # Calculate next review time
    review_hours = thresholds.get('review_intervals', {}).get('strategy_review_hours', 1)
    print(f"Next Review: {review_hours} hour(s)")

if __name__ == "__main__":
    main()
