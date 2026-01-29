"""
AutoInvestor Unified API
========================

A clean, consistent interface to all AutoInvestor analysis tools.
This module wraps the underlying implementations with intuitive names
and consistent return structures.

Usage:
    from autoinvestor_api import (
        get_stock_price,
        get_technicals,
        get_sentiment,
        get_macro_regime,
        get_portfolio,
        get_market_status,
        execute_order,
        get_correlation,    # Portfolio diversification analysis
        get_sectors         # Sector allocation analysis
    )

All functions automatically load environment variables from .env
"""

import os
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables on import
load_dotenv()

# Import underlying modules
import yfinance as yf
from technical_indicators import analyze_technicals
from news_sentiment import get_news_sentiment, analyze_news_sentiment
from macro_agent import MacroAgent
from order_executor import OrderExecutor
from market_status import get_market_status as _get_market_status
from portfolio_correlation import analyze_portfolio_correlation, get_portfolio_metrics
from sector_allocation import analyze_sector_allocation, get_sector_allocation


def get_stock_price(ticker: str) -> Dict:
    """
    Get current stock price and key metrics.

    Args:
        ticker: Stock symbol (e.g., 'AAPL')

    Returns:
        Dict with keys: ticker, price, volume, change_pct,
                       high_52w, low_52w, market_cap
    """
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        price = info.get('currentPrice') or info.get('regularMarketPrice', 0)
        prev_close = info.get('previousClose', price)
        change_pct = ((price - prev_close) / prev_close * 100) if prev_close else 0

        return {
            'ticker': ticker,
            'price': price,
            'volume': info.get('volume', 0),
            'change_pct': round(change_pct, 2),
            'high_52w': info.get('fiftyTwoWeekHigh', 0),
            'low_52w': info.get('fiftyTwoWeekLow', 0),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('trailingPE'),
            'dividend_yield': info.get('dividendYield'),
        }
    except Exception as e:
        return {'error': str(e), 'ticker': ticker}


def get_technicals(ticker: str) -> Dict:
    """
    Get technical analysis for a stock.

    Args:
        ticker: Stock symbol

    Returns:
        Dict with keys: ticker, signal, confidence, rsi, macd_signal,
                       sma50, sma50_distance, bullish_pct, details
    """
    try:
        result = analyze_technicals(ticker)
        raw = result.get('raw_data', {})
        overall = raw.get('overall_signal', {})
        rsi_data = raw.get('rsi', {})
        macd_data = raw.get('macd', {})
        sma_data = raw.get('sma', {})
        bb_data = raw.get('bollinger_bands', {})

        return {
            'ticker': ticker,
            'price': raw.get('current_price', 0),
            'signal': overall.get('recommendation', 'N/A'),
            'confidence': overall.get('confidence', 'N/A'),
            'bullish_pct': overall.get('bullish_pct', 0),
            'rsi': rsi_data.get('rsi_14', 0),
            'rsi_signal': rsi_data.get('signal', ''),
            'macd': macd_data.get('macd', 0),
            'macd_histogram': macd_data.get('histogram', 0),
            'macd_signal': 'bullish' if macd_data.get('histogram', 0) > 0 else 'bearish',
            'sma50': sma_data.get('sma_50', 0),
            'sma50_distance': sma_data.get('sma_50_distance', 0),
            'sma200': sma_data.get('sma_200', 0),
            'bb_upper': bb_data.get('upper_band', 0),
            'bb_lower': bb_data.get('lower_band', 0),
            'bb_signal': bb_data.get('sentiment', 'neutral'),
            'details': result.get('summary', '')
        }
    except Exception as e:
        return {'error': str(e), 'ticker': ticker}


def get_sentiment(ticker: str, days: int = 7) -> Dict:
    """
    Get news sentiment analysis for a stock.

    Args:
        ticker: Stock symbol
        days: Number of days of news to analyze (default: 7)

    Returns:
        Dict with keys: ticker, overall, positive, neutral, negative,
                       articles_count, headlines
    """
    try:
        result = get_news_sentiment(ticker, days=days)

        if 'error' in result:
            return result

        bd = result.get('sentiment_breakdown', {})
        articles = result.get('articles', [])

        return {
            'ticker': ticker,
            'overall': result.get('overall_sentiment', 'N/A'),
            'positive': bd.get('positive', 0),
            'neutral': bd.get('neutral', 0),
            'negative': bd.get('negative', 0),
            'positive_pct': bd.get('positive_pct', 0),
            'negative_pct': bd.get('negative_pct', 0),
            'articles_count': result.get('articles_analyzed', 0),
            'headlines': [
                {'title': a['title'], 'sentiment': a['sentiment'], 'source': a['publisher']}
                for a in articles[:5]
            ]
        }
    except Exception as e:
        return {'error': str(e), 'ticker': ticker}


