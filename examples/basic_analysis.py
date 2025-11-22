#!/usr/bin/env python3
"""
Basic Stock Analysis Example

This example shows how to use AutoInvestor to analyze a stock
with all available tools.
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from autoinvestor_react import ReActAgent, Tool
from autoinvestor_react import (
    get_stock_price,
    get_company_financials,
    get_analyst_ratings,
    calculate_valuation,
    risk_assessment
)


def main():
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Please set ANTHROPIC_API_KEY environment variable")
        print("\nOn Linux/Mac:")
        print('  export ANTHROPIC_API_KEY="your-key-here"')
        print("\nOn Windows:")
        print('  set ANTHROPIC_API_KEY=your-key-here')
        sys.exit(1)

    # Initialize agent
    print("Initializing AutoInvestor agent...")
    agent = ReActAgent(api_key=api_key, max_iterations=12)

    # Register all analysis tools
    print("Registering analysis tools...")

    agent.tools.register(Tool(
        name="get_stock_price",
        description="Get current stock price and trading data from Yahoo Finance",
        parameters={"ticker": "string (stock symbol, e.g., 'AAPL')"},
        function=get_stock_price
    ))

    agent.tools.register(Tool(
        name="get_company_financials",
        description="Get company financial statements from Yahoo Finance (revenue, earnings, margins, etc.)",
        parameters={
            "ticker": "string (stock symbol)",
            "statement": "string (optional: 'income', 'balance', 'cashflow', default='income')"
        },
        function=get_company_financials
    ))

    agent.tools.register(Tool(
        name="get_analyst_ratings",
        description="Get analyst consensus ratings and price targets from Yahoo Finance",
        parameters={"ticker": "string (stock symbol)"},
        function=get_analyst_ratings
    ))

    agent.tools.register(Tool(
        name="calculate_valuation",
        description="Calculate valuation metrics from Yahoo Finance (P/E, PEG, P/B, EV/Revenue, etc.)",
        parameters={"ticker": "string (stock symbol)"},
        function=calculate_valuation
    ))

    agent.tools.register(Tool(
        name="risk_assessment",
        description="Assess investment risk factors using Yahoo Finance data (beta, volatility, debt ratios)",
        parameters={"ticker": "string (stock symbol)"},
        function=risk_assessment
    ))

    # Run analysis
    print("\n" + "="*80)
    print("STARTING ANALYSIS")
    print("="*80 + "\n")

    # You can change the query and ticker here
    query = "Should I invest in Apple (AAPL) right now? Give me a clear buy/sell/hold recommendation with supporting analysis."

    result = agent.run(query, verbose=True)

    # Print final recommendation
    if result['success']:
        print("\n" + "="*80)
        print("FINAL RECOMMENDATION")
        print("="*80)
        print(f"\n{result['answer']}\n")
        print(f"Analysis completed in {result['iterations']} iterations")
    else:
        print(f"\nAnalysis failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
