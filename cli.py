#!/usr/bin/env python3
"""
AutoInvestor CLI - Command-line interface for investment analysis

Usage:
    python cli.py analyze TICKER [--collaborative]
    python cli.py technicals TICKER [--period DAYS]
    python cli.py congress [TICKER] [--aggregate]
    python cli.py portfolio TICKER1 TICKER2 ...
    python cli.py sectors TICKER:SHARES ...

Examples:
    python cli.py analyze NVDA
    python cli.py analyze MSFT --collaborative
    python cli.py technicals AAPL --period 90
    python cli.py congress --aggregate
    python cli.py congress AVGO
    python cli.py portfolio AAPL MSFT GOOGL AMZN
    python cli.py sectors AAPL:100 JPM:50 XOM:30

Author: Lyra & Thomas (Coalition)
Version: 1.0.0
"""

import argparse
import os
import sys
from typing import List, Dict

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)


def cmd_analyze(ticker: str, collaborative: bool = False):
    """Run full ReAct analysis on a ticker"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable required")
        print("Set it with: export ANTHROPIC_API_KEY=your_key_here")
        return

    # Import and setup agent
    from autoinvestor_react import ReActAgent, Tool, ToolRegistry
    from autoinvestor_react import get_stock_price, get_company_financials
    from autoinvestor_react import get_analyst_ratings, calculate_valuation, risk_assessment
    from technical_indicators import analyze_technicals
    from news_sentiment import analyze_news_sentiment

    if collaborative:
        from collaborative_agent import CollaborativeAgent
        agent = CollaborativeAgent(api_key=api_key, max_iterations=10)
    else:
        agent = ReActAgent(api_key=api_key, max_iterations=10)

    # Register Phase 1 tools
    agent.tools.register(Tool(
        name="get_stock_price",
        description="Get current stock price, volume, and 52-week range",
        func=get_stock_price,
        parameters={"ticker": "Stock ticker symbol (e.g., 'AAPL')"}
    ))
    agent.tools.register(Tool(
        name="get_company_financials",
        description="Get company financial metrics (revenue, earnings, margins)",
        func=get_company_financials,
        parameters={"ticker": "Stock ticker symbol"}
    ))
    agent.tools.register(Tool(
        name="get_analyst_ratings",
        description="Get analyst consensus ratings and price targets",
        func=get_analyst_ratings,
        parameters={"ticker": "Stock ticker symbol"}
    ))
    agent.tools.register(Tool(
        name="calculate_valuation",
        description="Calculate valuation metrics (P/E, PEG, P/B, EV/EBITDA)",
        func=calculate_valuation,
        parameters={"ticker": "Stock ticker symbol"}
    ))
    agent.tools.register(Tool(
        name="risk_assessment",
        description="Assess investment risk (beta, volatility, debt ratios)",
        func=risk_assessment,
        parameters={"ticker": "Stock ticker symbol"}
    ))

    # Register Phase 2 tools
    agent.tools.register(Tool(
        name="analyze_technicals",
        description="Technical analysis with SMA, RSI, MACD, Bollinger Bands",
        func=analyze_technicals,
        parameters={"ticker": "Stock ticker symbol", "period": "Days of history (default: 90)"}
    ))
    agent.tools.register(Tool(
        name="analyze_news_sentiment",
        description="Analyze recent news sentiment for a stock",
        func=analyze_news_sentiment,
        parameters={"ticker": "Stock ticker symbol"}
    ))

    # Run analysis
    query = f"Provide a comprehensive investment analysis of {ticker}. Include current price, financials, technicals, news sentiment, and your recommendation."

    print(f"\n{'='*60}")
    print(f"AutoInvestor Analysis: {ticker}")
    print(f"Mode: {'Collaborative' if collaborative else 'Standard'}")
    print(f"{'='*60}\n")

    if collaborative:
        result = agent.run_collaborative(query, max_questions=3, verbose=True)
    else:
        result = agent.run(query, verbose=True)

    print(f"\n{'='*60}")
    print("FINAL RECOMMENDATION")
    print(f"{'='*60}")
    print(result.get('answer', 'No answer generated'))

    print("\n" + "-"*60)
    print("DISCLAIMER: This is NOT financial advice. Consult a licensed")
    print("financial advisor before making investment decisions.")
    print("-"*60)


def cmd_technicals(ticker: str, period: int = 90):
    """Run technical analysis on a ticker"""
    from technical_indicators import analyze_technicals

    print(f"\nRunning technical analysis for {ticker}...\n")
    result = analyze_technicals(ticker)  # Period is hardcoded in the tool

    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print(result['summary'])


def cmd_congress(ticker: str = None, aggregate: bool = False):
    """Check congressional trading activity"""
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        print("ERROR: RAPIDAPI_KEY environment variable required")
        print("Get free API key at: https://rapidapi.com/politics-trackers-politics-trackers-default/api/politician-trade-tracker")
        return

    if aggregate:
        from congressional_trades_aggregate import get_aggregate_analysis
        print("\nFetching aggregate congressional trading patterns...\n")
        result = get_aggregate_analysis(api_key=api_key)
    else:
        if not ticker:
            print("ERROR: Ticker required for individual analysis. Use --aggregate for overall trends.")
            return
        from congressional_trades import analyze_congressional_trades
        print(f"\nFetching congressional trades for {ticker}...\n")
        result = analyze_congressional_trades(ticker, api_key=api_key)

    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print(result['summary'])


def cmd_portfolio(tickers: List[str]):
    """Analyze portfolio correlation and diversification"""
    from portfolio_correlation import analyze_portfolio_correlation

    print(f"\nAnalyzing portfolio correlation for: {', '.join(tickers)}...\n")
    result = analyze_portfolio_correlation(tickers)

    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print(result['summary'])


def cmd_sectors(holdings: List[str]):
    """Analyze sector allocation of portfolio"""
    from sector_allocation import analyze_sector_allocation

    # Parse holdings (format: TICKER:SHARES)
    portfolio = {}
    for holding in holdings:
        if ':' in holding:
            ticker, shares = holding.split(':')
            portfolio[ticker.upper()] = int(shares)
        else:
            portfolio[holding.upper()] = 1  # Default to 1 share

    print(f"\nAnalyzing sector allocation...\n")
    result = analyze_sector_allocation(portfolio)

    if "error" in result:
        print(f"ERROR: {result['error']}")
    else:
        print(result['summary'])


def cmd_backtest(windows_str: str = "30,60,90"):
    """Backtest congressional trading strategy"""
    from backtesting import run_backtest_from_api, format_backtest_report

    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        print("ERROR: RAPIDAPI_KEY environment variable required")
        print("Get free API key at: https://rapidapi.com/politics-trackers-politics-trackers-default/api/politician-trade-tracker")
        return

    # Parse windows
    try:
        windows = [int(w.strip()) for w in windows_str.split(',')]
    except ValueError:
        print("ERROR: Windows must be comma-separated integers (e.g., 30,60,90)")
        return

    print(f"\nRunning congressional trading backtest...")
    print(f"Return windows: {windows} days\n")

    results = run_backtest_from_api(api_key=api_key, verbose=True)

    if "error" in results:
        print(f"ERROR: {results['error']}")
    else:
        report = format_backtest_report(results)
        print(report)


def main():
    parser = argparse.ArgumentParser(
        description="AutoInvestor CLI - AI-powered investment research",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py analyze NVDA                    Full analysis of NVIDIA
  python cli.py analyze MSFT --collaborative    Interactive analysis with questions
  python cli.py technicals AAPL                 Technical indicators for Apple
  python cli.py congress --aggregate            Overall congressional trading trends
  python cli.py congress AVGO                   Congressional trades for Broadcom
  python cli.py portfolio AAPL MSFT GOOGL       Portfolio correlation analysis
  python cli.py sectors AAPL:100 JPM:50         Sector allocation analysis
  python cli.py backtest                        Backtest congressional trading strategy

Environment Variables:
  ANTHROPIC_API_KEY   Required for 'analyze' command
  RAPIDAPI_KEY        Required for 'congress' and 'backtest' commands
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Full ReAct analysis of a stock')
    analyze_parser.add_argument('ticker', help='Stock ticker symbol')
    analyze_parser.add_argument('--collaborative', '-c', action='store_true',
                               help='Enable collaborative mode (AI asks questions)')

    # technicals command
    tech_parser = subparsers.add_parser('technicals', help='Technical analysis (SMA, RSI, MACD, Bollinger)')
    tech_parser.add_argument('ticker', help='Stock ticker symbol')
    tech_parser.add_argument('--period', '-p', type=int, default=90,
                            help='Days of price history (default: 90)')

    # congress command
    congress_parser = subparsers.add_parser('congress', help='Congressional trading activity')
    congress_parser.add_argument('ticker', nargs='?', help='Stock ticker (optional if using --aggregate)')
    congress_parser.add_argument('--aggregate', '-a', action='store_true',
                                help='Show aggregate trends across all Congress')

    # portfolio command
    portfolio_parser = subparsers.add_parser('portfolio', help='Portfolio correlation analysis')
    portfolio_parser.add_argument('tickers', nargs='+', help='Stock tickers in portfolio')

    # sectors command
    sectors_parser = subparsers.add_parser('sectors', help='Sector allocation analysis')
    sectors_parser.add_argument('holdings', nargs='+',
                               help='Holdings as TICKER:SHARES (e.g., AAPL:100)')

    # backtest command
    backtest_parser = subparsers.add_parser('backtest', help='Backtest congressional trading strategy')
    backtest_parser.add_argument('--windows', '-w', type=str, default='30,60,90',
                                help='Comma-separated return windows in days (default: 30,60,90)')

    args = parser.parse_args()

    if args.command == 'analyze':
        cmd_analyze(args.ticker, args.collaborative)
    elif args.command == 'technicals':
        cmd_technicals(args.ticker, args.period)
    elif args.command == 'congress':
        cmd_congress(args.ticker, args.aggregate)
    elif args.command == 'portfolio':
        cmd_portfolio(args.tickers)
    elif args.command == 'sectors':
        cmd_sectors(args.holdings)
    elif args.command == 'backtest':
        cmd_backtest(args.windows)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
