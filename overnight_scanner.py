"""
Overnight News Scanner and Pre-Market Briefing System

Scans news overnight for held positions and watchlist tickers.
Generates pre-market briefings with actionable trade recommendations.
Tracks earnings calendar and flags upcoming events.

Schedule:
- Overnight scans: 8 PM, 2 AM PT (during market closed hours)
- Pre-market briefing: 6:15 AM PT (before market open at 6:30 AM PT)
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import yfinance as yf
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from news_sentiment import get_news_sentiment, analyze_news_sentiment
from order_executor import OrderExecutor

logger = logging.getLogger(__name__)


class OvernightScanner:
    """Scans news overnight and generates pre-market briefings"""

    def __init__(self, executor: OrderExecutor = None):
        self.executor = executor or OrderExecutor(mode='alpaca')
        self.project_dir = Path(__file__).parent
        self.overnight_news_file = self.project_dir / 'overnight_news.json'
        self.events_calendar_file = self.project_dir / 'events_calendar.json'
        self.morning_briefing_file = self.project_dir / 'morning_briefing.md'

        # Load thresholds for watchlist
        self.thresholds_file = self.project_dir / 'thresholds.json'
        self.watchlist = []
        self._load_watchlist()

    def _load_watchlist(self):
        """Load watchlist from thresholds.json"""
        try:
            with open(self.thresholds_file, 'r') as f:
                config = json.load(f)
                self.watchlist = config.get('watchlist', {}).get('scan_universe', [])
        except Exception as e:
            logger.error(f"Failed to load watchlist: {e}")
            self.watchlist = []

    def get_held_tickers(self) -> List[str]:
        """Get list of currently held position tickers"""
        try:
            portfolio = self.executor.get_portfolio_summary()
            return [pos['ticker'] for pos in portfolio.get('positions', [])]
        except Exception as e:
            logger.error(f"Failed to get held tickers: {e}")
            return []

    def scan_overnight_news(self) -> Dict:
        """
        Scan news for all held positions and watchlist.
        Returns categorized news with sentiment and urgency flags.
        """
        logger.info("[OVERNIGHT SCAN] Starting news scan...")

        held_tickers = self.get_held_tickers()
        all_tickers = list(set(held_tickers + self.watchlist))

        results = {
            "scan_time": datetime.now().isoformat(),
            "held_positions": held_tickers,
            "watchlist_scanned": self.watchlist,
            "breaking_news": [],      # High urgency - may need action
            "upgrades_downgrades": [], # Analyst actions
            "earnings_related": [],    # Earnings mentions
            "general_news": [],        # Normal news by ticker
            "sentiment_summary": {}    # Overall sentiment by ticker
        }

        for ticker in all_tickers:
            try:
                news_data = get_news_sentiment(ticker, days=1)  # Last 24 hours

                if "error" in news_data:
                    continue

                # Store sentiment summary
                results["sentiment_summary"][ticker] = {
                    "overall": news_data.get("overall_sentiment", "UNKNOWN"),
                    "positive_pct": news_data.get("sentiment_breakdown", {}).get("positive_pct", 0),
                    "negative_pct": news_data.get("sentiment_breakdown", {}).get("negative_pct", 0),
                    "article_count": news_data.get("articles_analyzed", 0),
                    "is_held": ticker in held_tickers
                }

                # Categorize articles
                for article in news_data.get("articles", []):
                    title_lower = article.get("title", "").lower()

                    article_data = {
                        "ticker": ticker,
                        "is_held": ticker in held_tickers,
                        **article
                    }

                    # Check for breaking/urgent news
                    breaking_keywords = ['breaking', 'urgent', 'alert', 'crash', 'surge',
                                        'plunge', 'halted', 'investigation', 'sec', 'fda',
                                        'recall', 'bankruptcy', 'merger', 'acquisition']
                    if any(kw in title_lower for kw in breaking_keywords):
                        article_data["urgency"] = "HIGH"
                        results["breaking_news"].append(article_data)
                        continue

                    # Check for analyst actions
                    analyst_keywords = ['upgrade', 'downgrade', 'price target', 'rating',
                                       'buy rating', 'sell rating', 'hold rating', 'outperform',
                                       'underperform', 'overweight', 'underweight']
                    if any(kw in title_lower for kw in analyst_keywords):
                        results["upgrades_downgrades"].append(article_data)
                        continue

                    # Check for earnings related
                    earnings_keywords = ['earnings', 'revenue', 'guidance', 'forecast',
                                        'quarterly', 'q1', 'q2', 'q3', 'q4', 'beat', 'miss',
                                        'eps', 'profit', 'loss']
                    if any(kw in title_lower for kw in earnings_keywords):
                        results["earnings_related"].append(article_data)
                        continue

                    # General news
                    results["general_news"].append(article_data)

            except Exception as e:
                logger.error(f"Error scanning news for {ticker}: {e}")

        # Save results
        with open(self.overnight_news_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"[OVERNIGHT SCAN] Complete - Breaking: {len(results['breaking_news'])}, "
                   f"Upgrades/Downgrades: {len(results['upgrades_downgrades'])}, "
                   f"Earnings: {len(results['earnings_related'])}")

        return results

    def get_earnings_calendar(self) -> Dict:
        """
        Get earnings dates for held positions and watchlist.
        Returns upcoming earnings within next 14 days.
        """
        logger.info("[EARNINGS CALENDAR] Fetching earnings dates...")

        held_tickers = self.get_held_tickers()
        all_tickers = list(set(held_tickers + self.watchlist))

        calendar = {
            "scan_time": datetime.now().isoformat(),
            "upcoming_earnings": [],
            "by_ticker": {}
        }

        today = datetime.now().date()
        cutoff = today + timedelta(days=14)

        for ticker in all_tickers:
            try:
                stock = yf.Ticker(ticker)

                # Get earnings dates
                try:
                    earnings_dates = stock.earnings_dates
                    if earnings_dates is not None and not earnings_dates.empty:
                        # Find next earnings date
                        future_dates = earnings_dates[earnings_dates.index >= datetime.now()]
                        if not future_dates.empty:
                            next_earnings = future_dates.index[0]
                            earnings_date = next_earnings.date() if hasattr(next_earnings, 'date') else next_earnings

                            earnings_info = {
                                "ticker": ticker,
                                "earnings_date": str(earnings_date),
                                "is_held": ticker in held_tickers,
                                "days_until": (earnings_date - today).days if isinstance(earnings_date, type(today)) else None
                            }

                            calendar["by_ticker"][ticker] = earnings_info

                            # Add to upcoming if within 14 days
                            if earnings_info["days_until"] is not None and 0 <= earnings_info["days_until"] <= 14:
                                calendar["upcoming_earnings"].append(earnings_info)
                except Exception as e:
                    # Earnings dates not available for this ticker
                    pass

                # Also check for ex-dividend dates
                try:
                    info = stock.info
                    ex_div_date = info.get('exDividendDate')
                    if ex_div_date:
                        ex_div = datetime.fromtimestamp(ex_div_date).date()
                        if today <= ex_div <= cutoff:
                            calendar["by_ticker"].setdefault(ticker, {})
                            calendar["by_ticker"][ticker]["ex_dividend_date"] = str(ex_div)
                            calendar["by_ticker"][ticker]["dividend_yield"] = info.get('dividendYield', 0)
                except:
                    pass

            except Exception as e:
                logger.debug(f"Could not get calendar for {ticker}: {e}")

        # Sort upcoming earnings by date
        calendar["upcoming_earnings"].sort(key=lambda x: x.get("days_until", 999))

        # Save calendar
        with open(self.events_calendar_file, 'w') as f:
            json.dump(calendar, f, indent=2)

        logger.info(f"[EARNINGS CALENDAR] Found {len(calendar['upcoming_earnings'])} upcoming earnings in next 14 days")

        return calendar

    def generate_premarket_briefing(self) -> str:
        """
        Generate a pre-market briefing summarizing overnight developments.
        Returns markdown-formatted briefing.
        """
        logger.info("[PRE-MARKET BRIEFING] Generating briefing...")

        # Get fresh data
        news_data = self.scan_overnight_news()
        calendar_data = self.get_earnings_calendar()

        # Get current portfolio
        try:
            portfolio = self.executor.get_portfolio_summary()
            portfolio_value = portfolio.get('total_value', 0)
            cash = portfolio.get('cash', 0)
            positions = portfolio.get('positions', [])
        except:
            portfolio_value = 0
            cash = 0
            positions = []

        # Build briefing
        briefing_lines = [
            f"# Pre-Market Briefing - {datetime.now().strftime('%Y-%m-%d %H:%M PT')}",
            "",
            "## Portfolio Snapshot",
            f"- **Portfolio Value:** ${portfolio_value:,.2f}",
            f"- **Cash:** ${cash:,.2f}",
            f"- **Positions:** {len(positions)}",
            "",
        ]

        # Breaking news section
        if news_data.get("breaking_news"):
            briefing_lines.append("## 🚨 BREAKING NEWS (Action May Be Required)")
            briefing_lines.append("")
            for news in news_data["breaking_news"][:5]:  # Top 5
                held_tag = "**[HELD]**" if news.get("is_held") else "[WATCHLIST]"
                sentiment_tag = f"[{news.get('sentiment', 'unknown').upper()}]"
                briefing_lines.append(f"- {held_tag} **{news['ticker']}** {sentiment_tag}: {news.get('title', 'No title')}")
                briefing_lines.append(f"  - Source: {news.get('publisher', 'Unknown')} | {news.get('published', '')}")
            briefing_lines.append("")

        # Upgrades/Downgrades
        if news_data.get("upgrades_downgrades"):
            briefing_lines.append("## 📊 Analyst Actions")
            briefing_lines.append("")
            for news in news_data["upgrades_downgrades"][:5]:
                held_tag = "**[HELD]**" if news.get("is_held") else "[WATCHLIST]"
                briefing_lines.append(f"- {held_tag} **{news['ticker']}**: {news.get('title', 'No title')}")
            briefing_lines.append("")

        # Earnings calendar
        if calendar_data.get("upcoming_earnings"):
            briefing_lines.append("## 📅 Upcoming Earnings (Next 14 Days)")
            briefing_lines.append("")
            for event in calendar_data["upcoming_earnings"][:10]:
                held_tag = "**[HELD]**" if event.get("is_held") else "[WATCHLIST]"
                days = event.get("days_until", "?")
                urgency = "⚠️ **TODAY**" if days == 0 else ("⚠️ **TOMORROW**" if days == 1 else f"in {days} days")
                briefing_lines.append(f"- {held_tag} **{event['ticker']}**: {event.get('earnings_date', 'TBD')} ({urgency})")
            briefing_lines.append("")

        # Sentiment summary for held positions
        briefing_lines.append("## 📰 Overnight Sentiment (Held Positions)")
        briefing_lines.append("")
        held_sentiment = {k: v for k, v in news_data.get("sentiment_summary", {}).items() if v.get("is_held")}
        if held_sentiment:
            # Sort by most negative first (potential concerns)
            sorted_sentiment = sorted(held_sentiment.items(), key=lambda x: x[1].get("negative_pct", 0), reverse=True)
            for ticker, data in sorted_sentiment:
                overall = data.get("overall", "UNKNOWN")
                pos_pct = data.get("positive_pct", 0)
                neg_pct = data.get("negative_pct", 0)
                count = data.get("article_count", 0)
                emoji = "🟢" if "POSITIVE" in overall else ("🔴" if "NEGATIVE" in overall else "⚪")
                briefing_lines.append(f"- {emoji} **{ticker}**: {overall} ({count} articles, +{pos_pct}%/-{neg_pct}%)")
        else:
            briefing_lines.append("- No overnight news for held positions")
        briefing_lines.append("")

        # Trading recommendations section
        briefing_lines.append("## 🎯 Pre-Market Considerations")
        briefing_lines.append("")

        recommendations = []

        # Flag very negative sentiment on held positions
        for ticker, data in held_sentiment.items():
            if data.get("negative_pct", 0) > 60:
                recommendations.append(f"- **REVIEW {ticker}**: High negative sentiment ({data['negative_pct']}% negative)")

        # Flag upcoming earnings on held positions
        for event in calendar_data.get("upcoming_earnings", []):
            if event.get("is_held") and event.get("days_until", 999) <= 3:
                recommendations.append(f"- **EARNINGS ALERT {event['ticker']}**: Reporting in {event['days_until']} days - consider position sizing")

        # Flag breaking news on held positions
        for news in news_data.get("breaking_news", []):
            if news.get("is_held") and news.get("sentiment") == "negative":
                recommendations.append(f"- **BREAKING {news['ticker']}**: Negative breaking news - monitor closely")

        if recommendations:
            briefing_lines.extend(recommendations)
        else:
            briefing_lines.append("- No immediate concerns identified overnight")

        briefing_lines.append("")
        briefing_lines.append("---")
        briefing_lines.append(f"*Generated: {datetime.now().isoformat()}*")

        briefing = "\n".join(briefing_lines)

        # Save briefing
        with open(self.morning_briefing_file, 'w', encoding='utf-8') as f:
            f.write(briefing)

        logger.info(f"[PRE-MARKET BRIEFING] Saved to {self.morning_briefing_file}")

        return briefing

    def get_premarket_agent_prompt(self) -> str:
        """
        Generate a prompt for the strategy agent based on overnight developments.
        Used to invoke the agent for pre-market trading decisions.
        """
        # Generate fresh briefing
        briefing = self.generate_premarket_briefing()

        # Load the data files
        try:
            with open(self.overnight_news_file, 'r') as f:
                news_data = json.load(f)
        except:
            news_data = {}

        try:
            with open(self.events_calendar_file, 'r') as f:
                calendar_data = json.load(f)
        except:
            calendar_data = {}

        # Build agent prompt
        prompt = f"""PRE-MARKET STRATEGY REVIEW - Overnight Developments

