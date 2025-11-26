"""
Backtesting Framework for AutoInvestor

Validates whether congressional trading signals actually predict returns.
Core question: Does following Congress make money?

Methodology:
1. Get historical congressional trades from API
2. For each trade, get stock price at transaction date and future dates
3. Calculate returns at 30/60/90 day windows
4. Compare to S&P 500 benchmark over same period
5. Generate performance statistics

Author: Lyra & Thomas (Coalition)
Version: 1.0.0 - 2025-11-25
"""

import os
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import warnings
warnings.filterwarnings('ignore')


def get_price_on_date(ticker: str, target_date: datetime,
                      price_cache: Dict = None) -> Optional[float]:
    """
    Get closing price for a ticker on or near a specific date

    Args:
        ticker: Stock symbol
        target_date: Date to get price for
        price_cache: Optional cache dict to avoid repeated API calls

    Returns:
        Closing price or None if unavailable
    """
    cache_key = f"{ticker}_{target_date.strftime('%Y-%m-%d')}"

    if price_cache is not None and cache_key in price_cache:
        return price_cache[cache_key]

    try:
        # Get a window around target date (in case of weekends/holidays)
        start = target_date - timedelta(days=5)
        end = target_date + timedelta(days=5)

        stock = yf.Ticker(ticker)
        hist = stock.history(start=start, end=end)

        if hist.empty:
            return None

        # Find closest date to target
        hist.index = pd.to_datetime(hist.index).tz_localize(None)
        target_naive = target_date.replace(tzinfo=None)

        # Get dates on or before target
        valid_dates = hist.index[hist.index <= target_naive]
        if len(valid_dates) == 0:
            # If no dates before, get earliest after
            valid_dates = hist.index

        closest_date = valid_dates[-1]
        price = hist.loc[closest_date, 'Close']

        if price_cache is not None:
            price_cache[cache_key] = price

        return float(price)

    except Exception as e:
        return None


def calculate_trade_returns(trade: Dict, windows: List[int] = [30, 60, 90],
                           price_cache: Dict = None) -> Dict:
    """
    Calculate returns for a single congressional trade at various windows

    Args:
        trade: Trade dict with ticker, transaction_date, transaction_type
        windows: List of days to calculate returns (default: 30, 60, 90)
        price_cache: Optional price cache

    Returns:
        Dict with returns for each window
    """
    ticker = trade['ticker']
    tx_date = datetime.strptime(trade['transaction_date'], '%Y-%m-%d')
    tx_type = trade['transaction_type'].lower()

    # Get entry price
    entry_price = get_price_on_date(ticker, tx_date, price_cache)
    if entry_price is None:
        return {'error': f'No price data for {ticker} on {tx_date}'}

    results = {
        'ticker': ticker,
        'politician': trade.get('politician', 'Unknown'),
        'transaction_date': trade['transaction_date'],
        'transaction_type': tx_type,
        'entry_price': entry_price,
        'returns': {}
    }

    # Calculate returns for each window
    for days in windows:
        exit_date = tx_date + timedelta(days=days)

        # Don't calculate if exit date is in the future
        if exit_date > datetime.now():
            results['returns'][f'{days}d'] = None
            continue

        exit_price = get_price_on_date(ticker, exit_date, price_cache)
        if exit_price is None:
            results['returns'][f'{days}d'] = None
            continue

        # Calculate return (positive for buys, inverted for sells)
        raw_return = (exit_price - entry_price) / entry_price * 100

        # For sells, we'd be short, so invert the return
        if 'sell' in tx_type or 'sale' in tx_type:
            raw_return = -raw_return

        results['returns'][f'{days}d'] = round(raw_return, 2)

    return results


def get_benchmark_returns(start_date: datetime, windows: List[int] = [30, 60, 90],
                         benchmark: str = 'SPY') -> Dict:
    """
    Get benchmark (SPY) returns for comparison

    Args:
        start_date: Starting date
        windows: List of days to calculate returns
        benchmark: Benchmark ticker (default: SPY for S&P 500)

    Returns:
        Dict with benchmark returns for each window
    """
    price_cache = {}

    entry_price = get_price_on_date(benchmark, start_date, price_cache)
    if entry_price is None:
        return {'error': f'No benchmark data for {start_date}'}

    results = {'entry_price': entry_price, 'returns': {}}

    for days in windows:
        exit_date = start_date + timedelta(days=days)

        if exit_date > datetime.now():
            results['returns'][f'{days}d'] = None
            continue

        exit_price = get_price_on_date(benchmark, exit_date, price_cache)
        if exit_price is None:
            results['returns'][f'{days}d'] = None
            continue

        returns = (exit_price - entry_price) / entry_price * 100
        results['returns'][f'{days}d'] = round(returns, 2)

    return results


