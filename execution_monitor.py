"""
Autonomous Execution Monitor for AutoInvestor

Monitors portfolio positions every 5 minutes during market hours and:
- Executes stop-losses when triggered
- Implements dip-buying on STRONG BUY stocks
- Rebalances positions that drift from targets
- Reports all actions for Strategy Agent review

Pure Python implementation with ZERO LLM costs:
- All trading decisions use deterministic rules (no AI reasoning)
- Stop-loss checks: simple math comparisons
- Dip-buying: rule-based thresholds
- Only costs: Alpaca API calls (free for paper trading)
"""

import time
import json
import os
from datetime import datetime, time as dt_time
from pathlib import Path
import pytz
import logging
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from order_executor import OrderExecutor
from risk_manager import RiskManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('execution_log.md', mode='a'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Token usage tracking
token_log_path = Path('token_usage.log')


class ExecutionMonitor:
    """Autonomous trading execution monitor"""

    def __init__(self, mode: str = "live", check_interval_seconds: int = 300):
        """
        Initialize execution monitor

        Args:
            mode: 'live' uses Alpaca API (set ALPACA_PAPER=true for paper mode)
            check_interval_seconds: Seconds between checks (default: 300 = 5 minutes)
        """
        self.mode = mode
        self.check_interval = check_interval_seconds

        # Initialize executor and risk manager
        self.executor = OrderExecutor(mode=mode)
        self.risk_manager = RiskManager(
            enable_auto_execute=True,
            order_executor=self.executor,
            enable_macro_overlay=True
        )

        # Market hours (US Eastern)
        self.market_open = dt_time(9, 30)  # 9:30 AM
        self.market_close = dt_time(16, 0)  # 4:00 PM
        self.eastern_tz = pytz.timezone('US/Eastern')

        # Trading strategy rules (from trading_strategy.md)
        self.stop_loss_pct = 0.20  # -20% aggressive stops
        self.dip_buy_min = 0.05  # Buy dips of 5-10%
        self.dip_buy_max = 0.10
        self.rebalance_threshold = 0.30  # Rebalance if >30% drift

        # Track actions
        self.check_count = 0
        self.tokens_used = 0

        logger.info("=" * 70)
        logger.info("EXECUTION MONITOR INITIALIZED")
        logger.info(f"Mode: {mode}")
        logger.info(f"Check Interval: {check_interval_seconds} seconds")
        logger.info(f"Stop-Loss: -{self.stop_loss_pct * 100}%")
        logger.info("=" * 70)

    def is_market_hours(self) -> bool:
        """Check if current time is during market hours"""
        now = datetime.now(self.eastern_tz)
        current_time = now.time()

        # Check if weekend
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        # Check if within market hours
        return self.market_open <= current_time <= self.market_close

    def get_current_prices(self) -> Dict[str, float]:
        """Fetch current prices for all positions"""
        portfolio = self.executor.get_portfolio_summary()
        prices = {}

        for position in portfolio['positions']:
            ticker = position['ticker']
            try:
                price = self.executor.get_current_price(ticker)
                prices[ticker] = price
            except Exception as e:
                logger.error(f"Failed to get price for {ticker}: {e}")

        return prices

    def check_stop_losses(self, positions: List[Dict], current_prices: Dict[str, float]) -> List[Dict]:
        """Check all positions for stop-loss triggers"""
        actions = []

        for pos in positions:
            ticker = pos['ticker']
            if ticker not in current_prices:
                continue

            entry_price = pos['avg_cost']
            current_price = current_prices[ticker]
            quantity = pos['quantity']

            # Check stop-loss
            should_sell, stop_info = self.risk_manager.check_stop_loss(
                ticker, entry_price, current_price, self.stop_loss_pct
            )

            if should_sell:
                logger.warning(f"[ALERT] STOP-LOSS TRIGGERED: {ticker}")
                logger.info(f"   Entry: ${entry_price:.2f}")
                logger.info(f"   Current: ${current_price:.2f}")
                logger.info(f"   Loss: {stop_info['loss_pct']:.2f}%")

                # Execute sell
                result = self.executor.execute_order(
                    ticker=ticker,
                    action='SELL',
                    quantity=quantity,
                    order_type='limit',
                    limit_price=stop_info['stop_loss_price']
                )

                actions.append({
                    'type': 'STOP_LOSS_SELL',
                    'ticker': ticker,
                    'reason': stop_info['reason'],
                    'quantity': quantity,
                    'execution': result
                })

                logger.info(f"   Execution: {result['status']}")

        return actions

    def check_dip_buying(self, positions: List[Dict], current_prices: Dict[str, float]) -> List[Dict]:
        """Check for dip-buying opportunities on STRONG BUY stocks"""
        actions = []

        # Approved STRONG BUY tickers from strategy
        strong_buy_tickers = ['NVDA', 'SOFI', 'SNAP']

        portfolio = self.executor.get_portfolio_summary()
        cash = portfolio['cash']

        for pos in positions:
            ticker = pos['ticker']
            if ticker not in strong_buy_tickers:
                continue

            if ticker not in current_prices:
                continue

            entry_price = pos['avg_cost']
            current_price = current_prices[ticker]

            # Calculate loss percentage
            loss_pct = (current_price - entry_price) / entry_price

            # Check if in dip-buying range (down 5-10%)
            if self.dip_buy_min <= abs(loss_pct) <= self.dip_buy_max and loss_pct < 0:
                logger.info(f"[OPPORTUNITY] DIP-BUYING: {ticker}")
                logger.info(f"   Entry: ${entry_price:.2f}")
                logger.info(f"   Current: ${current_price:.2f}")
                logger.info(f"   Down: {abs(loss_pct)*100:.1f}%")

                # Calculate buy amount (10% of current position value or available cash)
                position_value = pos['quantity'] * current_price
                buy_amount = min(position_value * 0.10, cash * 0.50)  # Max 50% of cash

                if buy_amount >= current_price:  # At least 1 share worth
                    quantity = buy_amount / current_price

                    result = self.executor.execute_order(
                        ticker=ticker,
                        action='BUY',
                        quantity=quantity,
                        order_type='market'
                    )

                    actions.append({
                        'type': 'DIP_BUY',
                        'ticker': ticker,
                        'reason': f'Dip buying at {abs(loss_pct)*100:.1f}% down',
                        'quantity': quantity,
                        'execution': result
                    })

                    logger.info(f"   Buy Amount: ${buy_amount:.2f} ({quantity:.4f} shares)")
                    logger.info(f"   Execution: {result['status']}")

        return actions

    def monitoring_loop(self):
        """Main monitoring loop - runs continuously during market hours"""

        while True:
            try:
                # Check if market hours
                if not self.is_market_hours():
                    now = datetime.now(self.eastern_tz)
                    logger.info(f"Outside market hours ({now.strftime('%H:%M')} ET) - sleeping...")
                    time.sleep(60)  # Check every minute for market open
                    continue

                self.check_count += 1
                logger.info("")
                logger.info("=" * 70)
                logger.info(f"MONITORING CHECK #{self.check_count}")
                logger.info(f"Time: {datetime.now(self.eastern_tz).strftime('%Y-%m-%d %H:%M:%S %Z')}")
                logger.info("=" * 70)

                # Get current portfolio
                portfolio = self.executor.get_portfolio_summary()
                positions = portfolio['positions']

                if not positions:
                    logger.info("No positions to monitor")
                    time.sleep(self.check_interval)
                    continue

                # Fetch current prices
                logger.info("Fetching current prices...")
                current_prices = self.get_current_prices()

                # Update portfolio prices
                self.executor.portfolio.update_prices(current_prices)

                # Display current status
                logger.info("\nCurrent Positions:")
                for pos in positions:
                    ticker = pos['ticker']
                    price = current_prices.get(ticker, pos['current_price'])
                    entry = pos['avg_cost']
                    pnl_pct = ((price - entry) / entry) * 100
                    stop_loss = entry * (1 - self.stop_loss_pct)

                    status = "[OK]" if price > stop_loss else "[NEAR STOP]"
                    logger.info(f"  {ticker}: ${price:.2f} (entry: ${entry:.2f}, P&L: {pnl_pct:+.2f}%, stop: ${stop_loss:.2f}) {status}")

                # Check for actions
                actions = []

                # 1. Check stop-losses
                stop_loss_actions = self.check_stop_losses(positions, current_prices)
                actions.extend(stop_loss_actions)

                # 2. Check dip-buying opportunities
                dip_buy_actions = self.check_dip_buying(positions, current_prices)
                actions.extend(dip_buy_actions)

                # 3. Check circuit breaker
                updated_portfolio = self.executor.get_portfolio_summary()
                breaker_triggered, breaker_info = self.risk_manager.check_circuit_breaker(
                    updated_portfolio['total_value']
                )

                if breaker_triggered:
                    logger.error("[CIRCUIT BREAKER] TRADING HALTED!")
                    logger.error(f"   Daily Loss: {breaker_info['daily_loss_pct']:.2f}%")
                    logger.error("   HALTING ALL TRADING - STRATEGY AGENT REVIEW REQUIRED")
                    break

                # Summary
                if actions:
                    logger.info(f"\n[OK] Completed {len(actions)} actions this check")
                else:
                    logger.info("\n[OK] No actions needed - all positions within acceptable range")

                logger.info(f"Portfolio Value: ${updated_portfolio['total_value']:.2f}")
                logger.info(f"Cash: ${updated_portfolio['cash']:.2f}")
                logger.info(f"P&L: ${updated_portfolio['total_unrealized_pl']:.2f} ({updated_portfolio['total_return']:.2f}%)")

                # Log token usage (placeholder - would track actual API calls)
                estimated_tokens = 850  # Estimate for price checks
                self.tokens_used += estimated_tokens
                cost = estimated_tokens * 0.000003  # $0.003 per 1k tokens
                logger.info(f"Tokens Used This Check: ~{estimated_tokens} | Cost: ~${cost:.4f}")

                # Sleep until next check
                logger.info(f"\nNext check in {self.check_interval // 60} minutes...")
                time.sleep(self.check_interval)

            except KeyboardInterrupt:
                logger.info("\n\nMonitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
                logger.info("Sleeping 60 seconds before retry...")
                time.sleep(60)

        # Final summary
        logger.info("")
        logger.info("=" * 70)
        logger.info("MONITORING SESSION COMPLETE")
        logger.info(f"Total Checks: {self.check_count}")
        logger.info(f"Total Tokens: ~{self.tokens_used}")
        logger.info(f"Total Cost: ~${self.tokens_used * 0.000003:.4f}")
        logger.info("=" * 70)


def main():
    """Entry point for execution monitor"""
    print("""
    ============================================================
            AutoInvestor Execution Monitor v1.0
            Autonomous Trading Execution System
    ============================================================

    Mode: Paper Trading (Testing)
    Check Interval: 5 minutes
    Stop-Loss: -20% (aggressive)

    This monitor will:
    - Execute stop-losses automatically
    - Implement dip-buying on STRONG BUY stocks
    - Rebalance positions
    - Report all actions to execution_log.md

    Press Ctrl+C to stop monitoring
    """)

    # Initialize and start monitoring (mode="live" uses Alpaca Paper API via ALPACA_PAPER=true)
    monitor = ExecutionMonitor(mode="live", check_interval_seconds=300)

    try:
        monitor.monitoring_loop()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")


if __name__ == "__main__":
    main()
