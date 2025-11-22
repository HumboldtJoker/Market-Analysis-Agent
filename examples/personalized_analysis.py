#!/usr/bin/env python3
"""
Personalized Stock Analysis Example

This example shows how to use AutoInvestor with an investor profile
to get personalized recommendations tailored to your goals and risk tolerance.
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
from investor_profile import InvestorProfile


def main():
    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: Please set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    # Step 1: Create investor profile
    print("="*80)
    print("STEP 1: BUILD YOUR INVESTOR PROFILE")
    print("="*80)

    profiler = InvestorProfile()

    # Try to load existing profile
    if os.path.exists("investor_profile.json"):
        print("\nFound existing profile. Use it?")
        use_existing = input("(yes/no): ").strip().lower()
        if use_existing == 'yes':
            profiler.load_from_file()
        else:
            profile = profiler.interview()
            profiler.save_to_file()
    else:
        profile = profiler.interview()
        profiler.save_to_file()

    # Step 2: Initialize agent
    print("\n" + "="*80)
    print("STEP 2: INITIALIZE AUTOINVESTOR AGENT")
    print("="*80)

    agent = ReActAgent(api_key=api_key, max_iterations=12)

    # Register tools (same as basic_analysis.py)
    agent.tools.register(Tool(
        name="get_stock_price",
        description="Get current stock price and trading data from Yahoo Finance",
        parameters={"ticker": "string (stock symbol)"},
        function=get_stock_price
    ))

    agent.tools.register(Tool(
        name="get_company_financials",
        description="Get company financial statements from Yahoo Finance",
        parameters={"ticker": "string (stock symbol)", "statement": "string (optional)"},
        function=get_company_financials
    ))

    agent.tools.register(Tool(
        name="get_analyst_ratings",
        description="Get analyst consensus ratings and price targets",
        parameters={"ticker": "string (stock symbol)"},
        function=get_analyst_ratings
    ))

    agent.tools.register(Tool(
        name="calculate_valuation",
        description="Calculate valuation metrics (P/E, PEG, P/B, etc.)",
        parameters={"ticker": "string (stock symbol)"},
        function=calculate_valuation
    ))

    agent.tools.register(Tool(
        name="risk_assessment",
        description="Assess investment risk factors (beta, volatility, debt)",
        parameters={"ticker": "string (stock symbol)"},
        function=risk_assessment
    ))

    # Step 3: Run personalized analysis
    print("\n" + "="*80)
    print("STEP 3: RUN PERSONALIZED ANALYSIS")
    print("="*80)

    ticker = input("\nEnter stock ticker to analyze (e.g., AAPL, TSLA, NVDA): ").strip().upper()

    # Build personalized query
    query = f"""
Analyze {ticker} for potential investment.

{profiler.get_analysis_context()}

Provide a clear BUY/SELL/HOLD recommendation with:
1. Supporting analysis based on fundamentals, valuation, and risk
2. Position sizing recommendation appropriate for my ${profiler.profile.get('investment_amount', 10000):,.2f} portfolio
3. Entry price and stop-loss levels
4. Timeframe for holding based on my investment horizon
5. Any specific concerns given my risk tolerance and goals

Be specific and actionable.
"""

    print(f"\nAnalyzing {ticker} based on your investor profile...\n")
    result = agent.run(query, verbose=True)

    # Print results
    if result['success']:
        print("\n" + "="*80)
        print("PERSONALIZED RECOMMENDATION")
        print("="*80)
        print(f"\n{result['answer']}\n")
        print(f"Analysis completed in {result['iterations']} iterations")
        print(f"Cost: ~$0.05")
    else:
        print(f"\nAnalysis failed: {result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()