def backtest_congressional_trades(trades: List[Dict],
                                  windows: List[int] = [30, 60, 90],
                                  verbose: bool = True) -> Dict:
    """
    Backtest a list of congressional trades

    Args:
        trades: List of trade dicts from congressional_trades module
        windows: Return windows to calculate
        verbose: Print progress

    Returns:
        Comprehensive backtest results
    """
    if verbose:
        print(f"Backtesting {len(trades)} congressional trades...")
        print(f"Windows: {windows} days")
        print("-" * 60)

    price_cache = {}
    results = []
    benchmark_returns = defaultdict(list)

    for i, trade in enumerate(trades):
        if verbose and (i + 1) % 10 == 0:
            print(f"  Processing trade {i + 1}/{len(trades)}...")

        # Calculate trade returns
        trade_result = calculate_trade_returns(trade, windows, price_cache)

        if 'error' in trade_result:
            continue

        results.append(trade_result)

        # Get benchmark for same period
        tx_date = datetime.strptime(trade['transaction_date'], '%Y-%m-%d')
        bench = get_benchmark_returns(tx_date, windows)

        if 'error' not in bench:
            for window in windows:
                key = f'{window}d'
                if bench['returns'].get(key) is not None:
                    benchmark_returns[key].append(bench['returns'][key])

    # Calculate aggregate statistics
    stats = calculate_backtest_statistics(results, benchmark_returns, windows)

    return {
        'individual_trades': results,
        'statistics': stats,
        'windows': windows,
        'total_trades_analyzed': len(results),
        'total_trades_input': len(trades)
    }


def calculate_backtest_statistics(results: List[Dict],
                                  benchmark_returns: Dict,
                                  windows: List[int]) -> Dict:
    """
    Calculate aggregate statistics from backtest results
    """
    stats = {}

    for window in windows:
        key = f'{window}d'

        # Extract returns for this window
        trade_returns = [r['returns'].get(key) for r in results
                        if r['returns'].get(key) is not None]

        if not trade_returns:
            stats[key] = {'error': 'No valid returns data'}
            continue

        # Calculate statistics
        returns_array = np.array(trade_returns)
        bench_array = np.array(benchmark_returns.get(key, []))

        win_rate = np.mean(returns_array > 0) * 100
        avg_return = np.mean(returns_array)
        median_return = np.median(returns_array)
        std_return = np.std(returns_array)

        # Best and worst trades
        best_idx = np.argmax(returns_array)
        worst_idx = np.argmin(returns_array)
        best_trade = results[best_idx] if best_idx < len(results) else None
        worst_trade = results[worst_idx] if worst_idx < len(results) else None

        # Sharpe ratio (assuming 0% risk-free rate for simplicity)
        sharpe = avg_return / std_return if std_return > 0 else 0

        # Alpha vs benchmark
        bench_avg = np.mean(bench_array) if len(bench_array) > 0 else 0
        alpha = avg_return - bench_avg

        # Separate buys vs sells
        buy_returns = [r['returns'][key] for r in results
                      if r['returns'].get(key) is not None
                      and ('buy' in r['transaction_type'] or 'purchase' in r['transaction_type'])]
        sell_returns = [r['returns'][key] for r in results
                       if r['returns'].get(key) is not None
                       and ('sell' in r['transaction_type'] or 'sale' in r['transaction_type'])]

        stats[key] = {
            'trade_count': len(trade_returns),
            'win_rate': round(win_rate, 1),
            'avg_return': round(avg_return, 2),
            'median_return': round(median_return, 2),
            'std_dev': round(std_return, 2),
            'sharpe_ratio': round(sharpe, 3),
            'benchmark_avg': round(bench_avg, 2),
            'alpha_vs_spy': round(alpha, 2),
            'best_return': round(float(np.max(returns_array)), 2),
            'worst_return': round(float(np.min(returns_array)), 2),
            'best_trade': {
                'ticker': best_trade['ticker'],
                'politician': best_trade['politician'],
                'return': best_trade['returns'][key]
            } if best_trade else None,
            'worst_trade': {
                'ticker': worst_trade['ticker'],
                'politician': worst_trade['politician'],
                'return': worst_trade['returns'][key]
            } if worst_trade else None,
            'buy_avg': round(np.mean(buy_returns), 2) if buy_returns else None,
            'sell_avg': round(np.mean(sell_returns), 2) if sell_returns else None,
        }

    return stats


