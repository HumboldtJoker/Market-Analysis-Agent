# AutoInvestor ReAct Agent Architecture

**Design:** Lyra
**Purpose:** Investment research and recommendation agent using ReAct (Reasoning + Acting) methodology
**Target:** Sellable product for retail and institutional investors

---

## 1. ReAct Pattern Overview

**Core Loop:**
```
Thought → Action → Observation → Thought → Action → Observation → ... → Final Answer
```

**Key Principles:**
- Agent explicitly reasons before each action
- Actions are tool calls (API requests, data fetches, calculations)
- Observations are tool results
- Reasoning traces are visible to users (builds trust)
- Agent can self-correct based on observations

---

## 2. Agent Architecture

### 2.1 System Components

```
┌─────────────────────────────────────────────────┐
│           ReAct Orchestrator                    │
│  - Manages thought/action/observation loop      │
│  - Maintains conversation history               │
│  - Handles tool execution                       │
└─────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│              Tool Suite                         │
│  - Market Data APIs                             │
│  - SEC Filing Retrieval                         │
│  - News & Sentiment Analysis                    │
│  - Financial Calculations                       │
│  - Portfolio Management                         │
└─────────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────┐
│         Knowledge Base (Optional)               │
│  - Historical analysis results                  │
│  - Company profiles                             │
│  - Sector trends                                │
└─────────────────────────────────────────────────┘
```

### 2.2 ReAct Loop Implementation

```python
class ReActInvestmentAgent:
    def __init__(self, tools, llm, max_iterations=10):
        self.tools = tools
        self.llm = llm
        self.max_iterations = max_iterations
        self.history = []

    def run(self, user_query):
        """Main ReAct loop"""
        for i in range(self.max_iterations):
            # Generate thought + action
            response = self.llm.generate(
                prompt=self._build_prompt(user_query),
                history=self.history
            )

            # Parse response
            thought, action, action_input = self._parse_response(response)

            # Record thought
            self.history.append({
                "type": "thought",
                "content": thought,
                "iteration": i
            })

            # Check if done
            if action == "FINAL_ANSWER":
                return self._format_final_answer(action_input)

            # Execute action
            observation = self._execute_tool(action, action_input)

            # Record action and observation
            self.history.append({
                "type": "action",
                "tool": action,
                "input": action_input,
                "iteration": i
            })

            self.history.append({
                "type": "observation",
                "content": observation,
                "iteration": i
            })

        # Max iterations reached
        return self._format_timeout_response()
```

---

## 3. Tool Suite Design

### 3.1 Core Tools

**1. get_stock_price**
```python
def get_stock_price(ticker: str, date: str = "latest") -> dict:
    """
    Fetch current or historical stock price

    Args:
        ticker: Stock symbol (e.g., "AAPL")
        date: "latest" or YYYY-MM-DD format

    Returns:
        {
            "ticker": "AAPL",
            "price": 178.45,
            "change": +2.34,
            "change_percent": +1.33,
            "volume": 45234567,
            "timestamp": "2025-11-20 16:00:00"
        }
    """
```

**2. get_company_financials**
```python
def get_company_financials(ticker: str, statement: str, period: str = "quarterly") -> dict:
    """
    Fetch company financial statements from SEC filings

    Args:
        ticker: Stock symbol
        statement: "income" | "balance" | "cashflow"
        period: "quarterly" | "annual"

    Returns:
        {
            "ticker": "AAPL",
            "statement": "income",
            "period": "Q3 2024",
            "revenue": 94930000000,
            "net_income": 22956000000,
            "eps": 1.47,
            "metrics": {...}
        }
    """
```

**3. get_market_news**
```python
def get_market_news(ticker: str = None, topic: str = None, limit: int = 10) -> list:
    """
    Fetch recent market news and sentiment

    Args:
        ticker: Optional stock symbol to filter news
        topic: Optional topic (e.g., "earnings", "FDA approval")
        limit: Number of articles to return

    Returns:
        [
            {
                "title": "Apple Reports Record Q3 Earnings",
                "source": "Bloomberg",
                "published": "2024-11-15 14:30:00",
                "sentiment": 0.85,  # -1 to 1
                "summary": "...",
                "url": "..."
            }
        ]
    """
```

