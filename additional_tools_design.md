# Additional Tools for AutoInvestor ReAct Agent

## Data Sources from Hugging Face Finance Commons

**Finance Commons:** https://huggingface.co/spaces/PleIAs/Finance-Commons

Available datasets:
- Financial news articles
- Company earnings transcripts
- SEC filings corpus
- Market sentiment data
- Historical price data
- Economic indicators

---

## Recommended Tool Suite (Next Phase)

### 1. Technical Analysis Tools

**Tool: `technical_indicators`**
```python
def technical_indicators(ticker: str, indicators: list) -> dict:
    """
    Calculate technical analysis indicators

    Args:
        ticker: Stock symbol
        indicators: List of indicators to calculate
            - "SMA_50": 50-day simple moving average
            - "SMA_200": 200-day simple moving average
            - "RSI": Relative Strength Index (14-day)
            - "MACD": Moving Average Convergence Divergence
            - "BB": Bollinger Bands
            - "VOLUME_SMA": Volume moving average

    Returns:
        {
            "ticker": "AAPL",
            "current_price": 178.45,
            "indicators": {
                "SMA_50": 172.30,
                "SMA_200": 165.80,
                "RSI": 62.5,
                "MACD": {
                    "value": 2.3,
                    "signal": 1.8,
                    "histogram": 0.5,
                    "interpretation": "bullish"
                },
                "BB": {
                    "upper": 185.20,
                    "middle": 175.40,
                    "lower": 165.60,
                    "position": "near_upper"
                }
            },
            "signals": [
                "Price above SMA_50 (bullish)",
                "SMA_50 above SMA_200 (golden cross)",
                "RSI neutral range (not overbought/oversold)",
                "MACD bullish crossover"
            ]
        }
    ```

    **Implementation:**
    - Use `pandas_ta` or `ta-lib` libraries
    - Fetch historical data from Yahoo Finance or Alpha Vantage
    - Calculate indicators
    - Generate interpretations

**Tool: `chart_patterns`**
```python
def chart_patterns(ticker: str, period: str = "6mo") -> dict:
    """
    Identify chart patterns (head & shoulders, triangles, etc.)

    Returns:
        {
            "ticker": "AAPL",
            "patterns_detected": [
                {
                    "pattern": "ascending_triangle",
                    "confidence": 0.85,
                    "timeframe": "3 months",
                    "target_price": 195.50,
                    "support_level": 170.00,
                    "resistance_level": 180.00
                }
            ],
            "key_levels": {
                "support": [165, 170, 175],
                "resistance": [180, 185, 190]
            }
        }
    ```

### 2. News & Sentiment Analysis

**Tool: `news_sentiment`**
```python
def news_sentiment(ticker: str, days: int = 7) -> dict:
    """
    Analyze recent news sentiment

    Uses Hugging Face Finance Commons news datasets

    Returns:
        {
            "ticker": "AAPL",
            "period": "7 days",
            "articles_analyzed": 45,
            "sentiment_score": 0.72,  # -1 to 1
            "sentiment_trend": "improving",
            "top_headlines": [
                {
                    "title": "Apple Unveils New AI Features",
                    "source": "Bloomberg",
                    "date": "2025-11-18",
                    "sentiment": 0.88,
                    "key_themes": ["AI", "innovation", "growth"]
                },
                ...
            ],
            "sentiment_by_category": {
                "product_news": 0.85,
                "earnings": 0.65,
                "regulation": -0.15,
                "management": 0.40
            }
        }
    ```

    **Implementation:**
    - Fetch news from NewsAPI, Finnhub, or HF Finance Commons
    - Use sentiment model (FinBERT or similar from HF)
    - Categorize and aggregate

**Tool: `social_sentiment`**
```python
def social_sentiment(ticker: str) -> dict:
    """
    Analyze social media sentiment (Twitter, Reddit, StockTwits)

    Returns:
        {
            "ticker": "AAPL",
            "platforms": {
                "twitter": {"sentiment": 0.65, "volume": "high", "mentions": 15420},
                "reddit": {"sentiment": 0.52, "volume": "medium", "wsb_rank": 8},
                "stocktwits": {"sentiment": 0.78, "bullish": 72, "bearish": 28}
            },
            "trending": true,
            "notable_mentions": [
                "Mentioned by 3 prominent finance influencers",
                "Trending on WallStreetBets"
            ]
        }
    ```

### 3. Historical Performance Tools