def format_backtest_report(backtest_results: Dict) -> str:
    """
    Format backtest results into human-readable report
    """
    stats = backtest_results['statistics']
    windows = backtest_results['windows']

    report = f"""
CONGRESSIONAL TRADING BACKTEST REPORT
=====================================
Analysis Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}
Trades Analyzed: {backtest_results['total_trades_analyzed']} / {backtest_results['total_trades_input']}

CORE QUESTION: Does following Congress make money?

"""

    for window in windows:
        key = f'{window}d'
        s = stats.get(key, {})

        if 'error' in s:
            report += f"\n{window}-Day Returns: {s['error']}\n"
            continue

        # Determine verdict
        alpha = s.get('alpha_vs_spy', 0) or 0
        if alpha > 2:
            verdict = "YES - Significant alpha"
        elif alpha > 0:
            verdict = "MAYBE - Slight outperformance"
        elif alpha > -2:
            verdict = "NEUTRAL - Market-like returns"
        else:
            verdict = "NO - Underperforms market"

        # Safe formatting helper
        def fmt(val, fmt_str="+.2f"):
            if val is None:
                return "N/A"
            try:
                return f"{val:{fmt_str}}"
            except:
                return str(val)

        # Safely get nested values
        best = s.get('best_trade') or {}
        worst = s.get('worst_trade') or {}

        report += f"""
{'='*60}
{window}-DAY RETURNS
{'='*60}

VERDICT: {verdict}

Performance Metrics:
  Trades Analyzed:    {s.get('trade_count', 0)}
  Win Rate:           {fmt(s.get('win_rate'), '.1f')}%
  Average Return:     {fmt(s.get('avg_return'))}%
  Median Return:      {fmt(s.get('median_return'))}%
  Standard Deviation: {fmt(s.get('std_dev'), '.2f')}%
  Sharpe Ratio:       {fmt(s.get('sharpe_ratio'), '.3f')}

Benchmark Comparison (SPY):
  SPY Average:        {fmt(s.get('benchmark_avg'))}%
  Alpha vs SPY:       {fmt(s.get('alpha_vs_spy'))}%

Buy vs Sell Signals:
  Buy Signal Avg:     {fmt(s.get('buy_avg'))}% (following purchases)
  Sell Signal Avg:    {fmt(s.get('sell_avg'))}% (inversing sales)

Best Trade:
  {best.get('ticker', 'N/A')} ({best.get('politician', 'N/A')}): {fmt(best.get('return'))}%

Worst Trade:
  {worst.get('ticker', 'N/A')} ({worst.get('politician', 'N/A')}): {fmt(worst.get('return'))}%

"""

    report += """
=====================================
METHODOLOGY NOTES
=====================================

- Returns calculated from transaction date (not disclosure date)
- This tests "perfect information" scenario (what if you knew immediately)
- Real-world returns would be lower due to 0-45 day disclosure lag
- Buy signals: Long position at entry, measure gain/loss
- Sell signals: Inverse return (as if shorting what Congress sells)
- Benchmark: SPY (S&P 500 ETF) over same holding period
- Alpha: Excess return vs benchmark

IMPORTANT DISCLAIMER:
This backtest is for research purposes only. Past performance does not
guarantee future results. Congressional trading patterns may change.
Always consult a licensed financial advisor before investing.
"""

    return report


def run_backtest_from_api(api_key: Optional[str] = None,
                          verbose: bool = True) -> Dict:
    """
    Convenience function to run backtest using live API data

    Args:
        api_key: RapidAPI key (or use RAPIDAPI_KEY env var)
        verbose: Print progress

    Returns:
        Backtest results dict
    """
    # Import the aggregate module to get trades
    from congressional_trades_aggregate import get_all_recent_trades

    if api_key is None:
        api_key = os.environ.get('RAPIDAPI_KEY')

    if not api_key:
        return {'error': 'API key required. Set RAPIDAPI_KEY environment variable.'}

    # Get recent trades
    if verbose:
        print("Fetching congressional trades from API...")

    trades, error = get_all_recent_trades(api_key)

    if error:
        return {'error': error}

    if not trades:
        return {'error': 'No trades found'}

    if verbose:
        print(f"Found {len(trades)} trades. Starting backtest...\n")

    # Run backtest
    results = backtest_congressional_trades(trades, windows=[30, 60, 90], verbose=verbose)

    return results


if __name__ == "__main__":
    import sys

    # Check for API key
    api_key = os.environ.get('RAPIDAPI_KEY')
    if len(sys.argv) > 1:
        api_key = sys.argv[1]

    if not api_key:
        print("Usage: python backtesting.py [RAPIDAPI_KEY]")
        print("Or set RAPIDAPI_KEY environment variable")
        sys.exit(1)

    print("\n" + "="*60)
    print("AUTOINVESTOR CONGRESSIONAL TRADING BACKTEST")
    print("="*60 + "\n")

    results = run_backtest_from_api(api_key=api_key, verbose=True)

    if 'error' in results:
        print(f"\nERROR: {results['error']}")
        sys.exit(1)

    report = format_backtest_report(results)
    print(report)
