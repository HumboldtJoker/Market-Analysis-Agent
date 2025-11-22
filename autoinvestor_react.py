#!/usr/bin/env python3
"""
AutoInvestor ReAct Agent
========================
Investment research agent using ReAct (Reasoning + Acting) methodology with Claude.

Author: Lyra + Thomas Edrington
Version: 1.0.0
"""

import json
import re
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import anthropic
import yfinance as yf
import pandas as pd


class Tool:
    """Base class for tools the ReAct agent can use"""

    def __init__(self, name: str, description: str, parameters: Dict, function: Callable):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.function = function

    def execute(self, **kwargs) -> Dict[str, Any]:
        """Execute the tool with given parameters"""
        try:
            result = self.function(**kwargs)
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def to_dict(self) -> Dict:
        """Convert tool to dictionary for prompt"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters
        }


class ToolRegistry:
    """Registry for managing available tools"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a new tool"""
        self.tools[tool.name] = tool
        print(f"Registered tool: {tool.name}")

    def get(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self.tools.get(name)

    def list_tools(self) -> List[Dict]:
        """List all available tools"""
        return [tool.to_dict() for tool in self.tools.values()]

    def get_descriptions(self) -> str:
        """Get formatted tool descriptions for prompt"""
        descriptions = []
        for tool in self.tools.values():
            params = json.dumps(tool.parameters, indent=2)
            descriptions.append(f"""
{tool.name}:
  Description: {tool.description}
  Parameters: {params}
""")
        return "\n".join(descriptions)


class ReActAgent:
    """
    ReAct (Reasoning + Acting) Agent for investment research

    Uses Claude to reason through investment questions by:
    1. Breaking down questions into steps (Reasoning)
    2. Using tools to gather data (Acting)
    3. Synthesizing information into recommendations
    """

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-5-20250929", max_iterations: int = 10):
        """
        Initialize ReAct agent

        Args:
            api_key: Anthropic API key
            model: Claude model to use
            max_iterations: Maximum reasoning loops before timeout
        """
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_iterations = max_iterations
        self.tools = ToolRegistry()
        self.history = []

    def _build_system_prompt(self) -> str:
        """Build system prompt with tool descriptions"""
        return f"""You are an expert investment research analyst using the ReAct (Reasoning + Acting) methodology.

Your goal is to provide thorough, data-driven investment recommendations by:
1. Breaking down complex research questions into steps
2. Using available tools to gather relevant data
3. Reasoning through the information systematically
4. Providing clear, actionable recommendations

IMPORTANT RULES:
- Always show your reasoning before taking actions
- Use tools to get real data, don't make up numbers
- Consider multiple perspectives (fundamentals, technicals, sentiment, risk)
- Be honest about uncertainties and limitations
- Provide specific recommendations with clear rationale

AVAILABLE TOOLS:
{self.tools.get_descriptions()}

OUTPUT FORMAT:
For each step, use this exact format:

Thought: [Your reasoning about what to do next]
Action: [tool_name]
Action Input: [tool parameters as JSON]

After receiving observations, continue with:

Thought: [Your analysis of the observation]
Action: [next tool_name or FINAL_ANSWER]
Action Input: [parameters or your final recommendation]

When you have enough information, use:
Action: FINAL_ANSWER
Action Input: [Your complete investment recommendation]

EXAMPLE:
Thought: I need to analyze Apple's recent performance. Let me start by getting the current stock price.
Action: get_stock_price
Action Input: {{"ticker": "AAPL"}}

Begin your research now.
"""

    def _parse_response(self, response: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Parse Claude's response to extract thought, action, and action input

        Returns:
            (thought, action, action_input)
        """
        thought_match = re.search(r'Thought:\s*(.+?)(?=\nAction:|$)', response, re.DOTALL | re.IGNORECASE)
        action_match = re.search(r'Action:\s*(\w+)', response, re.IGNORECASE)
        action_input_match = re.search(r'Action Input:\s*(.+?)(?=\n\n|$)', response, re.DOTALL | re.IGNORECASE)

        thought = thought_match.group(1).strip() if thought_match else None
        action = action_match.group(1).strip() if action_match else None
        action_input = action_input_match.group(1).strip() if action_input_match else None

        return thought, action, action_input

    def _execute_tool(self, tool_name: str, tool_input: str) -> str:
        """Execute a tool and return observation"""
        tool = self.tools.get(tool_name)

        if not tool:
            return f"ERROR: Tool '{tool_name}' not found. Available tools: {', '.join(self.tools.tools.keys())}"

        try:
            # Parse JSON input
            params = json.loads(tool_input)

            # Execute tool
            result = tool.execute(**params)

            if result["success"]:
                return json.dumps(result["data"], indent=2)
            else:
                return f"ERROR: {result['error']}"

        except json.JSONDecodeError as e:
            return f"ERROR: Invalid JSON in Action Input: {e}"
        except Exception as e:
            return f"ERROR: Tool execution failed: {e}"

    def _format_history_for_prompt(self) -> str:
        """Format conversation history for prompt"""
        formatted = []

        for i, item in enumerate(self.history):
            if item["type"] == "thought":
                formatted.append(f"\nIteration {item['iteration'] + 1}:")
                formatted.append(f"Thought: {item['content']}")
            elif item["type"] == "action":
                formatted.append(f"Action: {item['tool']}")
                formatted.append(f"Action Input: {item['input']}")
            elif item["type"] == "observation":
                formatted.append(f"Observation: {item['content']}")

        return "\n".join(formatted)

    def run(self, user_query: str, verbose: bool = True) -> Dict[str, Any]:
        """
        Run ReAct loop to answer user query

        Args:
            user_query: Investment question to research
            verbose: Print progress to console

        Returns:
            Dictionary with final answer and metadata
        """
        self.history = []

        if verbose:
            print(f"\n{'='*80}")
            print(f"INVESTMENT RESEARCH QUERY: {user_query}")
            print(f"{'='*80}\n")

        for iteration in range(self.max_iterations):
            # Build prompt with system instructions and history
            system_prompt = self._build_system_prompt()

            if iteration == 0:
                user_prompt = f"USER QUERY: {user_query}\n\nBegin your research:"
            else:
                user_prompt = self._format_history_for_prompt() + "\n\nContinue your research:"

            # Get response from Claude
            if verbose:
                print(f"\n--- Iteration {iteration + 1} ---")

            message = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            response = message.content[0].text

            # Parse response
            thought, action, action_input = self._parse_response(response)

            if verbose and thought:
                print(f"\nThought: {thought}")

            # Record thought
            if thought:
                self.history.append({
                    "type": "thought",
                    "content": thought,
                    "iteration": iteration
                })

            # Check if done
            if action and action.upper() == "FINAL_ANSWER":
                if verbose:
                    print(f"\n{'='*80}")
                    print("FINAL ANSWER:")
                    print(f"{'='*80}")
                    print(f"\n{action_input}\n")

                return {
                    "success": True,
                    "answer": action_input,
                    "iterations": iteration + 1,
                    "history": self.history
                }

            # Execute action
            if action and action_input:
                if verbose:
                    print(f"Action: {action}")
                    print(f"Action Input: {action_input}")

                # Record action
                self.history.append({
                    "type": "action",
                    "tool": action,
                    "input": action_input,
                    "iteration": iteration
                })

                # Execute tool
                observation = self._execute_tool(action, action_input)

                if verbose:
                    print(f"\nObservation: {observation[:500]}..." if len(observation) > 500 else f"\nObservation: {observation}")

                # Record observation
                self.history.append({
                    "type": "observation",
                    "content": observation,
                    "iteration": iteration
                })
            else:
                # No valid action found
                if verbose:
                    print(f"\nWARNING: Could not parse action from response:")
                    print(response)
                break

        # Max iterations reached
        return {
            "success": False,
            "error": f"Max iterations ({self.max_iterations}) reached without final answer",
            "iterations": self.max_iterations,
            "history": self.history
        }


# ============================================================================
# REAL YAHOO FINANCE TOOLS
# ============================================================================

def get_stock_price(ticker: str) -> Dict:
    """Get current stock price and trading data from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get current price
        current_price = info.get('currentPrice') or info.get('regularMarketPrice')
        if not current_price:
            raise ValueError(f"Could not fetch price for {ticker}")

        # Get previous close to calculate change
        prev_close = info.get('previousClose', current_price)
        change = current_price - prev_close
        change_percent = (change / prev_close * 100) if prev_close else 0

        return {
            "ticker": ticker,
            "price": round(current_price, 2),
            "change": round(change, 2),
            "change_percent": round(change_percent, 2),
            "volume": info.get('volume', 0),
            "market_cap": info.get('marketCap', 0),
            "day_high": info.get('dayHigh', 0),
            "day_low": info.get('dayLow', 0),
            "fifty_two_week_high": info.get('fiftyTwoWeekHigh', 0),
            "fifty_two_week_low": info.get('fiftyTwoWeekLow', 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise ValueError(f"Error fetching stock price for {ticker}: {str(e)}")


def get_company_financials(ticker: str, statement: str = "income") -> Dict:
    """Get company financial statements from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get quarterly revenue data
        quarterly_financials = stock.quarterly_financials

        financials = {
            "ticker": ticker,
            "statement": statement,
            "revenue": info.get('totalRevenue', 0),
            "revenue_growth_yoy": info.get('revenueGrowth', 0) * 100 if info.get('revenueGrowth') else 0,
            "net_income": info.get('netIncomeToCommon', 0),
            "earnings_growth_yoy": info.get('earningsGrowth', 0) * 100 if info.get('earningsGrowth') else 0,
            "eps": info.get('trailingEps', 0),
            "gross_margin": info.get('grossMargins', 0) * 100 if info.get('grossMargins') else 0,
            "operating_margin": info.get('operatingMargins', 0) * 100 if info.get('operatingMargins') else 0,
            "profit_margin": info.get('profitMargins', 0) * 100 if info.get('profitMargins') else 0,
            "ebitda": info.get('ebitda', 0),
            "free_cash_flow": info.get('freeCashflow', 0),
            "period": "TTM (Trailing Twelve Months)"
        }

        return financials
    except Exception as e:
        raise ValueError(f"Error fetching financials for {ticker}: {str(e)}")


def get_analyst_ratings(ticker: str) -> Dict:
    """Get analyst consensus ratings from Yahoo Finance"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get recommendations
        recommendations = stock.recommendations

        # Parse recommendation consensus
        recommendation = info.get('recommendationKey', 'none')
        num_analysts = info.get('numberOfAnalystOpinions', 0)

        # Get price targets
        target_high = info.get('targetHighPrice', 0)
        target_low = info.get('targetLowPrice', 0)
        target_mean = info.get('targetMeanPrice', 0)
        target_median = info.get('targetMedianPrice', 0)

        return {
            "ticker": ticker,
            "recommendation": recommendation,
            "num_analysts": num_analysts,
            "price_target": {
                "low": target_low,
                "mean": target_mean,
                "median": target_median,
                "high": target_high
            },
            "current_price": info.get('currentPrice', 0)
        }
    except Exception as e:
        raise ValueError(f"Error fetching analyst ratings for {ticker}: {str(e)}")


def calculate_valuation(ticker: str) -> Dict:
    """Calculate valuation metrics from Yahoo Finance data"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        return {
            "ticker": ticker,
            "pe_ratio": info.get('trailingPE', 0),
            "forward_pe": info.get('forwardPE', 0),
            "peg_ratio": info.get('pegRatio', 0),
            "price_to_book": info.get('priceToBook', 0),
            "price_to_sales": info.get('priceToSalesTrailing12Months', 0),
            "enterprise_value": info.get('enterpriseValue', 0),
            "ev_to_revenue": info.get('enterpriseToRevenue', 0),
            "ev_to_ebitda": info.get('enterpriseToEbitda', 0),
            "dividend_yield": info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0,
            "dividend_rate": info.get('dividendRate', 0)
        }
    except Exception as e:
        raise ValueError(f"Error calculating valuation for {ticker}: {str(e)}")


def risk_assessment(ticker: str) -> Dict:
    """Assess investment risk using Yahoo Finance data"""
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        # Get historical data for volatility calculation
        hist = stock.history(period="1mo")

        # Calculate 30-day volatility if we have data
        volatility_30d = 0
        if not hist.empty and 'Close' in hist.columns:
            returns = hist['Close'].pct_change().dropna()
            if len(returns) > 0:
                volatility_30d = returns.std() * (252 ** 0.5)  # Annualized

        # Get beta
        beta = info.get('beta', 1.0)

        # Calculate a simple risk score based on beta and volatility
        # Scale: 1-10 (higher = more risky)
        risk_score = min(10, max(1, (beta * 3) + (volatility_30d * 10)))

        # Identify risk factors based on metrics
        risk_factors = []

        if beta > 1.5:
            risk_factors.append(f"High beta ({beta:.2f}) - more volatile than market")

        if volatility_30d > 0.4:
            risk_factors.append(f"High volatility ({volatility_30d:.1%} annualized)")

        pe_ratio = info.get('trailingPE', 0)
        if pe_ratio > 40:
            risk_factors.append(f"High P/E ratio ({pe_ratio:.1f}) - valuation risk")

        debt_to_equity = info.get('debtToEquity', 0)
        if debt_to_equity > 100:
            risk_factors.append(f"High debt-to-equity ({debt_to_equity:.1f}%)")

        current_ratio = info.get('currentRatio', 0)
        if current_ratio < 1.0 and current_ratio > 0:
            risk_factors.append(f"Low current ratio ({current_ratio:.2f}) - liquidity concerns")

        return {
            "ticker": ticker,
            "beta": round(beta, 2),
            "volatility_30d": round(volatility_30d, 3),
            "risk_score": round(risk_score, 1),
            "debt_to_equity": debt_to_equity,
            "current_ratio": current_ratio,
            "risk_factors": risk_factors if risk_factors else ["Moderate risk profile based on available metrics"]
        }
    except Exception as e:
        raise ValueError(f"Error assessing risk for {ticker}: {str(e)}")


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    import os

    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY environment variable not set")
        exit(1)

    # Initialize agent
    agent = ReActAgent(api_key=api_key, max_iterations=12)

    # Register Yahoo Finance tools
    agent.tools.register(Tool(
        name="get_stock_price",
        description="Get current stock price and trading data from Yahoo Finance",
        parameters={
            "ticker": "string (stock symbol, e.g., 'AAPL')"
        },
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
        parameters={
            "ticker": "string (stock symbol)"
        },
        function=get_analyst_ratings
    ))

    agent.tools.register(Tool(
        name="calculate_valuation",
        description="Calculate valuation metrics from Yahoo Finance (P/E, PEG, P/B, EV/Revenue, etc.)",
        parameters={
            "ticker": "string (stock symbol)"
        },
        function=calculate_valuation
    ))

    agent.tools.register(Tool(
        name="risk_assessment",
        description="Assess investment risk factors using Yahoo Finance data (beta, volatility, debt ratios)",
        parameters={
            "ticker": "string (stock symbol)"
        },
        function=risk_assessment
    ))

    # Run example query
    result = agent.run(
        "Should I invest in NVIDIA right now? Give me a clear recommendation with supporting analysis.",
        verbose=True
    )

    # Print summary
    print(f"\n{'='*80}")
    print("EXECUTION SUMMARY")
    print(f"{'='*80}")
    print(f"Success: {result['success']}")
    print(f"Iterations: {result['iterations']}")
    if not result['success']:
        print(f"Error: {result.get('error', 'Unknown error')}")
