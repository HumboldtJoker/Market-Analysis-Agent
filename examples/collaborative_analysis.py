"""
Example: Collaborative Investment Analysis

Demonstrates human-AI collaborative decision-making where:
1. AI analyzes stock using all available tools
2. AI generates strategic questions based on findings
3. Human provides context/intuition
4. AI synthesizes recommendation incorporating both perspectives

This is the Coalition philosophy in action: augmentation over replacement.
"""

import os
import sys
sys.path.append('..')

from collaborative_agent import CollaborativeAgent
from autoinvestor_react import Tool

# Import all analysis tools
from autoinvestor_react import (
    get_stock_price,
    get_company_financials,
    get_analyst_ratings,
    calculate_valuation,
    risk_assessment
)

# Import Phase 2 tools
from technical_indicators import analyze_technicals
from news_sentiment import analyze_news_sentiment
from congressional_trades import analyze_congressional_trades
from portfolio_correlation import analyze_portfolio_correlation
from sector_allocation import analyze_sector_allocation


def main():
    """Run collaborative analysis on a stock"""

    # Initialize collaborative agent
    agent = CollaborativeAgent(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        max_iterations=12
    )

    # Register all tools
    print("Registering analysis tools...")

    # Phase 1 tools
    agent.tools.register(Tool(
        name="get_stock_price",
        description="Get current stock price, volume, and trading data from Yahoo Finance",
        parameters={"ticker": "string (stock symbol)"},
        function=get_stock_price
    ))

    agent.tools.register(Tool(
        name="get_company_financials",
        description="Get company financial statements, revenue, earnings, margins",
        parameters={"ticker": "string (stock symbol)"},
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
        description="Calculate valuation ratios: P/E, PEG, P/B, EV/EBITDA",
        parameters={"ticker": "string (stock symbol)"},
        function=calculate_valuation
    ))

    agent.tools.register(Tool(
        name="risk_assessment",
        description="Assess investment risks: volatility, beta, debt ratios",
        parameters={"ticker": "string (stock symbol)"},
        function=risk_assessment
    ))

    # Phase 2 tools
    agent.tools.register(Tool(
        name="analyze_technicals",
        description="Technical analysis: SMA, RSI, MACD, Bollinger Bands",
        parameters={"ticker": "string (stock symbol)"},
        function=lambda ticker: analyze_technicals(ticker)["summary"]
    ))

    agent.tools.register(Tool(
        name="analyze_news_sentiment",
        description="Analyze sentiment from recent financial news articles",
        parameters={"ticker": "string (stock symbol)"},
        function=lambda ticker: analyze_news_sentiment(ticker)["summary"]
    ))

    agent.tools.register(Tool(
        name="analyze_congressional_trades",
        description="Track congressional STOCK Act disclosures (insider information)",
        parameters={"ticker": "string (stock symbol)"},
        function=lambda ticker: analyze_congressional_trades(ticker)["summary"]
    ))

    print("Tools registered. Ready for collaborative analysis.\n")

    # Get query from command line or use default
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Should I invest in NVIDIA (NVDA) right now? I'm a long-term investor."

    # Run collaborative analysis
    print(f"\nQuery: {query}\n")
    print("="*80)
    print("COLLABORATIVE MODE")
    print("="*80)
    print("\nThe AI will analyze the stock, then ask you strategic questions")
    print("to incorporate your insights into the final recommendation.\n")
    print("Press Enter to skip any question and let AI decide autonomously.")
    print("="*80)

    result = agent.run_collaborative(
        query,
        max_questions=3,  # Ask up to 3 strategic questions
        verbose=True
    )

    # Show results
    print("\n\n" + "="*80)
    print("COLLABORATIVE ANALYSIS COMPLETE")
    print("="*80)

    print(f"\nAI conducted {result['iterations']} research iterations")
    print(f"Asked {len(result['questions_asked'])} strategic questions")
    print(f"Received {len([r for r in result['human_responses'] if not r['skipped']])} human insights")

    print(f"\n\nSYNTHESIS RATIONALE:")
    print(result['synthesis_rationale'])

    # Save full results
    import json
    output_file = "collaborative_analysis_results.json"
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"\n\nFull results saved to: {output_file}")
    print("\nThis collaborative recommendation combines:")
    print("  ✓ AI's comprehensive data analysis")
    print("  ✓ Your contextual knowledge and preferences")
    print("  ✓ Clear attribution of how insights were integrated")
    print("\nAugmentation, not replacement. 🤝")


if __name__ == "__main__":
    main()