**Tool: `historical_performance`**
```python
def historical_performance(ticker: str, periods: list) -> dict:
    """
    Analyze historical returns over multiple periods

    Args:
        ticker: Stock symbol
        periods: ["1W", "1M", "3M", "6M", "1Y", "3Y", "5Y"]

    Returns:
        {
            "ticker": "AAPL",
            "returns": {
                "1W": 1.2,
                "1M": 5.4,
                "3M": 8.9,
                "6M": 15.2,
                "1Y": 32.5,
                "3Y": 89.3,
                "5Y": 245.7
            },
            "vs_sp500": {
                "1Y": "+12.3%",  # Outperformance
                "3Y": "+15.8%"
            },
            "volatility": {
                "annual": 0.28,
                "sharpe_ratio": 1.45
            },
            "drawdowns": {
                "max_drawdown": -32.5,
                "current_drawdown": -5.2,
                "recovery_time_avg": "3.2 months"
            }
        }
    ```

**Tool: `seasonal_patterns`**
```python
def seasonal_patterns(ticker: str) -> dict:
    """
    Identify seasonal performance patterns

    Returns:
        {
            "ticker": "AAPL",
            "best_months": ["October", "November", "December"],
            "worst_months": ["September"],
            "month_performance": {
                "January": {"avg_return": 3.2, "win_rate": 0.65},
                ...
            },
            "current_month_historical": {
                "month": "November",
                "avg_return": 4.1,
                "win_rate": 0.73,
                "interpretation": "Historically strong month for AAPL"
            }
        }
    ```

### 4. Earnings & Events

**Tool: `earnings_calendar`**
```python
def earnings_calendar(ticker: str) -> dict:
    """
    Get upcoming earnings and key events

    Returns:
        {
            "ticker": "AAPL",
            "next_earnings": {
                "date": "2025-11-28",
                "type": "Q4 2024",
                "days_until": 8,
                "after_hours": true
            },
            "analyst_estimates": {
                "eps_estimate": 1.53,
                "revenue_estimate": 123.5e9,
                "earnings_surprise_history": [
                    {"quarter": "Q3 2024", "surprise": "+5.2%"},
                    {"quarter": "Q2 2024", "surprise": "+3.8%"}
                ]
            },
            "upcoming_events": [
                {"date": "2025-12-15", "event": "Dividend payment"},
                {"date": "2026-01-15", "event": "Product launch event"}
            ]
        }
    ```

**Tool: `earnings_transcript_analysis`**
```python
def earnings_transcript_analysis(ticker: str, quarter: str = "latest") -> dict:
    """
    Analyze earnings call transcript for sentiment and key themes

    Uses Hugging Face earnings transcript datasets

    Returns:
        {
            "ticker": "AAPL",
            "quarter": "Q3 2024",
            "call_date": "2024-11-02",
            "management_sentiment": 0.78,  # Confidence level
            "key_themes": [
                {"theme": "AI growth", "mentions": 12, "sentiment": 0.92},
                {"theme": "China market", "mentions": 8, "sentiment": 0.45},
                {"theme": "margins", "mentions": 6, "sentiment": 0.65}
            ],
            "guidance": {
                "next_quarter_revenue": "125-130B",
                "tone": "optimistic",
                "risks_mentioned": ["supply chain", "fx headwinds"]
            },
            "analyst_questions_focus": [
                "AI monetization strategy",
                "iPhone 15 demand",
                "Services growth"
            ]
        }
    ```

### 5. Insider Trading & Institutional Holdings

**Tool: `insider_activity`**
```python
def insider_activity(ticker: str, days: int = 90) -> dict:
    """
    Track insider buying/selling

    Returns:
        {
            "ticker": "AAPL",
            "period": "90 days",
            "transactions": {
                "buys": 5,
                "sells": 12,
                "net_shares": -150000
            },
            "total_value": -12_500_000,
            "notable_transactions": [
                {
                    "date": "2025-11-10",
                    "insider": "CFO",
                    "transaction": "Sell",
                    "shares": 50000,
                    "value": 4_200_000,
                    "notes": "Pre-planned 10b5-1 sale"
                }
            ],
            "interpretation": "Neutral - mostly planned sales, limited buying"
        }
    ```

**Tool: `institutional_holdings`**
```python
def institutional_holdings(ticker: str) -> dict:
    """
    Analyze institutional investor holdings

    Returns:
        {
            "ticker": "AAPL",
            "institutional_ownership": 59.8,  # percent
            "top_holders": [
                {"name": "Vanguard", "shares": 1_234_567_890, "percent": 8.2, "change_qoq": "+0.3%"},
                {"name": "BlackRock", "shares": 1_098_765_432, "percent": 7.3, "change_qoq": "+0.1%"},
                ...
            ],
            "recent_changes": {
                "new_positions": 23,
                "increased_positions": 145,
                "decreased_positions": 89,
                "closed_positions": 12
            },
            "hedge_fund_activity": {
                "net_buying": true,
                "notable_additions": ["Renaissance Tech", "Citadel"],
                "notable_reductions": ["Third Point"]
            }
        }
    ```

### 6. Options Market Analysis

