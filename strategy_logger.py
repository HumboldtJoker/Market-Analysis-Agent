"""
Strategy Review Logger

Logs all Strategy Agent analysis and decision-making for audit trail
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class StrategyReviewLogger:
    """Logs Strategy Agent reviews and decisions"""

    def __init__(self, review_dir: str = "strategy_reviews"):
        """
        Initialize logger

        Args:
            review_dir: Directory to save review logs
        """
        self.review_dir = Path(review_dir)
        self.review_dir.mkdir(exist_ok=True)

    def log_review(self,
                   trigger: str,
                   market_analysis: Dict,
                   portfolio_state: Dict,
                   decision: str,
                   reasoning: str,
                   instructions_created: bool = False,
                   instructions_file: Optional[str] = None,
                   metadata: Optional[Dict] = None) -> str:
        """
        Log a complete strategy review

        Args:
            trigger: What triggered this review (e.g., "scheduled_4hour", "vix_regime_change", "manual")
            market_analysis: Market conditions at time of review
            portfolio_state: Portfolio state at time of review
            decision: Summary of decision made
            reasoning: Detailed reasoning
            instructions_created: Whether trading instructions were created
            instructions_file: Path to instructions file if created
            metadata: Additional metadata

        Returns:
            Path to saved log file
        """
        timestamp = datetime.now()
        timestamp_str = timestamp.isoformat()

        review_log = {
            "timestamp": timestamp_str,
            "trigger": trigger,
            "market_analysis": market_analysis,
            "portfolio_state": portfolio_state,
            "decision": decision,
            "reasoning": reasoning,
            "instructions_created": instructions_created,
            "instructions_file": instructions_file,
            "metadata": metadata or {}
        }

        # Create filename with timestamp
        filename_timestamp = timestamp_str.replace(":", "-").replace(".", "-")
        filename = self.review_dir / f"review_{filename_timestamp}.json"

        # Save to file
        with open(filename, 'w') as f:
            json.dump(review_log, f, indent=2)

        return str(filename)

    def log_execution_result(self,
                            instructions_file: str,
                            execution_summary: Dict,
                            final_portfolio: Dict,
                            errors: Optional[list] = None) -> str:
        """
        Log execution results for a set of instructions

        Args:
            instructions_file: Path to instructions that were executed
            execution_summary: Summary of execution results
            final_portfolio: Portfolio state after execution
            errors: Any errors encountered

        Returns:
            Path to saved log file
        """
        timestamp = datetime.now()
        timestamp_str = timestamp.isoformat()

        result_log = {
            "timestamp": timestamp_str,
            "instructions_file": instructions_file,
            "execution_summary": execution_summary,
            "final_portfolio": final_portfolio,
            "errors": errors or []
        }

        # Create filename
        filename_timestamp = timestamp_str.replace(":", "-").replace(".", "-")
        filename = Path("execution_results") / f"result_{filename_timestamp}.json"
        filename.parent.mkdir(exist_ok=True)

        # Save to file
        with open(filename, 'w') as f:
            json.dump(result_log, f, indent=2)

        return str(filename)

    def get_recent_reviews(self, limit: int = 10) -> list:
        """
        Get most recent review logs

        Args:
            limit: Maximum number of reviews to return

        Returns:
            List of review log dictionaries, most recent first
        """
        review_files = sorted(self.review_dir.glob("review_*.json"), reverse=True)
        reviews = []

        for review_file in review_files[:limit]:
            try:
                with open(review_file, 'r') as f:
                    reviews.append(json.load(f))
            except Exception as e:
                print(f"Error loading {review_file}: {e}")

        return reviews

    def summary(self, days: int = 7) -> str:
        """
        Generate summary of recent strategy reviews

        Args:
            days: Number of days to summarize

        Returns:
            Human-readable summary
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)
        recent_reviews = []

        for review_file in self.review_dir.glob("review_*.json"):
            try:
                with open(review_file, 'r') as f:
                    review = json.load(f)
                    review_time = datetime.fromisoformat(review["timestamp"])
                    if review_time >= cutoff:
                        recent_reviews.append(review)
            except Exception:
                continue

        # Sort by timestamp
        recent_reviews.sort(key=lambda x: x["timestamp"], reverse=True)

        # Generate summary
        lines = [
            f"Strategy Review Summary (Last {days} days)",
            "=" * 60,
            f"Total Reviews: {len(recent_reviews)}",
            ""
        ]

        for review in recent_reviews:
            lines.append(f"[{review['timestamp']}] {review['trigger']}")
            lines.append(f"  Decision: {review['decision']}")
            if review['instructions_created']:
                lines.append(f"  Instructions: {review['instructions_file']}")
            lines.append("")

        return "\n".join(lines)


# Example usage
if __name__ == "__main__":
    logger = StrategyReviewLogger()

    # Example: Log a review
    log_file = logger.log_review(
        trigger="scheduled_4hour",
        market_analysis={
            "vix": 15.98,
            "regime": "BULLISH",
            "spy_change": 0.5
        },
        portfolio_state={
            "total_value": 99823.03,
            "cash": 99823.03,
            "positions": 0
        },
        decision="Deploy aggressive $200k momentum strategy",
        reasoning="Market conditions bullish, VIX calm, technical setups strong",
        instructions_created=True,
        instructions_file="trading_instructions.json"
    )

    print(f"Logged review to: {log_file}")

    # Example: Get summary
    print("\n" + logger.summary(days=7))
