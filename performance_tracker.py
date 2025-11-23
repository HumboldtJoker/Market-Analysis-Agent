"""
Performance Tracker for AutoInvestor

Tracks portfolio performance, calculates metrics, and benchmarks against market.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import yfinance as yf
import numpy as np


class PerformanceTracker:
    """
    Track and analyze portfolio performance

    Metrics:
    - Total return, daily/weekly/monthly returns
    - Sharpe ratio
    - Maximum drawdown
    - Win rate and average win/loss
    - Benchmark comparison (vs S&P 500)
    """

    def __init__(self, initial_value: float, benchmark_ticker: str = "SPY"):
        """
        Initialize performance tracker

        Args:
            initial_value: Starting portfolio value
            benchmark_ticker: Ticker for benchmark comparison (default: SPY for S&P 500)
        """
        self.initial_value = initial_value
        self.benchmark_ticker = benchmark_ticker

        # Track daily portfolio values
        self.daily_values = [(datetime.now().isoformat(), initial_value)]

        # Track individual trades for win/loss analysis
        self.closed_trades = []

    def record_value(self, portfolio_value: float, timestamp: Optional[str] = None) -> None:
        """
        Record portfolio value at a point in time

        Args:
            portfolio_value: Current total portfolio value
            timestamp: Optional timestamp (defaults to now)
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        self.daily_values.append((timestamp, portfolio_value))

    def record_closed_trade(self, ticker: str, entry_price: float, exit_price: float,
                           quantity: int, hold_days: int) -> None:
        """
        Record a closed trade for win/loss analysis

        Args:
            ticker: Stock symbol
            entry_price: Average entry price
            exit_price: Exit price
            quantity: Number of shares
            hold_days: Days held
        """
        pl = (exit_price - entry_price) * quantity
        pl_pct = ((exit_price - entry_price) / entry_price) * 100

        self.closed_trades.append({
            "ticker": ticker,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "quantity": quantity,
            "pl": pl,
            "pl_pct": pl_pct,
            "hold_days": hold_days,
            "winner": pl > 0
        })

    def get_total_return(self) -> Dict:
        """Calculate total return since inception"""
        if not self.daily_values:
            return {"total_return": 0.0, "total_return_pct": 0.0}

        current_value = self.daily_values[-1][1]
        total_return = current_value - self.initial_value
        total_return_pct = (total_return / self.initial_value) * 100 if self.initial_value > 0 else 0

        return {
            "initial_value": round(self.initial_value, 2),
            "current_value": round(current_value, 2),
            "total_return": round(total_return, 2),
            "total_return_pct": round(total_return_pct, 2)
        }

    def get_returns_by_period(self) -> Dict:
        """Calculate returns over different time periods"""
        if len(self.daily_values) < 2:
            return {}

        current_value = self.daily_values[-1][1]

        # Calculate returns for different periods
        periods = {
            "1_day": 1,
            "1_week": 7,
            "1_month": 30,
            "3_months": 90
        }

        results = {}

        for period_name, days_back in periods.items():
            # Find value from N days ago
            target_date = datetime.now() - timedelta(days=days_back)

            # Find closest historical value
            closest_value = None
            for timestamp_str, value in self.daily_values:
                timestamp = datetime.fromisoformat(timestamp_str)
                if timestamp <= target_date:
                    closest_value = value
                else:
                    break

            if closest_value:
                period_return = current_value - closest_value
                period_return_pct = (period_return / closest_value) * 100 if closest_value > 0 else 0

                results[period_name] = {
                    "return": round(period_return, 2),
                    "return_pct": round(period_return_pct, 2)
                }

        return results

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.04) -> float:
        """
        Calculate Sharpe ratio

        Args:
            risk_free_rate: Annual risk-free rate (default 4%)

        Returns:
            Sharpe ratio
        """
        if len(self.daily_values) < 2:
            return 0.0

        # Calculate daily returns
        returns = []
        for i in range(1, len(self.daily_values)):
            prev_value = self.daily_values[i-1][1]
            curr_value = self.daily_values[i][1]
            daily_return = (curr_value - prev_value) / prev_value if prev_value > 0 else 0
            returns.append(daily_return)

        if not returns:
            return 0.0

        # Calculate mean and std of returns
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return 0.0

        # Annualize (assuming 252 trading days)
        daily_rf_rate = risk_free_rate / 252
        sharpe = (mean_return - daily_rf_rate) / std_return
        sharpe_annualized = sharpe * np.sqrt(252)

        return round(sharpe_annualized, 2)

    def calculate_max_drawdown(self) -> Dict:
        """
        Calculate maximum drawdown

        Returns:
            Dict with max drawdown percentage and details
        """
        if len(self.daily_values) < 2:
            return {"max_drawdown_pct": 0.0, "peak_value": 0.0, "trough_value": 0.0}

        values = [v[1] for v in self.daily_values]

        peak = values[0]
        max_drawdown = 0.0
        peak_value = peak
        trough_value = peak

        for value in values:
            if value > peak:
                peak = value

            drawdown = (peak - value) / peak if peak > 0 else 0

            if drawdown > max_drawdown:
                max_drawdown = drawdown
                peak_value = peak
                trough_value = value

        max_drawdown_pct = max_drawdown * 100

        return {
            "max_drawdown_pct": round(max_drawdown_pct, 2),
            "peak_value": round(peak_value, 2),
            "trough_value": round(trough_value, 2),
            "drawdown_amount": round(peak_value - trough_value, 2)
        }

    def get_trade_statistics(self) -> Dict:
        """
        Calculate win rate and trade statistics

        Returns:
            Dict with win rate, avg win, avg loss, profit factor
        """
        if not self.closed_trades:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0
            }

        winners = [t for t in self.closed_trades if t["winner"]]
        losers = [t for t in self.closed_trades if not t["winner"]]

        avg_win = np.mean([t["pl"] for t in winners]) if winners else 0
        avg_loss = np.mean([t["pl"] for t in losers]) if losers else 0

        total_wins = sum(t["pl"] for t in winners)
        total_losses = abs(sum(t["pl"] for t in losers))

        profit_factor = total_wins / total_losses if total_losses > 0 else 0

        win_rate = (len(winners) / len(self.closed_trades)) * 100 if self.closed_trades else 0

        return {
            "total_trades": len(self.closed_trades),
            "winning_trades": len(winners),
            "losing_trades": len(losers),
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "total_profit": round(sum(t["pl"] for t in self.closed_trades), 2)
        }

    def compare_to_benchmark(self, days_back: int = 30) -> Dict:
        """
        Compare portfolio performance to benchmark

        Args:
            days_back: Number of days to compare

        Returns:
            Dict with portfolio vs benchmark performance
        """
        if len(self.daily_values) < 2:
            return {}

        # Get portfolio performance
        current_value = self.daily_values[-1][1]

        # Find value from N days ago
        target_date = datetime.now() - timedelta(days=days_back)
        start_value = self.initial_value

        for timestamp_str, value in self.daily_values:
            timestamp = datetime.fromisoformat(timestamp_str)
            if timestamp >= target_date:
                start_value = value
                break

        portfolio_return_pct = ((current_value - start_value) / start_value) * 100 if start_value > 0 else 0

        # Get benchmark performance
        try:
            benchmark = yf.Ticker(self.benchmark_ticker)
            hist = benchmark.history(period=f"{days_back}d")

            if not hist.empty and len(hist) >= 2:
                benchmark_start = hist['Close'].iloc[0]
                benchmark_end = hist['Close'].iloc[-1]
                benchmark_return_pct = ((benchmark_end - benchmark_start) / benchmark_start) * 100

                alpha = portfolio_return_pct - benchmark_return_pct

                return {
                    "period_days": days_back,
                    "portfolio_return_pct": round(portfolio_return_pct, 2),
                    "benchmark_return_pct": round(benchmark_return_pct, 2),
                    "alpha": round(alpha, 2),
                    "benchmark_ticker": self.benchmark_ticker,
                    "outperforming": bool(alpha > 0)
                }
        except Exception as e:
            print(f"Warning: Could not fetch benchmark data: {e}")

        return {
            "period_days": days_back,
            "portfolio_return_pct": round(portfolio_return_pct, 2),
            "benchmark_return_pct": None,
            "alpha": None,
            "error": "Could not fetch benchmark data"
        }

    def get_performance_summary(self) -> Dict:
        """
        Get comprehensive performance summary

        Returns:
            Dict with all performance metrics
        """
        total_return = self.get_total_return()
        sharpe = self.calculate_sharpe_ratio()
        max_dd = self.calculate_max_drawdown()
        trade_stats = self.get_trade_statistics()
        benchmark_30d = self.compare_to_benchmark(30)

        return {
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "trade_statistics": trade_stats,
            "benchmark_comparison_30d": benchmark_30d,
            "num_data_points": len(self.daily_values)
        }

    def save_state(self, filepath: str = "performance_history.json") -> None:
        """Save performance tracking data to file"""
        state = {
            "initial_value": self.initial_value,
            "benchmark_ticker": self.benchmark_ticker,
            "daily_values": self.daily_values,
            "closed_trades": self.closed_trades
        }

        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)

    def load_state(self, filepath: str = "performance_history.json") -> None:
        """Load performance tracking data from file"""
        with open(filepath, 'r') as f:
            state = json.load(f)

        self.initial_value = state['initial_value']
        self.benchmark_ticker = state['benchmark_ticker']
        self.daily_values = state['daily_values']
        self.closed_trades = state['closed_trades']