The overnight scanner has completed. Review the briefing and take appropriate action.

## Overnight Summary
- Breaking news items: {len(news_data.get('breaking_news', []))}
- Analyst upgrades/downgrades: {len(news_data.get('upgrades_downgrades', []))}
- Earnings-related news: {len(news_data.get('earnings_related', []))}
- Upcoming earnings (14 days): {len(calendar_data.get('upcoming_earnings', []))}

## Full Briefing
{briefing}

## Your Task
1. Review the overnight developments for held positions
2. Identify any positions that need adjustment based on:
   - Breaking news (especially negative for held positions)
   - Analyst downgrades on held positions
   - Earnings within 1-3 days (consider risk management)
   - Significant sentiment shifts
3. Identify watchlist opportunities from positive overnight news
4. Execute appropriate trades via the MCP tools

IMPORTANT:
- This is a PRE-MARKET review - market opens soon
- Prioritize risk management on held positions with negative news
- Check overnight_news.json and events_calendar.json for full details
- Reference morning_briefing.md for formatted summary
"""

        return prompt

    def scan_weekend_news(self) -> Dict:
        """
        Scan news with extended 72-hour lookback for weekend coverage.
        Covers Friday evening through Sunday for Monday preparation.
        """
        logger.info("[WEEKEND SCAN] Starting extended weekend news scan (72 hours)...")

        held_tickers = self.get_held_tickers()
        all_tickers = list(set(held_tickers + self.watchlist))

        results = {
            "scan_time": datetime.now().isoformat(),
            "scan_type": "weekend",
            "lookback_hours": 72,
            "held_positions": held_tickers,
            "watchlist_scanned": self.watchlist,
            "breaking_news": [],
            "upgrades_downgrades": [],
            "earnings_related": [],
            "general_news": [],
            "sentiment_summary": {}
        }

        for ticker in all_tickers:
            try:
                # Extended 3-day lookback for weekend
                news_data = get_news_sentiment(ticker, days=3)

                if "error" in news_data:
                    continue

                results["sentiment_summary"][ticker] = {
                    "overall": news_data.get("overall_sentiment", "UNKNOWN"),
                    "positive_pct": news_data.get("sentiment_breakdown", {}).get("positive_pct", 0),
                    "negative_pct": news_data.get("sentiment_breakdown", {}).get("negative_pct", 0),
                    "article_count": news_data.get("articles_analyzed", 0),
                    "is_held": ticker in held_tickers
                }

                for article in news_data.get("articles", []):
                    title_lower = article.get("title", "").lower()
                    article_data = {"ticker": ticker, "is_held": ticker in held_tickers, **article}

                    breaking_keywords = ['breaking', 'urgent', 'alert', 'crash', 'surge',
                                        'plunge', 'halted', 'investigation', 'sec', 'fda',
                                        'recall', 'bankruptcy', 'merger', 'acquisition']
                    if any(kw in title_lower for kw in breaking_keywords):
                        article_data["urgency"] = "HIGH"
                        results["breaking_news"].append(article_data)
                        continue

                    analyst_keywords = ['upgrade', 'downgrade', 'price target', 'rating',
                                       'buy rating', 'sell rating', 'hold rating', 'outperform',
                                       'underperform', 'overweight', 'underweight']
                    if any(kw in title_lower for kw in analyst_keywords):
                        results["upgrades_downgrades"].append(article_data)
                        continue

                    earnings_keywords = ['earnings', 'revenue', 'guidance', 'forecast',
                                        'quarterly', 'q1', 'q2', 'q3', 'q4', 'beat', 'miss',
                                        'eps', 'profit', 'loss']
                    if any(kw in title_lower for kw in earnings_keywords):
                        results["earnings_related"].append(article_data)
                        continue

                    results["general_news"].append(article_data)

            except Exception as e:
                logger.error(f"Error scanning weekend news for {ticker}: {e}")

        # Save to weekend-specific file
        weekend_news_file = self.project_dir / 'weekend_news.json'
        with open(weekend_news_file, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"[WEEKEND SCAN] Complete - Breaking: {len(results['breaking_news'])}, "
                   f"Upgrades/Downgrades: {len(results['upgrades_downgrades'])}, "
                   f"Earnings: {len(results['earnings_related'])}")

        return results

    def generate_weekend_briefing(self) -> str:
        """
        Generate comprehensive weekend briefing for Monday morning.
        Aggregates Friday-Sunday news and events.
        """
        logger.info("[WEEKEND BRIEFING] Generating Monday preparation briefing...")

        # Get extended weekend scan
        news_data = self.scan_weekend_news()
        calendar_data = self.get_earnings_calendar()

        try:
            portfolio = self.executor.get_portfolio_summary()
            portfolio_value = portfolio.get('total_value', 0)
            cash = portfolio.get('cash', 0)
            positions = portfolio.get('positions', [])
        except:
            portfolio_value = 0
            cash = 0
            positions = []

        briefing_lines = [
            f"# Weekend Briefing - Monday {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "## Weekend Summary (Friday-Sunday Coverage)",
            "",
            "## Portfolio Snapshot (Friday Close)",
            f"- **Portfolio Value:** ${portfolio_value:,.2f}",
            f"- **Cash:** ${cash:,.2f}",
            f"- **Positions:** {len(positions)}",
            "",
        ]

        # Breaking news (extended)
        if news_data.get("breaking_news"):
            briefing_lines.append("## WEEKEND BREAKING NEWS")
            briefing_lines.append("")
            for news in news_data["breaking_news"][:10]:  # Top 10 for weekend
                held_tag = "**[HELD]**" if news.get("is_held") else "[WATCHLIST]"
                sentiment_tag = f"[{news.get('sentiment', 'unknown').upper()}]"
                briefing_lines.append(f"- {held_tag} **{news['ticker']}** {sentiment_tag}: {news.get('title', 'No title')}")
                briefing_lines.append(f"  - Source: {news.get('publisher', 'Unknown')} | {news.get('published', '')}")
            briefing_lines.append("")

        # Analyst actions (weekend aggregate)
        if news_data.get("upgrades_downgrades"):
            briefing_lines.append("## WEEKEND ANALYST ACTIONS")
            briefing_lines.append("")
            for news in news_data["upgrades_downgrades"][:10]:
                held_tag = "**[HELD]**" if news.get("is_held") else "[WATCHLIST]"
                briefing_lines.append(f"- {held_tag} **{news['ticker']}**: {news.get('title', 'No title')}")
            briefing_lines.append("")

        # Earnings this week
        if calendar_data.get("upcoming_earnings"):
            briefing_lines.append("## THIS WEEK'S EARNINGS")
            briefing_lines.append("")
            for event in calendar_data["upcoming_earnings"][:15]:
                held_tag = "**[HELD]**" if event.get("is_held") else "[WATCHLIST]"
                days = event.get("days_until", "?")
                if days <= 5:  # This week
                    urgency = "**TODAY**" if days == 0 else (f"in {days} days")
                    briefing_lines.append(f"- {held_tag} **{event['ticker']}**: {event.get('earnings_date', 'TBD')} ({urgency})")
            briefing_lines.append("")

        # Weekend sentiment summary
        briefing_lines.append("## WEEKEND SENTIMENT SUMMARY (Held Positions)")
        briefing_lines.append("")
        held_sentiment = {k: v for k, v in news_data.get("sentiment_summary", {}).items() if v.get("is_held")}
        if held_sentiment:
            sorted_sentiment = sorted(held_sentiment.items(), key=lambda x: x[1].get("negative_pct", 0), reverse=True)
            for ticker, data in sorted_sentiment:
                overall = data.get("overall", "UNKNOWN")
                pos_pct = data.get("positive_pct", 0)
                neg_pct = data.get("negative_pct", 0)
                count = data.get("article_count", 0)
                emoji = "[+]" if "POSITIVE" in overall else ("[-]" if "NEGATIVE" in overall else "[=]")
                briefing_lines.append(f"- {emoji} **{ticker}**: {overall} ({count} articles, +{pos_pct}%/-{neg_pct}%)")
        else:
            briefing_lines.append("- No weekend news for held positions")
        briefing_lines.append("")

        # Monday action items
        briefing_lines.append("## MONDAY ACTION ITEMS")
        briefing_lines.append("")

        action_items = []

        # Flag negative sentiment
        for ticker, data in held_sentiment.items():
            if data.get("negative_pct", 0) > 50:
                action_items.append(f"- **REVIEW {ticker}**: High negative weekend sentiment ({data['negative_pct']}%)")

        # Flag earnings this week
        for event in calendar_data.get("upcoming_earnings", []):
            if event.get("is_held") and event.get("days_until", 999) <= 5:
                action_items.append(f"- **EARNINGS {event['ticker']}**: Reports in {event['days_until']} days - review position size")

        # Flag breaking news on held
        for news in news_data.get("breaking_news", []):
            if news.get("is_held") and news.get("sentiment") == "negative":
                action_items.append(f"- **ALERT {news['ticker']}**: Negative breaking news over weekend")

        if action_items:
            briefing_lines.extend(action_items)
        else:
            briefing_lines.append("- No immediate concerns from weekend news")
            briefing_lines.append("- Standard Monday open - follow regular strategy")

        briefing_lines.append("")
        briefing_lines.append("---")
        briefing_lines.append(f"*Generated: {datetime.now().isoformat()}*")

        briefing = "\n".join(briefing_lines)

        # Save to weekend briefing file
        weekend_briefing_file = self.project_dir / 'weekend_briefing.md'
        with open(weekend_briefing_file, 'w', encoding='utf-8') as f:
            f.write(briefing)

        logger.info(f"[WEEKEND BRIEFING] Saved to {weekend_briefing_file}")

        return briefing

    def get_weekend_agent_prompt(self) -> str:
        """
        Generate prompt for Monday morning strategy agent with weekend context.
        """
        briefing = self.generate_weekend_briefing()

        try:
            with open(self.project_dir / 'weekend_news.json', 'r') as f:
                news_data = json.load(f)
        except:
            news_data = {}

        try:
            with open(self.events_calendar_file, 'r') as f:
                calendar_data = json.load(f)
        except:
            calendar_data = {}

        prompt = f"""MONDAY MORNING STRATEGY REVIEW - Weekend Developments

