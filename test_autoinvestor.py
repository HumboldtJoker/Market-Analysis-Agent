#!/usr/bin/env python3
"""
Test script for AutoInvestor ReAct Agent
"""

import os
import sys

# Make sure autoinvestor_react is importable
sys.path.insert(0, os.path.dirname(__file__))

from autoinvestor_react import ReActAgent, Tool, mock_get_stock_price, mock_get_company_financials, mock_get_analyst_ratings, mock_calculate_valuation, mock_risk_assessment


def test_mock_tools():
    """Test that all mock tools work correctly"""
    print("Testing mock tools...")

    # Test get_stock_price
    print("\n1. Testing get_stock_price:")
    result = mock_get_stock_price("AAPL")
    print(f"   ✓ AAPL price: ${result['price']}")

    # Test get_company_financials
    print("\n2. Testing get_company_financials:")
    result = mock_get_company_financials("NVDA", "income")
    print(f"   ✓ NVDA revenue: ${result['revenue']:,}")
    print(f"   ✓ Revenue growth: {result['revenue_growth_yoy']}%")

    # Test get_analyst_ratings
    print("\n3. Testing get_analyst_ratings:")
    result = mock_get_analyst_ratings("NVDA")
    print(f"   ✓ Consensus: {result['consensus']}")
    print(f"   ✓ Average target: ${result['price_target']['average']}")

    # Test calculate_valuation
    print("\n4. Testing calculate_valuation:")
    result = mock_calculate_valuation("AAPL")
    print(f"   ✓ P/E ratio: {result['pe_ratio']}")
    print(f"   ✓ PEG ratio: {result['peg_ratio']}")

    # Test risk_assessment
    print("\n5. Testing risk_assessment:")
    result = mock_risk_assessment("NVDA")
    print(f"   ✓ Risk score: {result['risk_score']}/10")
    print(f"   ✓ Beta: {result['beta']}")

    print("\n✓ All mock tools working correctly!")


def test_tool_registry():
    """Test tool registration system"""
    print("\n" + "="*80)
    print("Testing Tool Registry...")
    print("="*80)

    from autoinvestor_react import ToolRegistry

    registry = ToolRegistry()

    # Register a test tool
    registry.register(Tool(
        name="test_tool",
        description="A test tool",
        parameters={"param1": "string"},
        function=lambda param1: {"result": f"Got {param1}"}
    ))

    # Check it was registered
    tool = registry.get("test_tool")
    print(f"✓ Tool registered: {tool.name}")

    # Execute it
    result = tool.execute(param1="test_value")
    print(f"✓ Tool executed: {result}")

    # Get tool descriptions
    descriptions = registry.get_descriptions()
    print(f"✓ Tool descriptions generated ({len(descriptions)} chars)")


def test_agent_initialization():
    """Test agent can be initialized"""
    print("\n" + "="*80)
    print("Testing Agent Initialization...")
    print("="*80)

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        print("⚠ ANTHROPIC_API_KEY not set - skipping agent initialization test")
        print("  Set environment variable to test full agent")
        return False

    try:
        agent = ReActAgent(api_key=api_key, max_iterations=5)
        print(f"✓ Agent initialized with model: {agent.model}")

        # Register mock tools
        agent.tools.register(Tool(
            name="get_stock_price",
            description="Get current stock price",
            parameters={"ticker": "string"},
            function=mock_get_stock_price
        ))

        print(f"✓ Registered {len(agent.tools.tools)} tools")
        return True

    except Exception as e:
        print(f"✗ Agent initialization failed: {e}")
        return False


def test_full_agent_run():
    """Test full agent run with real Claude API"""
    print("\n" + "="*80)
    print("Testing Full Agent Run...")
    print("="*80)

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        print("⚠ ANTHROPIC_API_KEY not set - skipping full agent test")
        print("  Set environment variable: export ANTHROPIC_API_KEY='your-key-here'")
        return

    # Initialize agent
    agent = ReActAgent(api_key=api_key, max_iterations=6)

    # Register all mock tools
    agent.tools.register(Tool(
        name="get_stock_price",
        description="Get current stock price and trading data",
        parameters={"ticker": "string (stock symbol)"},
        function=mock_get_stock_price
    ))

    agent.tools.register(Tool(
        name="get_company_financials",
        description="Get company financial statements",
        parameters={"ticker": "string", "statement": "string (optional)"},
        function=mock_get_company_financials
    ))

    agent.tools.register(Tool(
        name="get_analyst_ratings",
        description="Get analyst consensus and price targets",
        parameters={"ticker": "string"},
        function=mock_get_analyst_ratings
    ))

    agent.tools.register(Tool(
        name="calculate_valuation",
        description="Calculate valuation metrics",
        parameters={"ticker": "string"},
        function=mock_calculate_valuation
    ))

    agent.tools.register(Tool(
        name="risk_assessment",
        description="Assess investment risk",
        parameters={"ticker": "string"},
        function=mock_risk_assessment
    ))

    # Run test query
    print("\nRunning query: 'Is Apple a good buy right now?'\n")

    result = agent.run(
        "Is Apple a good buy right now? Give me a brief recommendation.",
        verbose=True
    )

    if result["success"]:
        print("\n✓ Agent run completed successfully!")
        print(f"  Iterations: {result['iterations']}")
    else:
        print(f"\n✗ Agent run failed: {result.get('error')}")


if __name__ == "__main__":
    print("="*80)
    print("AUTOINVESTOR REACT AGENT TEST SUITE")
    print("="*80)

    # Test 1: Mock tools
    test_mock_tools()

    # Test 2: Tool registry
    test_tool_registry()

    # Test 3: Agent initialization
    agent_initialized = test_agent_initialization()

    # Test 4: Full run (only if API key available)
    if agent_initialized:
        print("\n" + "="*80)
        print("READY FOR FULL AGENT TEST")
        print("="*80)
        print("\nTo run full agent test with Claude:")
        print("  python test_autoinvestor.py --full")
        print()

        if "--full" in sys.argv:
            test_full_agent_run()

    print("\n" + "="*80)
    print("TEST SUITE COMPLETE")
    print("="*80)
