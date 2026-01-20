#!/usr/bin/env python3
"""
AutoInvestor MCP Server

Exposes AutoInvestor investment research and trading tools as MCP tools
for direct access from Claude Code.

Author: Lyra & Thomas
Version: 1.0.0
"""

import os
import sys
import json
from typing import Any, Dict, Optional

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

# MCP imports
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# AutoInvestor imports
try:
    # TODO: Migrate MCP tools to use unified API (autoinvestor_api)
    # Currently using legacy imports for backward compatibility
    from autoinvestor_react import (
        get_stock_price,
        get_company_financials,
        get_analyst_ratings,
        calculate_valuation,
        risk_assessment
    )
    from technical_indicators import analyze_technicals
    from news_sentiment import analyze_news_sentiment
    from congressional_trades import analyze_congressional_trades
    from congressional_trades_aggregate import get_aggregate_analysis
    from portfolio_correlation import analyze_portfolio_correlation
    from sector_allocation import analyze_sector_allocation
    from order_executor import OrderExecutor
    from risk_manager import RiskManager
    from macro_agent import MacroAgent
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)

# Initialize MCP server
app = Server("autoinvestor")


# Helper function to format results
def format_result(result: Any) -> str:
    """Format tool results as JSON string"""
    if isinstance(result, dict):
        return json.dumps(result, indent=2, default=str)
    return str(result)