**4. calculate_valuation_metrics**
```python
def calculate_valuation_metrics(ticker: str) -> dict:
    """
    Calculate key valuation metrics

    Returns:
        {
            "ticker": "AAPL",
            "pe_ratio": 28.4,
            "forward_pe": 26.1,
            "peg_ratio": 2.1,
            "price_to_book": 42.3,
            "price_to_sales": 7.8,
            "dividend_yield": 0.52,
            "market_cap": 2_850_000_000_000
        }
    """
```

**5. get_analyst_ratings**
```python
def get_analyst_ratings(ticker: str) -> dict:
    """
    Fetch analyst consensus ratings

    Returns:
        {
            "ticker": "AAPL",
            "consensus": "Buy",
            "ratings": {
                "strong_buy": 15,
                "buy": 12,
                "hold": 3,
                "sell": 0,
                "strong_sell": 0
            },
            "price_target": {
                "low": 165,
                "average": 195,
                "high": 220
            }
        }
    """
```

**6. compare_competitors**
```python
def compare_competitors(ticker: str, metrics: list) -> dict:
    """
    Compare company against sector competitors

    Args:
        ticker: Primary stock symbol
        metrics: List of metrics to compare (e.g., ["revenue_growth", "profit_margin"])

    Returns:
        {
            "ticker": "AAPL",
            "sector": "Technology",
            "competitors": ["MSFT", "GOOGL", "META"],
            "comparison": {
                "revenue_growth": {
                    "AAPL": 8.5,
                    "MSFT": 12.3,
                    "GOOGL": 6.7,
                    "META": 22.1,
                    "sector_avg": 12.4
                },
                ...
            }
        }
    """
```

**7. search_sec_filings**
```python
def search_sec_filings(ticker: str, filing_type: str = "10-K", limit: int = 5) -> list:
    """
    Search and retrieve SEC filings

    Args:
        ticker: Stock symbol
        filing_type: "10-K" | "10-Q" | "8-K" | "DEF 14A"
        limit: Number of filings to return

    Returns:
        [
            {
                "ticker": "AAPL",
                "filing_type": "10-K",
                "filed_date": "2024-10-27",
                "period_end": "2024-09-28",
                "url": "...",
                "key_sections": {...}
            }
        ]
    """
```

### 3.2 Analysis Tools

**8. technical_analysis**
```python
def technical_analysis(ticker: str, indicators: list) -> dict:
    """
    Perform technical analysis

    Args:
        ticker: Stock symbol
        indicators: List of indicators ["SMA_50", "RSI", "MACD", "Bollinger"]

    Returns:
        {
            "ticker": "AAPL",
            "current_price": 178.45,
            "indicators": {
                "SMA_50": 172.30,
                "SMA_200": 165.80,
                "RSI": 62.5,
                "MACD": {"value": 2.3, "signal": "bullish"},
                "Bollinger": {"upper": 185, "middle": 175, "lower": 165}
            },
            "signals": ["Price above SMA_50", "RSI neutral", "MACD bullish"]
        }
    """
```

**9. risk_assessment**
```python
def risk_assessment(ticker: str) -> dict:
    """
    Assess investment risk factors

    Returns:
        {
            "ticker": "AAPL",
            "volatility": {
                "30_day": 0.22,
                "90_day": 0.28,
                "1_year": 0.31
            },
            "beta": 1.24,
            "risk_score": 6.5,  # 1-10 scale
            "risk_factors": [
                "High valuation multiples",
                "Regulatory scrutiny in EU",
                "Supply chain dependencies"
            ]
        }
    """
```

