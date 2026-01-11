#!/usr/bin/env python3
"""
MCP Wrapper for Market Analysis Agent
Bridges MCP calls to existing Python analysis tools
"""

import sys
import json
import os
from typing import Dict, List, Optional
import traceback

# Add current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the existing analysis modules
try:
    from autoinvestor_react import ReActAgent, Tool
    from collaborative_agent import CollaborativeAgent
    from technical_indicators import get_technical_indicators
    from congressional_trades import get_congressional_trades
    from congressional_trades_aggregate import get_aggregate_analysis
    from portfolio_correlation import analyze_portfolio_correlation
    from macro_agent import MacroAgent
    from investor_profile import InvestorProfile
    from news_sentiment import get_news_sentiment
except ImportError as e:
    print(f"Error importing modules: {e}", file=sys.stderr)
    sys.exit(1)

def setup_basic_agent():
    """Set up the basic ReAct agent with tools"""
    # Note: This would normally require an API key
    # For MCP integration, we'll modify to use Claude via MCP instead

    # Import the tool functions
    from autoinvestor_react import (
        get_stock_price,
        get_company_financials,
        get_analyst_ratings,
        calculate_valuation,
        risk_assessment
    )

    # Create agent - we'll modify this to use MCP instead of direct API calls
    agent = ReActAgent(api_key="mcp_placeholder")  # Will be replaced with MCP calls

    # Register tools
    tools = [
        Tool(
            name="get_stock_price",
            description="Get current stock price and trading data from Yahoo Finance",
            parameters={"ticker": "string (stock symbol, e.g., 'AAPL')"},
            function=get_stock_price
        ),
        Tool(
            name="get_company_financials",
            description="Get financial metrics like revenue, earnings, margins",
            parameters={"ticker": "string (stock symbol, e.g., 'AAPL')"},
            function=get_company_financials
        ),
        Tool(
            name="get_analyst_ratings",
            description="Get analyst consensus ratings and price targets",
            parameters={"ticker": "string (stock symbol, e.g., 'AAPL')"},
            function=get_analyst_ratings
        ),
        Tool(
            name="calculate_valuation",
            description="Calculate valuation metrics like P/E, PEG ratios",
            parameters={"ticker": "string (stock symbol, e.g., 'AAPL')"},
            function=calculate_valuation
        ),
        Tool(
            name="risk_assessment",
            description="Assess stock risk factors and volatility",
            parameters={"ticker": "string (stock symbol, e.g., 'AAPL')"},
            function=risk_assessment
        )
    ]

    for tool in tools:
        agent.tools.register(tool)

    return agent

def analyze_stock(ticker: str, query: str, include_profile: bool = False):
    """Perform comprehensive stock analysis"""
    try:
        agent = setup_basic_agent()

        # Modify query to include profile context if requested
        if include_profile:
            profiler = InvestorProfile()
            # For MCP, we'll use a default profile or ask user to configure
            profile_context = "Using standard balanced investor profile for analysis."
            query = f"{query}\n\nInvestor Context: {profile_context}"

        # For now, let's return a structured analysis instead of full ReAct
        # This will be enhanced once we integrate with MCP for the AI reasoning

        # Get the raw data
        from autoinvestor_react import (
            get_stock_price, get_company_financials,
            get_analyst_ratings, calculate_valuation, risk_assessment
        )

        price_data = get_stock_price(ticker)
        financials = get_company_financials(ticker)
        ratings = get_analyst_ratings(ticker)
        valuation = calculate_valuation(ticker)
        risk_data = risk_assessment(ticker)

        # Format the response
        analysis = f"""
STOCK ANALYSIS: {ticker.upper()}

CURRENT PRICE DATA:
{json.dumps(price_data, indent=2)}

FINANCIAL METRICS:
{json.dumps(financials, indent=2)}

ANALYST RATINGS:
{json.dumps(ratings, indent=2)}

VALUATION METRICS:
{json.dumps(valuation, indent=2)}

RISK ASSESSMENT:
{json.dumps(risk_data, indent=2)}

QUERY: {query}

Note: Full AI reasoning analysis will be available once MCP integration is complete.
This provides the raw data that would be processed by Claude for investment recommendations.
"""

        return analysis

    except Exception as e:
        return f"Error in stock analysis: {str(e)}\nTraceback: {traceback.format_exc()}"

def collaborative_analysis(ticker: str, query: str, max_questions: int = 3):
    """Perform collaborative analysis with strategic questions"""
    try:
        # For now, return the basic analysis plus collaborative framework
        basic_analysis = analyze_stock(ticker, query)

        collaborative_response = f"""
COLLABORATIVE ANALYSIS MODE: {ticker.upper()}

{basic_analysis}

COLLABORATIVE FRAMEWORK:
This analysis would normally include strategic questions from the AI such as:
1. "Given the current valuation metrics, what's your risk tolerance for growth vs value?"
2. "The technical indicators show [pattern] - how does this fit your investment timeline?"
3. "Congressional trading data shows [activity] - do you have insights on sector trends?"

Max Questions Configured: {max_questions}

Note: Full collaborative dialogue will be available once MCP integration enables
real-time conversation flow with Claude Code/Desktop.
"""

        return collaborative_response

    except Exception as e:
        return f"Error in collaborative analysis: {str(e)}"