if __name__ == "__main__":
    # Quick test
    print("Testing PerformanceTracker...")

    # Create tracker
    tracker = PerformanceTracker(initial_value=100000)

    print("\n1. Initial State:")
    print(tracker.get_performance_summary())

    # Simulate some performance
    print("\n2. Simulating portfolio growth...")
    tracker.record_value(102000)  # +2%
    tracker.record_value(104000)  # +4%
    tracker.record_value(103000)  # +3% (drawdown from peak)
    tracker.record_value(106000)  # +6%

    # Record some trades
    tracker.record_closed_trade("AAPL", 150, 165, 100, 10)  # Winner: +$1500
    tracker.record_closed_trade("NVDA", 500, 480, 50, 5)    # Loser: -$1000
    tracker.record_closed_trade("MSFT", 350, 370, 50, 7)    # Winner: +$1000

    print("\n3. Performance Summary:")
    summary = tracker.get_performance_summary()
    print(json.dumps(summary, indent=2))

    print("\n4. Trade Statistics:")
    print(json.dumps(tracker.get_trade_statistics(), indent=2))

    print("\n5. Max Drawdown:")
    print(json.dumps(tracker.calculate_max_drawdown(), indent=2))

    print("\n6. Sharpe Ratio:")
    print(f"Sharpe Ratio: {tracker.calculate_sharpe_ratio()}")