**10. portfolio_optimization**
```python
def portfolio_optimization(tickers: list, weights: list = None) -> dict:
    """
    Analyze portfolio composition and suggest optimizations

    Args:
        tickers: List of stock symbols
        weights: Optional list of current weights (must sum to 1.0)

    Returns:
        {
            "current_portfolio": {...},
            "suggested_weights": {...},
            "expected_return": 0.12,
            "risk": 0.18,
            "sharpe_ratio": 0.67,
            "diversification_score": 7.2
        }
    """
```

---

## 4. ReAct Prompt Template

```python
REACT_SYSTEM_PROMPT = """You are an expert investment research analyst using the ReAct (Reasoning + Acting) methodology.

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
{tool_descriptions}

OUTPUT FORMAT:
For each step, use this exact format:

Thought: [Your reasoning about what to do next]
Action: [tool_name]
Action Input: [tool parameters as JSON]

After receiving observations, continue with:

Thought: [Your analysis of the observation]
Action: [next tool_name or FINAL_ANSWER]
Action Input: [parameters or your final recommendation]

EXAMPLE:
Thought: I need to analyze Apple's recent performance. Let me start by getting the current stock price and recent price movements.
Action: get_stock_price
Action Input: {{"ticker": "AAPL", "date": "latest"}}

[After observation]

Thought: The stock is up 1.33% today. Now I should check the fundamental health by looking at recent earnings.
Action: get_company_financials
Action Input: {{"ticker": "AAPL", "statement": "income", "period": "quarterly"}}

...

Thought: Based on strong earnings growth, positive analyst sentiment, but elevated valuation, I have enough information for a recommendation.
Action: FINAL_ANSWER
Action Input: **Recommendation: BUY with caution**

[Full recommendation details]

USER QUERY: {user_query}

Begin your research:
"""
```

---

## 5. Example Workflow

### User Query: "Should I invest in NVIDIA right now?"

**Agent ReAct Trace:**