def congressional_trades_analysis(ticker: str):
    """Analyze congressional trading for specific ticker"""
    try:
        trades_data = get_congressional_trades(ticker)
        return f"Congressional Trading Analysis for {ticker.upper()}:\n{json.dumps(trades_data, indent=2)}"
    except Exception as e:
        return f"Error in congressional trades analysis: {str(e)}"

def aggregate_congressional_analysis_wrapper():
    """Analyze aggregate congressional trading patterns"""
    try:
        # This requires RAPIDAPI_KEY environment variable
        api_key = os.environ.get('RAPIDAPI_KEY')
        if not api_key:
            return "Error: RAPIDAPI_KEY environment variable not set. Please set it to access congressional trading data."

        aggregate_data = get_aggregate_analysis(api_key=api_key)
        return f"Aggregate Congressional Trading Analysis:\n{json.dumps(aggregate_data, indent=2)}"
    except Exception as e:
        return f"Error in aggregate congressional analysis: {str(e)}"

def technical_analysis_wrapper(ticker: str):
    """Perform technical analysis"""
    try:
        tech_data = get_technical_indicators(ticker)
        return f"Technical Analysis for {ticker.upper()}:\n{json.dumps(tech_data, indent=2)}"
    except Exception as e:
        return f"Error in technical analysis: {str(e)}"

def portfolio_analysis_wrapper(tickers_json: str):
    """Analyze portfolio correlation"""
    try:
        tickers = json.loads(tickers_json)
        correlation_data = analyze_portfolio_correlation(tickers)
        return f"Portfolio Correlation Analysis:\n{json.dumps(correlation_data, indent=2)}"
    except Exception as e:
        return f"Error in portfolio analysis: {str(e)}"

def macro_analysis_wrapper():
    """Perform macro economic analysis"""
    try:
        # This requires FRED_API_KEY environment variable
        macro_agent = MacroAgent()
        regime_data = macro_agent.get_market_regime()
        report = macro_agent.format_report()

        return f"Macro Economic Analysis:\n{report}\n\nDetailed Data:\n{json.dumps(regime_data, indent=2)}"
    except Exception as e:
        return f"Error in macro analysis: {str(e)}\nNote: Ensure FRED_API_KEY environment variable is set."

def main():
    """Main entry point for MCP wrapper"""
    if len(sys.argv) < 2:
        print("Error: No command specified", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "analyze_stock":
            if len(sys.argv) < 4:
                print("Error: analyze_stock requires ticker and query arguments", file=sys.stderr)
                sys.exit(1)
            ticker = sys.argv[2]
            query = sys.argv[3]
            include_profile = sys.argv[4].lower() == 'true' if len(sys.argv) > 4 else False
            result = analyze_stock(ticker, query, include_profile)

        elif command == "collaborative_analysis":
            if len(sys.argv) < 4:
                print("Error: collaborative_analysis requires ticker and query arguments", file=sys.stderr)
                sys.exit(1)
            ticker = sys.argv[2]
            query = sys.argv[3]
            max_questions = int(sys.argv[4]) if len(sys.argv) > 4 else 3
            result = collaborative_analysis(ticker, query, max_questions)

        elif command == "congressional_trades":
            if len(sys.argv) < 3:
                print("Error: congressional_trades requires ticker argument", file=sys.stderr)
                sys.exit(1)
            ticker = sys.argv[2]
            result = congressional_trades_analysis(ticker)

        elif command == "aggregate_congressional_analysis":
            result = aggregate_congressional_analysis_wrapper()

        elif command == "technical_analysis":
            if len(sys.argv) < 3:
                print("Error: technical_analysis requires ticker argument", file=sys.stderr)
                sys.exit(1)
            ticker = sys.argv[2]
            result = technical_analysis_wrapper(ticker)

        elif command == "portfolio_analysis":
            if len(sys.argv) < 3:
                print("Error: portfolio_analysis requires tickers JSON argument", file=sys.stderr)
                sys.exit(1)
            tickers_json = sys.argv[2]
            result = portfolio_analysis_wrapper(tickers_json)

        elif command == "macro_analysis":
            result = macro_analysis_wrapper()

        else:
            print(f"Error: Unknown command: {command}", file=sys.stderr)
            sys.exit(1)

        print(result)

    except Exception as e:
        print(f"Error executing command {command}: {str(e)}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()