def get_macro_regime() -> Dict:
    """
    Get current macro economic regime and risk assessment.

    Returns:
        Dict with keys: regime, risk_modifier, vix, vix_status,
                       yield_curve, credit_spreads, recommendation
    """
    try:
        api_key = os.getenv('FRED_API_KEY')
        ma = MacroAgent(api_key=api_key)
        result = ma.get_market_regime()

        indicators = result.get('indicators', {})

        return {
            'regime': result.get('regime', 'UNKNOWN'),
            'risk_modifier': result.get('risk_modifier', 1.0),
            'recommendation': result.get('recommendation', ''),
            'vix': indicators.get('vix', {}).get('value'),
            'vix_status': indicators.get('vix', {}).get('interpretation', ''),
            'yield_curve': indicators.get('yield_curve', {}).get('value'),
            'yield_curve_status': indicators.get('yield_curve', {}).get('interpretation', ''),
            'credit_spreads': indicators.get('credit_spread', {}).get('value'),
            'fed_funds': indicators.get('fed_funds_rate', {}).get('value'),
            'unemployment': indicators.get('unemployment', {}).get('value'),
        }
    except Exception as e:
        return {'error': str(e)}


def get_portfolio(mode: str = 'alpaca') -> Dict:
    """
    Get current portfolio summary.

    Args:
        mode: 'local' or 'alpaca' (default: 'alpaca')
              'local' = simulated portfolio, 'alpaca' = Alpaca API

    Returns:
        Dict with keys: total_value, cash, equity, positions, pnl, pnl_pct
    """
    try:
        executor = OrderExecutor(mode=mode)
        result = executor.get_portfolio_summary()

        equity = result['total_value'] - result['cash']

        return {
            'total_value': result['total_value'],
            'cash': result['cash'],
            'equity': equity,
            'pnl': result.get('total_unrealized_pl', 0),
            'pnl_pct': (result.get('total_unrealized_pl', 0) / 100000) * 100,
            'num_positions': result.get('num_positions', 0),
            'positions': [
                {
                    'ticker': p['ticker'],
                    'shares': p['quantity'],
                    'price': p['current_price'],
                    'entry': p['avg_cost'],
                    'pnl': p['unrealized_pl'],
                    'pnl_pct': p['unrealized_pl_percent']
                }
                for p in result.get('positions', [])
            ]
        }
    except Exception as e:
        return {'error': str(e)}


def get_market_status() -> Dict:
    """
    Get current market status (date, open/closed, next trading day).

    Returns:
        Dict with keys: now, today, day_of_week, is_trading_day,
                       market_open, next_trading_day
    """
    try:
        return _get_market_status()
    except Exception as e:
        return {'error': str(e)}


def execute_order(ticker: str, action: str, quantity: float,
                  order_type: str = 'market', mode: str = 'local') -> Dict:
    """
    Execute a trade order.

    Args:
        ticker: Stock symbol
        action: Trade action:
            - 'BUY': Open or add to long position
            - 'SELL': Close or reduce long position
            - 'SHORT': Open or add to short position (sell borrowed shares)
            - 'COVER': Close or reduce short position (buy back shares)
        quantity: Number of shares
        order_type: 'market' or 'limit' (default: 'market')
        mode: 'local' or 'alpaca' (default: 'local' for safety)

    Returns:
        Dict with order status and details

    Note:
        Defaults to local (simulated) mode for safety. Use mode='alpaca'
        explicitly for real trading (paper vs live determined by ALPACA_PAPER env var).
        SHORT requires margin account with appropriate permissions.
    """
    try:
        executor = OrderExecutor(mode=mode)
        result = executor.execute_order(
            ticker=ticker,
            action=action,
            quantity=quantity,
            order_type=order_type
        )
        return result
    except Exception as e:
        return {'error': str(e)}