```
Thought: To evaluate NVIDIA as an investment, I need to check multiple factors:
current price trends, financial health, competitive position, and analyst sentiment.
Let me start with the current stock price and recent movement.

Action: get_stock_price
Action Input: {"ticker": "NVDA", "date": "latest"}

Observation: {
    "ticker": "NVDA",
    "price": 495.32,
    "change": +12.45,
    "change_percent": +2.58,
    "volume": 52341234,
    "timestamp": "2025-11-20 16:00:00"
}

---

Thought: Stock is up 2.58% today with high volume - shows strong momentum. Now I need
to understand if this is justified by fundamentals. Let me check recent earnings.

Action: get_company_financials
Action Input: {"ticker": "NVDA", "statement": "income", "period": "quarterly"}

Observation: {
    "ticker": "NVDA",
    "statement": "income",
    "period": "Q3 2024",
    "revenue": 18120000000,
    "revenue_growth_yoy": 206%,
    "net_income": 9243000000,
    "eps": 3.71,
    "gross_margin": 75.0%
}

---

Thought: Exceptional revenue growth of 206% YoY and 75% gross margin - this is
extraordinary performance driven by AI chip demand. But I need to check if the
valuation has gotten ahead of itself.

Action: calculate_valuation_metrics
Action Input: {"ticker": "NVDA"}

Observation: {
    "ticker": "NVDA",
    "pe_ratio": 67.2,
    "forward_pe": 42.1,
    "peg_ratio": 0.32,
    "price_to_sales": 32.1,
    "market_cap": 1_220_000_000_000
}

---

Thought: PE of 67.2 looks high, but PEG ratio of 0.32 (under 1.0 is attractive)
suggests growth justifies valuation. Let me see how NVIDIA compares to competitors
in the semiconductor space.

Action: compare_competitors
Action Input: {"ticker": "NVDA", "metrics": ["revenue_growth", "gross_margin", "market_share"]}

Observation: {
    "ticker": "NVDA",
    "sector": "Semiconductors",
    "competitors": ["AMD", "INTC", "QCOM"],
    "comparison": {
        "revenue_growth": {
            "NVDA": 206%,
            "AMD": 18%,
            "INTC": -8%,
            "QCOM": 5%
        },
        "gross_margin": {
            "NVDA": 75%,
            "AMD": 48%,
            "INTC": 43%,
            "QCOM": 58%
        }
    }
}

---

Thought: NVIDIA is significantly outperforming all major competitors in both growth
and margins - dominant market position. Let me check analyst sentiment and risk factors.

Action: get_analyst_ratings
Action Input: {"ticker": "NVDA"}

Observation: {
    "ticker": "NVDA",
    "consensus": "Strong Buy",
    "ratings": {
        "strong_buy": 28,
        "buy": 7,
        "hold": 2,
        "sell": 0
    },
    "price_target": {
        "low": 450,
        "average": 625,
        "high": 800
    }
}

---

Thought: Overwhelming analyst support with average target of $625 (26% upside from
current $495). But I should assess risk factors before final recommendation.

Action: risk_assessment
Action Input: {"ticker": "NVDA"}

Observation: {
    "ticker": "NVDA",
    "volatility": {
        "30_day": 0.45,
        "90_day": 0.52
    },
    "beta": 1.68,
    "risk_score": 7.5,
    "risk_factors": [
        "High concentration in AI chips (diversification concern)",
        "Elevated volatility - beta of 1.68",
        "Geopolitical risks (China export restrictions)",
        "Valuation sensitivity to growth expectations"
    ]
}

---

Thought: High risk score of 7.5/10 and beta of 1.68 means this is a volatile
stock. However, the fundamental strength, market dominance, and analyst support
are compelling. Let me check recent news for any immediate concerns.

Action: get_market_news
Action Input: {"ticker": "NVDA", "limit": 5}

Observation: [
    {
        "title": "NVIDIA Unveils Next-Gen AI Chips, Stock Surges",
        "sentiment": 0.92,
        "published": "2025-11-18",
        "summary": "New Blackwell architecture showing 30x performance improvement..."
    },
    {
        "title": "Hyperscalers Increase NVIDIA Orders for 2025",
        "sentiment": 0.88,
        "published": "2025-11-17"
    }
]

---

Thought: Recent positive catalysts with new product launches and strong demand signals.
I have enough data for a comprehensive recommendation. Let me synthesize this into
a clear investment thesis.

Action: FINAL_ANSWER
Action Input:

**INVESTMENT RECOMMENDATION: BUY (Moderate Position Size)**

**Recommendation Strength:** 8/10

**Investment Thesis:**
NVIDIA demonstrates exceptional fundamental strength with 206% YoY revenue growth
and market-leading 75% gross margins, driven by dominant position in AI accelerators.
The company significantly outperforms all semiconductor competitors.

**Key Strengths:**
✓ Explosive revenue growth (206% YoY) vs competitors (AMD 18%, Intel -8%)
✓ Industry-leading gross margins (75% vs sector avg ~50%)
✓ Strong analyst consensus: 28 Strong Buy, 7 Buy, 2 Hold, 0 Sell
✓ Attractive PEG ratio (0.32) suggests growth justifies valuation
✓ Recent product catalysts (Blackwell architecture launch)
✓ Average analyst price target $625 (+26% upside from $495)

**Risk Factors:**
⚠ High volatility (beta 1.68) - expect large price swings
⚠ Elevated PE ratio (67.2) vulnerable to growth disappointments
⚠ Concentration risk in AI chips
⚠ Geopolitical risks (China export restrictions)
⚠ Risk score: 7.5/10 (above average)

**Recommended Action:**
- **Entry:** BUY at current levels ($495)
- **Position Size:** Moderate (5-8% of portfolio max due to volatility)
- **Target Price:** $625 (analyst average)
- **Stop Loss:** $420 (-15% downside protection)
- **Time Horizon:** 12-18 months

**Caveats:**
- Only suitable for growth-oriented investors with moderate-to-high risk tolerance
- Expect significant volatility - prepare for 20%+ swings
- Monitor quarterly earnings closely - any growth deceleration could trigger selloff
- Consider dollar-cost averaging to mitigate timing risk

**Alternative Strategy (Conservative):**
If volatility concerns you, consider waiting for a pullback to $450-460 range
or building position gradually over 2-3 months.

---

This recommendation is based on current market conditions as of 2025-11-20.
Market conditions can change rapidly. Always do your own due diligence.
```