This is the MONDAY OPEN review after the weekend. Markets have been closed since Friday.
Review the comprehensive weekend briefing and prepare for the week ahead.

## Weekend Summary (72-hour coverage)
- Breaking news items: {len(news_data.get('breaking_news', []))}
- Analyst upgrades/downgrades: {len(news_data.get('upgrades_downgrades', []))}
- Earnings-related news: {len(news_data.get('earnings_related', []))}
- Earnings this week: {len([e for e in calendar_data.get('upcoming_earnings', []) if e.get('days_until', 999) <= 5])}

## Full Weekend Briefing
{briefing}

## Your Monday Tasks
1. Review ALL weekend developments for held positions
2. Check for any breaking news that requires immediate action at open
3. Review earnings calendar - adjust positions for imminent reports
4. Identify any watchlist opportunities from positive weekend news
5. Set the week's strategic priorities based on:
   - Earnings reports scheduled
   - Analyst rating changes
   - Sector trends from weekend news
6. Execute appropriate trades via the MCP tools

IMPORTANT:
- This is MONDAY OPEN - first chance to react to 3 days of news
- Prioritize: (1) Risk management, (2) Earnings positioning, (3) New opportunities
- Check weekend_news.json and weekend_briefing.md for full details
"""

        return prompt


if __name__ == "__main__":
    # Test the overnight scanner
    logging.basicConfig(level=logging.INFO)

    print("Testing Overnight Scanner\n")

    scanner = OvernightScanner()

    print("1. Scanning overnight news...")
    news = scanner.scan_overnight_news()
    print(f"   Found {len(news.get('breaking_news', []))} breaking news items")

    print("\n2. Getting earnings calendar...")
    calendar = scanner.get_earnings_calendar()
    print(f"   Found {len(calendar.get('upcoming_earnings', []))} upcoming earnings")

    print("\n3. Generating pre-market briefing...")
    briefing = scanner.generate_premarket_briefing()
    print(briefing)
