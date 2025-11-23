"""
Trading Agent for AutoInvestor

Extends ReAct agent with trading execution capabilities.
Integrates analysis tools with portfolio management, risk management, and execution.
"""

import os
from typing import Dict, Optional
from datetime import datetime

# Import existing components
from autoinvestor_react import ReActAgent, Tool
from order_executor import OrderExecutor
from risk_manager import RiskManager
from performance_tracker import PerformanceTracker
from investor_profile import InvestorProfile

# Import analysis tools from existing agent
from autoinvestor_react import (
    get_stock_price,
    get_company_financials,
    get_analyst_ratings,
    calculate_valuation,
    risk_assessment
)


class TradingAgent(ReActAgent):
    """
    AI Trading Agent with full execution capabilities

    Extends ReActAgent with:
    - Order execution (buy/sell)
    - Portfolio management
    - Risk management (position sizing, circuit breakers)
    - Performance tracking
    - Personalized recommendations based on investor profile
    """

    def __init__(self, mode: str = "paper", api_key: Optional[str] = None,
                 initial_cash: float = 100000.0,
                 investor_profile: Optional[InvestorProfile] = None,
                 max_iterations: int = 15):
        """
        Initialize trading agent

        Args:
            mode: 'paper' for simulated trading, 'live' for real trading
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            initial_cash: Starting cash for paper mode
            investor_profile: Optional investor profile for personalized recommendations
            max_iterations: Maximum ReAct iterations
        """
        # Initialize base ReAct agent
        super().__init__(api_key=api_key, max_iterations=max_iterations)

        self.mode = mode
        self.investor_profile = investor_profile

        # Initialize components
        self.executor = OrderExecutor(mode=mode)
        self.risk_manager = RiskManager(investor_profile=investor_profile)

        # Set initial cash for paper mode
        if mode == "paper" and not hasattr(self.executor.portfolio, 'initial_cash'):
            self.executor.portfolio.cash = initial_cash
            self.executor.portfolio.initial_cash = initial_cash

        self.performance_tracker = PerformanceTracker(
            initial_value=self.executor.get_portfolio_value()
        )

        # Register all tools (analysis + trading)
        self._register_all_tools()

    def _register_all_tools(self) -> None:
        """Register both analysis and trading tools"""

        # Analysis tools (from existing agent)
        self.tools.register(Tool(
            name="get_stock_price",
            description="Get current stock price and trading data from Yahoo Finance",
            parameters={"ticker": "string (stock symbol, e.g., 'AAPL')"},
            function=get_stock_price
        ))

        self.tools.register(Tool(
            name="get_company_financials",
            description="Get company financial statements (income, balance sheet, or cash flow)",
            parameters={
                "ticker": "string (stock symbol)",
                "statement": "string ('income', 'balance', or 'cashflow')"
            },
            function=get_company_financials
        ))

        self.tools.register(Tool(
            name="get_analyst_ratings",
            description="Get analyst recommendations and price targets",
            parameters={"ticker": "string (stock symbol)"},
            function=get_analyst_ratings
        ))

        self.tools.register(Tool(
            name="calculate_valuation",
            description="Calculate valuation metrics (P/E, PEG, Price/Book, etc.)",
            parameters={"ticker": "string (stock symbol)"},
            function=calculate_valuation
        ))

        self.tools.register(Tool(
            name="risk_assessment",
            description="Assess investment risk using beta, volatility, and financial ratios",
            parameters={"ticker": "string (stock symbol)"},
            function=risk_assessment
        ))

        # Trading tools (new)
        self.tools.register(Tool(
            name="get_portfolio",
            description="Get current portfolio summary including cash, positions, and total value",
            parameters={},
            function=self._get_portfolio
        ))

        self.tools.register(Tool(
            name="check_position",
            description="Check current position in a specific stock",
            parameters={"ticker": "string (stock symbol)"},
            function=self._check_position
        ))

        self.tools.register(Tool(
            name="calculate_position_size",
            description="Calculate recommended position size for a stock based on risk management rules",
            parameters={
                "ticker": "string (stock symbol)",
                "current_price": "float (current stock price)"
            },
            function=self._calculate_position_size
        ))

        self.tools.register(Tool(
            name="execute_trade",
            description="Execute a buy or sell order. Always calculate position size first and validate with risk manager.",
            parameters={
                "ticker": "string (stock symbol)",
                "action": "string ('BUY' or 'SELL')",
                "quantity": "integer (number of shares)",
                "order_type": "string (optional: 'market' or 'limit', default 'market')",
                "limit_price": "float (optional: limit price for limit orders)"
            },
            function=self._execute_trade
        ))

        self.tools.register(Tool(
            name="get_performance",
            description="Get portfolio performance metrics (returns, Sharpe ratio, win rate, etc.)",
            parameters={},
            function=self._get_performance
        ))

    # Trading tool implementations

    def _get_portfolio(self) -> Dict:
        """Get current portfolio summary"""
        summary = self.executor.get_portfolio_summary()

        # Add risk manager status
        summary["risk_settings"] = self.risk_manager.get_risk_summary()

        return summary

    def _check_position(self, ticker: str) -> Dict:
        """Check current position in a stock"""
        position = self.executor.get_position(ticker)

        if position:
            # Check if stop-loss should trigger
            should_sell, stop_loss_info = self.risk_manager.check_stop_loss(
                ticker=ticker,
                entry_price=position["avg_cost"],
                current_price=position["current_price"]
            )

            position["stop_loss_info"] = stop_loss_info

        return position or {"error": f"No position in {ticker}"}

    def _calculate_position_size(self, ticker: str, current_price: float) -> Dict:
        """Calculate recommended position size"""
        portfolio_value = self.executor.get_portfolio_value()

        return self.risk_manager.calculate_position_size(
            portfolio_value=portfolio_value,
            ticker=ticker,
            current_price=current_price
        )

    def _execute_trade(self, ticker: str, action: str, quantity: int,
                      order_type: str = "market",
                      limit_price: Optional[float] = None) -> Dict:
        """Execute a buy or sell order with risk management"""

        action = action.upper()

        # Get current portfolio state
        portfolio_value = self.executor.get_portfolio_value()
        current_positions = self.executor.portfolio.get_all_positions()
        cash = self.executor.get_buying_power()

        # Get current price
        try:
            current_price = self.executor.get_current_price(ticker)
        except Exception as e:
            return {
                "success": False,
                "error": f"Could not fetch price for {ticker}: {str(e)}"
            }

        # Risk management validation
        valid, reason = self.risk_manager.validate_order(
            action=action,
            ticker=ticker,
            quantity=quantity,
            price=limit_price if limit_price else current_price,
            portfolio_value=portfolio_value,
            current_positions=current_positions,
            cash=cash
        )

        if not valid:
            return {
                "success": False,
                "rejected": True,
                "reason": reason,
                "risk_check": "failed"
            }

        # Check circuit breaker
        circuit_breaker_triggered, cb_info = self.risk_manager.check_circuit_breaker(portfolio_value)

        if circuit_breaker_triggered:
            return {
                "success": False,
                "rejected": True,
                "reason": "Circuit breaker triggered - daily loss limit exceeded",
                "circuit_breaker_info": cb_info
            }

        # Execute order
        result = self.executor.execute_order(
            ticker=ticker,
            action=action,
            quantity=quantity,
            order_type=order_type,
            limit_price=limit_price
        )

        # Record performance data
        if result.get("success"):
            new_portfolio_value = self.executor.get_portfolio_value()
            self.performance_tracker.record_value(new_portfolio_value)

            # If selling, record closed trade
            if action == "SELL" and ticker in current_positions:
                pos = current_positions[ticker]
                self.performance_tracker.record_closed_trade(
                    ticker=ticker,
                    entry_price=pos.avg_cost,
                    exit_price=result.get("execution_price", current_price),
                    quantity=quantity,
                    hold_days=0  # Would need to track entry dates for accurate calculation
                )

        return result

    def _get_performance(self) -> Dict:
        """Get portfolio performance metrics"""
        return self.performance_tracker.get_performance_summary()

    def analyze_and_recommend(self, ticker: str, verbose: bool = True) -> Dict:
        """
        Analyze a stock and provide investment recommendation

        Args:
            ticker: Stock symbol to analyze
            verbose: Whether to print ReAct iterations

        Returns:
            Dict with analysis and recommendation
        """
        # Build query with investor profile context if available
        if self.investor_profile:
            profile_context = self.investor_profile.get_analysis_context()
            query = f"""
Analyze {ticker} and provide a specific investment recommendation.

{profile_context}

Include:
1. Current price and valuation analysis
2. Financial health and growth metrics
3. Risk assessment
4. Analyst consensus
5. Recommended action (BUY/SELL/HOLD) with specific position size
6. Entry price and stop-loss level

Your final answer must include a clear recommendation.
"""
        else:
            query = f"""
Analyze {ticker} and provide a specific investment recommendation.

Include:
1. Current price and valuation analysis
2. Financial health and growth metrics
3. Risk assessment
4. Analyst consensus
5. Recommended action (BUY/SELL/HOLD) with specific position size
6. Entry price and stop-loss level

Your final answer must include a clear recommendation.
"""

        return self.run(query, verbose=verbose)

    def execute_recommendation(self, ticker: str, verbose: bool = True) -> Dict:
        """
        Analyze a stock and automatically execute the recommended trade

        Args:
            ticker: Stock symbol to analyze
            verbose: Whether to print ReAct iterations

        Returns:
            Dict with analysis, recommendation, and execution result
        """
        # Build query with execution capability
        if self.investor_profile:
            profile_context = self.investor_profile.get_analysis_context()
            query = f"""
Analyze {ticker} and execute a trade if appropriate.

{profile_context}

Process:
1. Get current price and portfolio status
2. Analyze fundamentals, valuation, and risk
3. Calculate appropriate position size
4. If analysis is positive AND risk checks pass, execute BUY order
5. If we hold a position and analysis is negative, consider SELL
6. Provide detailed explanation of your decision

Use the trading tools to check portfolio, calculate position size, and execute trades.
Your final answer must include what action was taken and why.
"""
        else:
            query = f"""
Analyze {ticker} and execute a trade if appropriate.

Process:
1. Get current portfolio status
2. Analyze fundamentals, valuation, and risk
3. Calculate appropriate position size
4. If analysis is positive AND risk checks pass, execute BUY order
5. If we hold a position and analysis is negative, consider SELL
6. Provide detailed explanation of your decision

Use the trading tools to check portfolio, calculate position size, and execute trades.
Your final answer must include what action was taken and why.
"""

        return self.run(query, verbose=verbose)