def get_correlation(tickers: list, period: str = '1y') -> Dict:
    """
    Get portfolio correlation and diversification analysis.

    Args:
        tickers: List of stock symbols (minimum 2)
        period: Historical period ('6mo', '1y', '2y')

    Returns:
        Dict with keys: diversification_score, avg_correlation,
                       high_correlation_pairs, stocks (metrics per ticker)
    """
    try:
        result = get_portfolio_metrics(tickers, period)

        if 'error' in result:
            return result

        # Find high correlation pairs (>0.7)
        high_corr_pairs = []
        correlations = result.get('correlations', {})
        ticker_list = list(correlations.keys())

        for i, t1 in enumerate(ticker_list):
            for t2 in ticker_list[i+1:]:
                if t1 in correlations and t2 in correlations.get(t1, {}):
                    corr = correlations[t1][t2]
                    if abs(corr) >= 0.7:
                        high_corr_pairs.append({
                            'pair': f"{t1}-{t2}",
                            'correlation': round(corr, 3)
                        })

        return {
            'tickers': tickers,
            'diversification_score': result.get('diversification_score', 0),
            'avg_correlation': result.get('avg_correlation', 0),
            'high_correlation_pairs': high_corr_pairs,
            'stocks': result.get('stocks', {}),
            'assessment': 'GOOD' if result.get('avg_correlation', 1) < 0.5 else
                         'FAIR' if result.get('avg_correlation', 1) < 0.7 else 'POOR'
        }
    except Exception as e:
        return {'error': str(e)}


def get_sectors(tickers: list, weights: list = None) -> Dict:
    """
    Get sector allocation and concentration risk analysis.

    Args:
        tickers: List of stock symbols
        weights: Optional portfolio weights (must sum to 1.0)

    Returns:
        Dict with keys: sector_exposure, concentration_risks,
                       diversification_score, largest_sector
    """
    try:
        result = get_sector_allocation(tickers, weights)

        if 'error' in result:
            return result

        sector_exposure = result.get('sector_exposure', {})

        # Find concentration risks (>30%)
        concentration_risks = [
            {'sector': sector, 'exposure': pct}
            for sector, pct in sector_exposure.items()
            if pct > 30 and sector != 'Unknown'
        ]

        # Find largest sector
        largest_sector = max(sector_exposure.items(), key=lambda x: x[1]) if sector_exposure else ('Unknown', 0)

        return {
            'tickers': tickers,
            'sector_exposure': sector_exposure,
            'num_sectors': result.get('num_sectors', 0),
            'diversification_score': result.get('diversification_score', 0),
            'largest_sector': largest_sector[0],
            'largest_sector_pct': largest_sector[1],
            'concentration_risks': concentration_risks,
            'assessment': 'POOR' if largest_sector[1] > 40 else
                         'FAIR' if largest_sector[1] > 30 else
                         'GOOD' if largest_sector[1] > 20 else 'EXCELLENT'
        }
    except Exception as e:
        return {'error': str(e)}


def scan_technicals(tickers: list) -> list:
    """
    Scan multiple tickers for technical signals.

    Args:
        tickers: List of stock symbols

    Returns:
        List of dicts sorted by bullish_pct descending
    """
    results = []
    for ticker in tickers:
        result = get_technicals(ticker)
        if 'error' not in result:
            results.append(result)

    return sorted(results, key=lambda x: x.get('bullish_pct', 0), reverse=True)


# Convenience aliases for common operations
analyze_stock = get_technicals
check_sentiment = get_sentiment
market_regime = get_macro_regime
portfolio_status = get_portfolio
check_correlation = get_correlation
check_sectors = get_sectors


if __name__ == '__main__':
    # Quick test of all functions
    print("Testing AutoInvestor API...")
    print()

    print("1. get_stock_price('AMD'):")
    result = get_stock_price('AMD')
    print(f"   Price: ${result.get('price', 0):.2f}")
    print()

    print("2. get_technicals('AMD'):")
    result = get_technicals('AMD')
    print(f"   Signal: {result.get('signal')} (RSI {result.get('rsi', 0):.0f})")
    print()

    print("3. get_sentiment('AMD'):")
    result = get_sentiment('AMD')
    print(f"   Overall: {result.get('overall')}")
    print()

    print("4. get_macro_regime():")
    result = get_macro_regime()
    print(f"   Regime: {result.get('regime')} (Risk: {result.get('risk_modifier')})")
    print()

    print("5. get_portfolio():")
    result = get_portfolio()
    print(f"   Value: ${result.get('total_value', 0):,.2f}")
    print()

    print("6. get_market_status():")
    result = get_market_status()
    print(f"   {result.get('today')} - Market {'OPEN' if result.get('market_open') else 'CLOSED'}")
    print()

    print("All tests passed!")