---

## 6. Safety Guardrails & Risk Management

### 6.1 Investment Risk Safeguards

```python
class RiskGuardrails:
    """Safety checks before providing recommendations"""

    def validate_recommendation(self, recommendation: dict) -> tuple[bool, str]:
        """Validate recommendation meets safety criteria"""

        # Check 1: Must have supporting data
        if not recommendation.get("supporting_data"):
            return False, "Recommendation must be backed by real data"

        # Check 2: Risk assessment required
        if not recommendation.get("risk_factors"):
            return False, "Risk factors must be disclosed"

        # Check 3: Position size limits
        if recommendation.get("position_size", 0) > 0.15:
            return False, "Single position cannot exceed 15% of portfolio"

        # Check 4: Stop loss required for high-risk stocks
        risk_score = recommendation.get("risk_score", 0)
        if risk_score > 7.0 and not recommendation.get("stop_loss"):
            return False, "High-risk stocks require stop loss recommendation"

        # Check 5: Disclaimer present
        if "Market conditions can change" not in recommendation.get("disclaimer", ""):
            return False, "Must include disclaimer"

        return True, "Recommendation passes safety checks"

    def check_concentration_risk(self, portfolio: dict, new_ticker: str) -> bool:
        """Prevent over-concentration in single stocks"""
        current_holdings = portfolio.get("holdings", {})

        # No single stock > 20%
        if current_holdings.get(new_ticker, 0) > 0.20:
            return False

        # Top 5 holdings < 60%
        top_5_weight = sum(sorted(current_holdings.values(), reverse=True)[:5])
        if top_5_weight > 0.60:
            return False

        return True

    def volatility_check(self, ticker: str, risk_tolerance: str) -> bool:
        """Match stock volatility to user risk tolerance"""
        stock_data = get_stock_volatility(ticker)
        volatility = stock_data["90_day_volatility"]

        limits = {
            "conservative": 0.25,
            "moderate": 0.40,
            "aggressive": 1.0
        }

        return volatility <= limits.get(risk_tolerance, 0.40)
```

### 6.2 Data Quality Checks

```python
def validate_tool_output(tool_name: str, output: dict) -> bool:
    """Ensure tool outputs are complete and reasonable"""

    validation_rules = {
        "get_stock_price": {
            "required_fields": ["ticker", "price", "timestamp"],
            "price_range": (0.01, 100000),  # Reasonable stock price range
            "volume_min": 1000
        },
        "get_company_financials": {
            "required_fields": ["revenue", "net_income"],
            "revenue_min": 1000000  # $1M minimum (filters penny stocks)
        },
        "get_analyst_ratings": {
            "required_fields": ["consensus", "ratings"],
            "min_analyst_count": 3  # Need minimum analyst coverage
        }
    }

    rules = validation_rules.get(tool_name, {})

    # Check required fields exist
    for field in rules.get("required_fields", []):
        if field not in output:
            return False

    # Check value ranges
    if "price_range" in rules:
        price = output.get("price", 0)
        if not (rules["price_range"][0] <= price <= rules["price_range"][1]):
            return False

    return True
```

### 6.3 Compliance & Disclaimers