if __name__ == "__main__":
    # Quick test
    print("Testing TradingAgent (Paper Mode)...")

    # Check for API key
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nError: ANTHROPIC_API_KEY not found in environment")
        print("Set it with: export ANTHROPIC_API_KEY=your-api-key")
        exit(1)

    # Create trading agent
    print("\nInitializing trading agent...")
    agent = TradingAgent(
        mode="paper",
        api_key=api_key,
        initial_cash=100000,
        max_iterations=15
    )

    print("\n1. Portfolio Status:")
    portfolio = agent._get_portfolio()
    print(f"Cash: ${portfolio['cash']:,.2f}")
    print(f"Total Value: ${portfolio['total_value']:,.2f}")
    print(f"Positions: {portfolio['num_positions']}")

    print("\n2. Calculating position size for AAPL...")
    try:
        current_price = agent.executor.get_current_price("AAPL")
        position_rec = agent._calculate_position_size("AAPL", current_price)
        print(f"Current price: ${current_price:.2f}")
        print(f"Recommended shares: {position_rec['recommended_shares']}")
        print(f"Position value: ${position_rec['position_value']:,.2f}")
        print(f"Position %: {position_rec['position_pct']:.1f}%")
    except Exception as e:
        print(f"Error: {e}")

    print("\n3. Testing buy order validation (without executing)...")
    print("(Full AI-driven analysis requires running analyze_and_recommend)")

    print("\nTradingAgent ready! Use analyze_and_recommend() or execute_recommendation() for AI-driven trading.")
