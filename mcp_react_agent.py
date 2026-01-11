#!/usr/bin/env python3
"""
MCP-Enabled ReAct Agent
Uses Claude Code/Desktop via MCP instead of direct API calls
"""

import json
import re
from typing import Dict, List, Optional, Any
from datetime import datetime
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from autoinvestor_react import Tool, ToolRegistry

class MCPReActAgent:
    """
    MCP-enabled ReAct Agent that delegates AI reasoning to Claude Code/Desktop
    while using local tools for data gathering
    """

    def __init__(self, max_iterations: int = 10):
        """
        Initialize MCP ReAct agent

        Args:
            max_iterations: Maximum reasoning loops before timeout
        """
        self.max_iterations = max_iterations
        self.tools = ToolRegistry()
        self.history = []

    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def get_conversation_context(self) -> str:
        """Get formatted conversation context for MCP"""
        if not self.history:
            return ""

        context = "CONVERSATION HISTORY:\n"
        for msg in self.history[-5:]:  # Last 5 messages for context
            context += f"{msg['role'].upper()}: {msg['content']}\n\n"

        return context

    def _build_analysis_prompt(self, query: str) -> str:
        """Build analysis prompt for Claude via MCP"""
        context = self.get_conversation_context()

        return f"""I need you to act as an expert investment research analyst and help me analyze this investment question using the ReAct (Reasoning + Acting) methodology.

{context}

CURRENT QUERY: {query}

AVAILABLE DATA GATHERING TOOLS:
{self.tools.get_descriptions()}

Please provide your investment analysis following this structure:

1. **REASONING PHASE**: Break down what information you need to answer this question

2. **DATA REQUEST**: Tell me which tools I should use to gather the required data (I'll execute them and provide you the results)

3. **ANALYSIS PHASE**: Once I provide the data, analyze it comprehensively considering:
   - Fundamentals (financials, valuation, growth)
   - Technical indicators (if applicable)
   - Market sentiment and news
   - Risk factors
   - Congressional trading patterns (if relevant)
   - Macro economic conditions

4. **RECOMMENDATION**: Provide a clear, actionable investment recommendation with:
   - Buy/Hold/Sell decision
   - Position sizing considerations
   - Risk management suggestions
   - Timeline and exit strategy

Please start with your reasoning about what information you need, then tell me which tools to run."""

    def _parse_tool_requests(self, response: str) -> List[Dict]:
        """Parse tool requests from Claude's response"""
        tool_requests = []

        # Look for patterns like "run get_stock_price with ticker AAPL"
        # or "execute technical_analysis for MSFT"
        patterns = [
            r'(?:run|execute|use)\s+(\w+)(?:\s+(?:with|for|on))?\s+(?:ticker\s+)?(\w+)',
            r'(\w+)\s*\(\s*["\']?(\w+)["\']?\s*\)',
            r'Tool:\s*(\w+)\s*\n.*?Ticker:\s*(\w+)',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, response, re.IGNORECASE)
            for match in matches:
                tool_name = match.group(1)
                param = match.group(2) if len(match.groups()) > 1 else ""

                if tool_name in self.tools.tools:
                    tool_requests.append({
                        "tool": tool_name,
                        "params": {"ticker": param} if param else {}
                    })

        return tool_requests

    def execute_tools(self, tool_requests: List[Dict]) -> Dict[str, Any]:
        """Execute requested tools and return results"""
        results = {}

        for request in tool_requests:
            tool_name = request["tool"]
            params = request.get("params", {})

            tool = self.tools.get(tool_name)
            if tool:
                print(f"Executing {tool_name} with params: {params}")
                result = tool.execute(**params)
                results[tool_name] = result
            else:
                results[tool_name] = {"success": False, "error": f"Tool {tool_name} not found"}

        return results

    def format_tool_results(self, results: Dict[str, Any]) -> str:
        """Format tool execution results for Claude"""
        formatted = "TOOL EXECUTION RESULTS:\n\n"

        for tool_name, result in results.items():
            formatted += f"=== {tool_name.upper()} ===\n"
            if result.get("success"):
                formatted += json.dumps(result["data"], indent=2)
            else:
                formatted += f"ERROR: {result.get('error', 'Unknown error')}"
            formatted += "\n\n"

        return formatted

    def run_mcp_analysis(self, query: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Run analysis using MCP integration
        This method coordinates between local tools and Claude via MCP
        """
        self.add_message("user", query)

        # Build initial prompt
        analysis_prompt = self._build_analysis_prompt(query)

        print("=== MCP REACT ANALYSIS ===")
        print(f"Query: {query}")
        print("\n=== STEP 1: INITIAL REASONING ===")
        print("Please provide this prompt to Claude Code/Desktop for initial reasoning:")
        print("-" * 50)
        print(analysis_prompt)
        print("-" * 50)

        # Return structured response for MCP integration
        return {
            "status": "awaiting_claude_reasoning",
            "prompt_for_claude": analysis_prompt,
            "next_step": "provide_claude_response",
            "instructions": """
1. Copy the above prompt to Claude Code/Desktop
2. Get Claude's reasoning and tool requests
3. Use the 'process_claude_response' method with Claude's response
            """
        }

    def process_claude_response(self, claude_response: str, execute_tools: bool = True) -> Dict[str, Any]:
        """Process Claude's response and execute requested tools"""
        self.add_message("assistant", claude_response)

        # Parse tool requests from Claude's response
        tool_requests = self._parse_tool_requests(claude_response)

        if not tool_requests and execute_tools:
            # If no tools found, try to extract manually or ask for clarification
            return {
                "status": "needs_clarification",
                "claude_response": claude_response,
                "message": "No clear tool requests found. Please specify which tools to run.",
                "available_tools": list(self.tools.tools.keys())
            }

        if execute_tools and tool_requests:
            print("\n=== STEP 2: EXECUTING TOOLS ===")
            print(f"Found {len(tool_requests)} tool requests:")
            for req in tool_requests:
                print(f"  - {req['tool']} with {req['params']}")

            # Execute tools
            results = self.execute_tools(tool_requests)

            # Format results for Claude
            formatted_results = self.format_tool_results(results)

            print("\n=== STEP 3: TOOL RESULTS ===")
            print(formatted_results)

            # Build prompt for final analysis
            final_prompt = f"""Based on my previous reasoning and the tool execution results below, please provide your comprehensive investment analysis and recommendation.

ORIGINAL QUERY: {self.history[0]['content']}

MY PREVIOUS REASONING:
{claude_response}

TOOL EXECUTION RESULTS:
{formatted_results}

Please now provide your final analysis and investment recommendation following the structure I outlined earlier."""

            print("\n=== STEP 4: FINAL ANALYSIS ===")
            print("Please provide this prompt to Claude Code/Desktop for final analysis:")
            print("-" * 50)
            print(final_prompt)
            print("-" * 50)

            return {
                "status": "awaiting_final_analysis",
                "tool_results": results,
                "prompt_for_claude": final_prompt,
                "claude_reasoning": claude_response,
                "tool_requests": tool_requests
            }

        else:
            return {
                "status": "tools_parsed",
                "tool_requests": tool_requests,
                "claude_response": claude_response,
                "message": "Tools parsed but not executed. Set execute_tools=True to run them."
            }

    def manual_tool_execution(self, tool_name: str, **params) -> Dict[str, Any]:
        """Manually execute a specific tool"""
        tool = self.tools.get(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool {tool_name} not found"}

        return tool.execute(**params)

def create_mcp_agent():
    """Create MCP agent with all standard tools registered"""
    from autoinvestor_react import (
        get_stock_price,
        get_company_financials,
        get_analyst_ratings,
        calculate_valuation,
        risk_assessment
    )

    agent = MCPReActAgent()

    # Register standard tools
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

# Example usage for testing
if __name__ == "__main__":
    # Create agent
    agent = create_mcp_agent()

    # Example analysis
    query = "Should I invest in Apple (AAPL) right now? I'm a balanced investor looking for long-term growth."

    # Start analysis
    result = agent.run_mcp_analysis(query)
    print(json.dumps(result, indent=2))