**Tool: `options_flow`**
```python
def options_flow(ticker: str) -> dict:
    """
    Analyze unusual options activity

    Returns:
        {
            "ticker": "AAPL",
            "unusual_activity": {
                "calls": 15,  # Unusual call sweeps detected
                "puts": 3
            },
            "put_call_ratio": 0.45,  # <1 is bullish
            "implied_volatility": {
                "current": 22.5,
                "rank": 35,  # Percentile vs historical
                "trend": "increasing"
            },
            "notable_trades": [
                {
                    "type": "call",
                    "strike": 200,
                    "expiry": "2026-01-15",
                    "volume": 5000,
                    "premium": 1_250_000,
                    "interpretation": "Bullish bet on >$200 by Jan"
                }
            ],
            "max_pain": 175.00,
            "interpretation": "Bullish options positioning"
        }
    ```

### 7. Macroeconomic Context

**Tool: `macro_indicators`**
```python
def macro_indicators(sector: str = None) -> dict:
    """
    Get relevant macroeconomic indicators

    Returns:
        {
            "indicators": {
                "fed_funds_rate": 5.25,
                "10_year_yield": 4.45,
                "inflation_yoy": 3.2,
                "unemployment": 3.8,
                "gdp_growth": 2.4
            },
            "market_regime": "late_cycle",
            "sector_impact": {
                "technology": "neutral_to_positive",
                "rationale": "Rates stabilizing, AI growth offsetting concerns"
            },
            "upcoming_events": [
                {"date": "2025-12-15", "event": "FOMC meeting", "expected": "Hold rates"}
            ]
        }
    ```

### 8. Competitor & Sector Analysis

**Tool: `sector_comparison`**
```python
def sector_comparison(ticker: str) -> dict:
    """
    Compare stock to sector peers

    Returns:
        {
            "ticker": "AAPL",
            "sector": "Technology - Consumer Electronics",
            "peers": ["MSFT", "GOOGL", "META", "AMZN"],
            "ranking": {
                "revenue_growth": 3,  # 3rd best of 5
                "profit_margin": 1,
                "valuation": 4,  # Expensive relative to peers
                "momentum": 2
            },
            "metrics_comparison": {
                "pe_ratio": {"AAPL": 28.4, "sector_avg": 32.1, "vs_sector": "-11.5%"},
                "revenue_growth": {"AAPL": 8.5, "sector_avg": 15.2, "vs_sector": "-44%"},
                "profit_margin": {"AAPL": 25.3, "sector_avg": 18.7, "vs_sector": "+35%"}
            },
            "relative_strength": {
                "vs_sector": "+5.2%",  # YTD
                "vs_sp500": "+12.8%"
            }
        }
    ```

---

## Implementation Priority

**Phase 1 (Essential - Week 2-3):**
1. technical_indicators
2. news_sentiment
3. historical_performance
4. earnings_calendar

**Phase 2 (Enhanced Analysis - Week 3-4):**
5. insider_activity
6. institutional_holdings
7. sector_comparison
8. chart_patterns

**Phase 3 (Advanced - Week 4-5):**
9. options_flow
10. social_sentiment
11. earnings_transcript_analysis
12. seasonal_patterns
13. macro_indicators

---

## Data Source Integration Plan

### For Real Implementation:

**Market Data:**
- Alpha Vantage (free tier: 500 calls/day)
- Yahoo Finance (yfinance Python library - free)
- IEX Cloud (better for production)

**News:**
- NewsAPI (free tier: 100 calls/day)
- Finnhub (free tier available)
- Hugging Face Finance Commons (free datasets)

**Fundamentals:**
- SEC EDGAR API (free)
- Financial Modeling Prep (free tier)
- Yahoo Finance (free)

**Sentiment:**
- FinBERT from Hugging Face (free)
- Twitter API (paid, or scrape Reddit)
- StockTwits API (free)

**Options:**
- CBOE (free delayed data)
- Unusual Whales (paid API)
- TradingView (scraping)

**Insider/Institutional:**
- SEC Form 4/13F filings (free via EDGAR)
- WhaleWisdom API (paid)
- Fintel (free tier)

---

## Cost Estimates for Real Data

**Free Tier (Development):**
- Market data: Yahoo Finance + Alpha Vantage
- News: NewsAPI free tier
- Sentiment: Hugging Face models (free)
- SEC data: EDGAR (free)
- **Cost: $0/month, 500-1000 analyses/month**

**Basic Paid (Production):**
- IEX Cloud: $9/month
- Finnhub: $0 (free tier)
- NewsAPI: $0 (free tier)
- **Cost: ~$10/month, 10,000 analyses/month**

**Professional:**
- IEX Cloud: $79/month
- Finnhub Pro: $60/month
- Unusual Whales: $40/month
- **Cost: ~$180/month, unlimited analyses**

---

## Next Steps

1. **Test current implementation** with mock data
2. **Integrate one real API** (start with Yahoo Finance - easiest)
3. **Add technical_indicators tool** (most requested by traders)
4. **Add news_sentiment** using Hugging Face
5. **Iterate based on user feedback**

Ready to implement!