# ============================================================================
# PHASE 1: Core Analysis Tools
# ============================================================================

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List all available AutoInvestor tools"""

    tools = [
        # Phase 1: Core Analysis
        Tool(
            name="get_stock_price",
            description="Get current stock price, volume, and 52-week range from Yahoo Finance",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol (e.g., 'AAPL', 'NVDA')"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_company_financials",
            description="Get company financial metrics (revenue, earnings, margins, cash flow)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_analyst_ratings",
            description="Get analyst consensus ratings and price targets",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="calculate_valuation",
            description="Calculate valuation metrics (P/E, PEG, P/B, EV/EBITDA)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="risk_assessment",
            description="Assess investment risk (beta, volatility, debt ratios)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),

        # Phase 2: Advanced Analysis
        Tool(
            name="analyze_technicals",
            description="Technical analysis with SMA (20/50/200), RSI, MACD, Bollinger Bands",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "period": {
                        "type": "integer",
                        "description": "Days of price history to analyze (default: 90)",
                        "default": 90
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="analyze_news_sentiment",
            description="Analyze recent news sentiment for a stock",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="analyze_congressional_trades",
            description="Analyze individual congressional trades for a stock (STOCK Act disclosures)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "api_key": {
                        "type": "string",
                        "description": "RapidAPI key (optional, will use RAPIDAPI_KEY env var if not provided)"
                    }
                },
                "required": ["ticker"]
            }
        ),
        Tool(
            name="get_aggregate_congressional_analysis",
            description="Get aggregate congressional trading trends across all Congress (sector patterns, partisan divergence)",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "RapidAPI key (optional, will use RAPIDAPI_KEY env var if not provided)"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="analyze_portfolio_correlation",
            description="Analyze portfolio diversification and correlation matrix",
            inputSchema={
                "type": "object",
                "properties": {
                    "tickers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of stock ticker symbols in portfolio"
                    }
                },
                "required": ["tickers"]
            }
        ),
        Tool(
            name="analyze_sector_allocation",
            description="Analyze sector exposure and concentration risk vs benchmarks",
            inputSchema={
                "type": "object",
                "properties": {
                    "portfolio": {
                        "type": "object",
                        "description": "Portfolio holdings as {ticker: shares} dict",
                        "additionalProperties": {"type": "integer"}
                    }
                },
                "required": ["portfolio"]
            }
        ),
        Tool(
            name="get_market_regime",
            description="Get current market regime from macro indicators (yield curve, VIX, credit spreads)",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_key": {
                        "type": "string",
                        "description": "FRED API key (optional, will use FRED_API_KEY env var if not provided)"
                    }
                },
                "required": []
            }
        ),

        # Phase 3: Execution Tools
        Tool(
            name="execute_order",
            description="Execute a buy or sell order (paper or live trading via Alpaca)",
            inputSchema={
                "type": "object",
                "properties": {
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "action": {
                        "type": "string",
                        "enum": ["BUY", "SELL"],
                        "description": "Buy or sell action"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Number of shares",
                        "minimum": 1
                    },
                    "order_type": {
                        "type": "string",
                        "enum": ["market", "limit"],
                        "description": "Order type (default: market)",
                        "default": "market"
                    },
                    "limit_price": {
                        "type": "number",
                        "description": "Limit price (required for limit orders)"
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["local", "alpaca", "paper", "live"],
                        "description": "Trading mode: 'local' (simulated) or 'alpaca' (API). Old names 'paper'/'live' still work.",
                        "default": "local"
                    }
                },
                "required": ["ticker", "action", "quantity"]
            }
        ),
        Tool(
            name="calculate_position_size",
            description="Calculate recommended position size with risk management and macro overlay",
            inputSchema={
                "type": "object",
                "properties": {
                    "portfolio_value": {
                        "type": "number",
                        "description": "Total portfolio value in dollars"
                    },
                    "ticker": {
                        "type": "string",
                        "description": "Stock ticker symbol"
                    },
                    "current_price": {
                        "type": "number",
                        "description": "Current stock price"
                    },
                    "enable_macro_overlay": {
                        "type": "boolean",
                        "description": "Adjust size based on macro regime (default: true)",
                        "default": True
                    }
                },
                "required": ["portfolio_value", "ticker", "current_price"]
            }
        ),
        Tool(
            name="get_portfolio_summary",
            description="Get current portfolio summary with positions and performance",
            inputSchema={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["local", "alpaca", "paper", "live"],
                        "description": "Trading mode: 'local' (simulated) or 'alpaca' (API). Old names 'paper'/'live' still work.",
                        "default": "alpaca"
                    }
                },
                "required": []
            }
        ),
        Tool(
            name="market_status",
            description="Get current market status including date, day of week, whether market is open, and upcoming trading days. Use this before making any date or calendar-related statements.",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]

    return tools


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute AutoInvestor tool"""

    if not IMPORTS_AVAILABLE:
        return [TextContent(
            type="text",
            text=f"ERROR: AutoInvestor modules not available: {IMPORT_ERROR}"
        )]

    try:
        # Phase 1 Tools
        if name == "get_stock_price":
            result = get_stock_price(arguments["ticker"])
            return [TextContent(type="text", text=format_result(result))]

        elif name == "get_company_financials":
            result = get_company_financials(arguments["ticker"])
            return [TextContent(type="text", text=format_result(result))]

        elif name == "get_analyst_ratings":
            result = get_analyst_ratings(arguments["ticker"])
            return [TextContent(type="text", text=format_result(result))]

        elif name == "calculate_valuation":
            result = calculate_valuation(arguments["ticker"])
            return [TextContent(type="text", text=format_result(result))]

        elif name == "risk_assessment":
            result = risk_assessment(arguments["ticker"])
            return [TextContent(type="text", text=format_result(result))]

        # Phase 2 Tools
        elif name == "analyze_technicals":
            period = arguments.get("period", 90)
            result = analyze_technicals(arguments["ticker"], period=period)
            return [TextContent(type="text", text=format_result(result))]

        elif name == "analyze_news_sentiment":
            result = analyze_news_sentiment(arguments["ticker"])
            return [TextContent(type="text", text=format_result(result))]

        elif name == "analyze_congressional_trades":
            api_key = arguments.get("api_key") or os.environ.get("RAPIDAPI_KEY")
            if not api_key:
                return [TextContent(
                    type="text",
                    text="ERROR: RAPIDAPI_KEY required. Set environment variable or pass as parameter."
                )]
            result = analyze_congressional_trades(arguments["ticker"], api_key=api_key)
            return [TextContent(type="text", text=format_result(result))]

        elif name == "get_aggregate_congressional_analysis":
            api_key = arguments.get("api_key") or os.environ.get("RAPIDAPI_KEY")
            if not api_key:
                return [TextContent(
                    type="text",
                    text="ERROR: RAPIDAPI_KEY required. Set environment variable or pass as parameter."
                )]
            result = get_aggregate_analysis(api_key=api_key)
            return [TextContent(type="text", text=format_result(result))]

        elif name == "analyze_portfolio_correlation":
            result = analyze_portfolio_correlation(arguments["tickers"])
            return [TextContent(type="text", text=format_result(result))]

        elif name == "analyze_sector_allocation":
            result = analyze_sector_allocation(arguments["portfolio"])
            return [TextContent(type="text", text=format_result(result))]

        elif name == "get_market_regime":
            api_key = arguments.get("api_key") or os.environ.get("FRED_API_KEY")
            agent = MacroAgent(api_key=api_key) if api_key else MacroAgent()
            result = agent.get_market_regime()
            return [TextContent(type="text", text=format_result(result))]

        # Phase 3 Execution Tools
        elif name == "execute_order":
            mode = arguments.get("mode", "local")
            executor = OrderExecutor(mode=mode)
            result = executor.execute_order(
                ticker=arguments["ticker"],
                action=arguments["action"],
                quantity=arguments["quantity"],
                order_type=arguments.get("order_type", "market"),
                limit_price=arguments.get("limit_price")
            )
            return [TextContent(type="text", text=format_result(result))]

        elif name == "calculate_position_size":
            enable_macro = arguments.get("enable_macro_overlay", True)
            rm = RiskManager(enable_auto_execute=False, enable_macro_overlay=enable_macro)
            result = rm.calculate_position_size(
                portfolio_value=arguments["portfolio_value"],
                ticker=arguments["ticker"],
                current_price=arguments["current_price"]
            )
            return [TextContent(type="text", text=format_result(result))]

        elif name == "get_portfolio_summary":
            mode = arguments.get("mode", "alpaca")
            executor = OrderExecutor(mode=mode)
            result = executor.get_portfolio_summary()
            return [TextContent(type="text", text=format_result(result))]

        elif name == "market_status":
            from market_status import get_market_status
            result = get_market_status()
            return [TextContent(type="text", text=format_result(result))]

        else:
            return [TextContent(
                type="text",
                text=f"ERROR: Unknown tool: {name}"
            )]

    except Exception as e:
        return [TextContent(
            type="text",
            text=f"ERROR executing {name}: {str(e)}"
        )]


async def main():
    """Run the MCP server"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