```python
COMPLIANCE_DISCLAIMER = """
IMPORTANT DISCLAIMERS:

1. This analysis is for informational purposes only and does not constitute
   financial advice, investment recommendation, or an offer to buy/sell securities.

2. Past performance does not guarantee future results. All investments carry risk,
   including potential loss of principal.

3. The information provided is based on data available as of {timestamp} and may
   not reflect current market conditions.

4. You should conduct your own research and consult with a licensed financial
   advisor before making investment decisions.

5. The analyst/tool provider does not have a material financial relationship
   with the companies mentioned.

6. Market conditions can change rapidly. Always do your own due diligence.

By using this analysis, you acknowledge these disclaimers and assume full
responsibility for your investment decisions.
"""
```

---

## 7. Implementation Roadmap

### Phase 1: Core ReAct Engine (Week 1-2)
- [ ] Build ReAct orchestrator with thought/action/observation loop
- [ ] Implement prompt template system
- [ ] Create tool execution framework
- [ ] Add conversation history management
- [ ] Test with mock tools

### Phase 2: Essential Tools (Week 2-3)
- [ ] Integrate market data API (Alpha Vantage, Yahoo Finance, or IEX Cloud)
- [ ] Implement SEC filing retrieval (EDGAR API)
- [ ] Add basic financial calculations
- [ ] Build analyst rating aggregator
- [ ] Create simple risk assessment

### Phase 3: Advanced Analysis (Week 3-4)
- [ ] Add technical analysis indicators
- [ ] Implement competitor comparison
- [ ] Build sentiment analysis from news
- [ ] Create portfolio optimization tools
- [ ] Add custom metric calculations

### Phase 4: Safety & Polish (Week 4-5)
- [ ] Implement all safety guardrails
- [ ] Add compliance disclaimers
- [ ] Build output formatting
- [ ] Create user preference system (risk tolerance, investment style)
- [ ] Comprehensive testing

### Phase 5: Product Features (Week 5-6)
- [ ] Multi-stock comparison mode
- [ ] Portfolio analysis mode
- [ ] Watchlist monitoring
- [ ] Alert generation
- [ ] Export capabilities (PDF reports)

---

## 8. Tech Stack Recommendations

### Core Components
- **LLM:** Claude 3.5 Sonnet (for reasoning) + Haiku (for simple tool calls)
- **Orchestration:** LangChain or custom Python
- **Data APIs:**
  - Market data: Alpha Vantage (free tier) or IEX Cloud (better for production)
  - SEC filings: EDGAR API (free)
  - News: NewsAPI or Finnhub
- **Database:** PostgreSQL for storing analysis history
- **Cache:** Redis for API response caching (reduce costs)

### Development Tools
- **Framework:** FastAPI for backend API
- **Frontend:** React or Streamlit (for demo/MVP)
- **Testing:** pytest for unit tests
- **Monitoring:** Sentry for error tracking

---

## 9. Pricing Strategy for Product

### Tier 1: Free (Demo/Freemium)
- 10 stock analyses per month
- Basic tools only (price, financials, news)
- Community support

### Tier 2: Individual ($29/month)
- 100 stock analyses per month
- All analysis tools
- Portfolio tracking (up to 3 portfolios)
- Email alerts
- Priority support

### Tier 3: Professional ($99/month)
- Unlimited analyses
- Advanced tools (portfolio optimization, custom metrics)
- API access
- White-label reports
- Dedicated support

### Tier 4: Institutional (Custom pricing)
- Multi-user accounts
- Custom tool integration
- Dedicated infrastructure
- SLA guarantees
- Compliance support

---

## 10. Next Steps

**Immediate Actions:**
1. Set up development environment
2. Choose and integrate first market data API
3. Build minimal ReAct loop with 2-3 core tools
4. Test with real stock analysis examples
5. Iterate on prompt engineering for better reasoning

**Success Metrics:**
- Recommendation accuracy (track vs actual performance)
- User satisfaction with reasoning transparency
- Tool usage patterns (which tools most valuable)
- Time to complete analysis
- Cost per analysis (LLM token usage)

---

**Ready to build?** Let's start with the core ReAct orchestrator and get a working prototype analyzing real stocks.
