"""
Risk Manager for AutoInvestor

Handles position sizing, stop-losses, and circuit breakers to protect capital.
Supports automated stop-loss execution with comprehensive safety mechanisms.
"""

from typing import Dict, Optional, Tuple, List
from investor_profile import InvestorProfile
import time
from datetime import datetime, time as dt_time
import pytz
import logging


class RiskManager:
    """
    Manages trading risk through position sizing, stop-losses, and circuit breakers

    Key Features:
    - Position sizing based on portfolio value and risk tolerance
    - Maximum position concentration limits
    - Daily loss circuit breakers
    - Stop-loss recommendations
    - Risk-adjusted order validation
    """

    def __init__(self, investor_profile: Optional[InvestorProfile] = None,
                 enable_auto_execute: bool = False,
                 order_executor=None):
        """
        Initialize risk manager

        Args:
            investor_profile: Optional investor profile for personalized risk settings
            enable_auto_execute: Enable automated stop-loss execution (default: False)
            order_executor: OrderExecutor instance for executing trades (required if enable_auto_execute=True)
        """
        self.profile = investor_profile

        # Auto-execution settings
        self.enable_auto_execute = enable_auto_execute
        self.order_executor = order_executor

        if self.enable_auto_execute and not self.order_executor:
            raise ValueError("order_executor required when enable_auto_execute=True")

        # Default risk parameters (can be overridden by investor profile)
        if investor_profile and hasattr(investor_profile, 'profile'):
            risk_tolerance = investor_profile.profile.get('risk_tolerance', 3)
            # Map risk tolerance (1-5) to max position size (5-25%)
            self.max_position_size = 0.05 + (risk_tolerance - 1) * 0.05
            # Map to daily loss limit (1-5%)
            self.daily_loss_limit = 0.01 + (risk_tolerance - 1) * 0.01
        else:
            # Conservative defaults
            self.max_position_size = 0.10  # 10% max per position
            self.daily_loss_limit = 0.02   # 2% daily loss limit

        # Hard limits (never exceed regardless of risk tolerance)
        self.absolute_max_position = 0.25  # 25% max
        self.absolute_daily_loss_limit = 0.05  # 5% max daily loss

        # Tracking
        self.daily_starting_value = None
        self.circuit_breaker_triggered = False

        # Auto-execute tracking
        self.daily_auto_sells = 0
        self.max_daily_auto_sells = 10
        self.confirmation_delay_seconds = 5
        self.auto_execute_log = []

        # Market hours (US Eastern Time)
        self.market_open = dt_time(9, 30)  # 9:30 AM
        self.market_close = dt_time(16, 0)  # 4:00 PM
        self.eastern_tz = pytz.timezone('US/Eastern')

        # Setup logging
        logging.basicConfig(level=logging.INFO,
                          format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)

    def calculate_position_size(self, portfolio_value: float,
                               ticker: str,
                               current_price: float,
                               risk_per_trade: Optional[float] = None) -> Dict:
        """
        Calculate recommended position size for a trade

        Args:
            portfolio_value: Total portfolio value
            ticker: Stock symbol
            current_price: Current stock price
            risk_per_trade: Optional risk amount per trade (defaults to 1% of portfolio)

        Returns:
            Dict with recommended shares and position details
        """
        if risk_per_trade is None:
            risk_per_trade = 0.01  # 1% default risk per trade

        # Calculate maximum dollar amount for this position
        max_position_dollars = portfolio_value * self.max_position_size

        # Calculate shares based on price
        max_shares = int(max_position_dollars / current_price)

        # Calculate position as percentage
        position_value = max_shares * current_price
        position_pct = (position_value / portfolio_value) * 100 if portfolio_value > 0 else 0

        return {
            "ticker": ticker,
            "recommended_shares": max_shares,
            "position_value": round(position_value, 2),
            "position_pct": round(position_pct, 2),
            "max_position_pct": round(self.max_position_size * 100, 2),
            "current_price": round(current_price, 2),
            "portfolio_value": round(portfolio_value, 2)
        }

    def validate_order(self, action: str, ticker: str, quantity: int,
                      price: float, portfolio_value: float,
                      current_positions: Dict, cash: float) -> Tuple[bool, Optional[str]]:
        """
        Validate if an order meets risk management criteria

        Args:
            action: 'BUY' or 'SELL'
            ticker: Stock symbol
            quantity: Number of shares
            price: Order price
            portfolio_value: Total portfolio value
            current_positions: Dict of current positions
            cash: Available cash

        Returns:
            Tuple of (is_valid: bool, rejection_reason: Optional[str])
        """
        action = action.upper()

        # Check circuit breaker
        if self.circuit_breaker_triggered:
            return False, "Circuit breaker triggered - trading halted for today"

        if action == 'BUY':
            # Calculate order value
            order_value = quantity * price

            # Check if we have enough cash
            if order_value > cash:
                return False, f"Insufficient cash: need ${order_value:.2f}, have ${cash:.2f}"

            # Check position size limits
            current_position = current_positions.get(ticker)
            if current_position:
                new_quantity = current_position.quantity + quantity
                new_position_value = new_quantity * price
            else:
                new_position_value = order_value

            position_pct = (new_position_value / portfolio_value) * 100 if portfolio_value > 0 else 0

            if position_pct > (self.max_position_size * 100):
                return False, (
                    f"Position size {position_pct:.1f}% exceeds limit of "
                    f"{self.max_position_size * 100:.1f}%"
                )

            # Check absolute max
            if position_pct > (self.absolute_max_position * 100):
                return False, (
                    f"Position size {position_pct:.1f}% exceeds absolute limit of "
                    f"{self.absolute_max_position * 100:.1f}%"
                )

            return True, None

        elif action == 'SELL':
            # Check if we have the position
            current_position = current_positions.get(ticker)
            if not current_position:
                return False, f"No position in {ticker} to sell"

            # Check if we have enough shares
            if quantity > current_position.quantity:
                return False, (
                    f"Insufficient shares: have {current_position.quantity}, "
                    f"trying to sell {quantity}"
                )

            return True, None

        else:
            return False, f"Invalid action: {action}"

    def check_stop_loss(self, ticker: str, entry_price: float,
                       current_price: float,
                       stop_loss_pct: float = 0.10) -> Tuple[bool, Dict]:
        """
        Check if a position has hit its stop-loss

        Args:
            ticker: Stock symbol
            entry_price: Average entry price
            current_price: Current market price
            stop_loss_pct: Stop-loss percentage (default 10%)

        Returns:
            Tuple of (should_sell: bool, info: Dict)
        """
        loss_pct = ((current_price - entry_price) / entry_price) * 100
        stop_loss_price = entry_price * (1 - stop_loss_pct)

        should_sell = current_price <= stop_loss_price

        return should_sell, {
            "ticker": ticker,
            "entry_price": round(entry_price, 2),
            "current_price": round(current_price, 2),
            "loss_pct": round(loss_pct, 2),
            "stop_loss_price": round(stop_loss_price, 2),
            "stop_loss_pct": round(stop_loss_pct * 100, 2),
            "should_sell": should_sell,
            "reason": "Stop-loss triggered" if should_sell else "Within acceptable range"
        }

    def check_circuit_breaker(self, current_portfolio_value: float) -> Tuple[bool, Dict]:
        """
        Check if daily loss limit has been breached

        Args:
            current_portfolio_value: Current total portfolio value

        Returns:
            Tuple of (triggered: bool, info: Dict)
        """
        # Set daily starting value on first check of the day
        if self.daily_starting_value is None:
            self.daily_starting_value = current_portfolio_value

        # Calculate daily loss
        daily_loss = self.daily_starting_value - current_portfolio_value
        daily_loss_pct = (daily_loss / self.daily_starting_value) * 100 if self.daily_starting_value > 0 else 0

        # Check if circuit breaker should trigger
        triggered = daily_loss_pct >= (self.daily_loss_limit * 100)

        if triggered and not self.circuit_breaker_triggered:
            self.circuit_breaker_triggered = True

        return triggered, {
            "daily_starting_value": round(self.daily_starting_value, 2),
            "current_value": round(current_portfolio_value, 2),
            "daily_loss": round(daily_loss, 2),
            "daily_loss_pct": round(daily_loss_pct, 2),
            "loss_limit_pct": round(self.daily_loss_limit * 100, 2),
            "triggered": triggered,
            "message": "CIRCUIT BREAKER TRIGGERED - Trading halted" if triggered else "Within daily loss limits"
        }

    def reset_daily_limits(self, starting_value: float) -> None:
        """
        Reset daily tracking (call at start of trading day)

        Args:
            starting_value: Portfolio value at start of day
        """
        self.daily_starting_value = starting_value
        self.circuit_breaker_triggered = False
        self.daily_auto_sells = 0  # Reset auto-sell counter

    def _is_market_hours(self) -> bool:
        """Check if current time is within market hours (9:30 AM - 4:00 PM ET)"""
        now_et = datetime.now(self.eastern_tz).time()
        return self.market_open <= now_et <= self.market_close

    def _can_auto_execute(self) -> Tuple[bool, Optional[str]]:
        """
        Check if automated execution is allowed

        Returns:
            Tuple of (allowed: bool, reason: Optional[str])
        """
        if not self.enable_auto_execute:
            return False, "Auto-execution is disabled"

        if self.circuit_breaker_triggered:
            return False, "Circuit breaker is active"

        if not self._is_market_hours():
            return False, "Outside market hours (9:30 AM - 4:00 PM ET)"

        if self.daily_auto_sells >= self.max_daily_auto_sells:
            return False, f"Daily auto-sell limit reached ({self.max_daily_auto_sells})"

        return True, None

    def monitor_and_execute_stops(self, positions: Dict[str, Dict],
                                  current_prices: Dict[str, float],
                                  stop_loss_pct: float = 0.10,
                                  dry_run: bool = False) -> List[Dict]:
        """
        Monitor positions for stop-loss triggers and optionally execute sells

        Args:
            positions: Dict of positions {ticker: {'quantity': int, 'avg_price': float, ...}}
            current_prices: Dict of current prices {ticker: float}
            stop_loss_pct: Stop-loss percentage (default: 10%)
            dry_run: If True, only report triggers without executing (default: False)

        Returns:
            List of dicts containing stop-loss trigger info and execution results
        """
        results = []

        for ticker, position in positions.items():
            # Skip if no current price available
            if ticker not in current_prices:
                self.logger.warning(f"No price available for {ticker}, skipping")
                continue

            current_price = current_prices[ticker]
            entry_price = position.get('avg_price') or position.get('entry_price')
            quantity = position.get('quantity', 0)

            if not entry_price or quantity <= 0:
                continue

            # Check stop-loss
            should_sell, stop_info = self.check_stop_loss(
                ticker, entry_price, current_price, stop_loss_pct
            )

            if should_sell:
                result = {
                    **stop_info,
                    'quantity': quantity,
                    'dry_run': dry_run,
                    'auto_executed': False,
                    'execution_result': None
                }

                # If dry run, just report
                if dry_run:
                    result['message'] = "STOP-LOSS TRIGGERED (DRY RUN - no action taken)"
                    self.logger.info(f"[DRY RUN] Stop-loss triggered for {ticker}: "
                                   f"{current_price} <= {stop_info['stop_loss_price']}")
                    results.append(result)
                    continue

                # Check if we can auto-execute
                can_execute, reason = self._can_auto_execute()

                if not can_execute:
                    result['message'] = f"Stop-loss triggered but auto-execution blocked: {reason}"
                    self.logger.warning(f"Stop-loss triggered for {ticker} but cannot execute: {reason}")
                    results.append(result)
                    continue

                # Log the pending execution
                self.logger.warning(
                    f"STOP-LOSS TRIGGERED for {ticker}: "
                    f"current=${current_price:.2f}, stop=${stop_info['stop_loss_price']:.2f}, "
                    f"loss={stop_info['loss_pct']:.2f}%"
                )

                # Confirmation delay (safety mechanism against flash crashes)
                self.logger.info(f"Waiting {self.confirmation_delay_seconds}s before executing...")
                time.sleep(self.confirmation_delay_seconds)

                # Re-fetch price after delay to avoid stale data
                try:
                    fresh_price = self.order_executor.get_current_price(ticker)

                    # Re-check stop-loss with fresh price
                    still_triggered, fresh_info = self.check_stop_loss(
                        ticker, entry_price, fresh_price, stop_loss_pct
                    )

                    if not still_triggered:
                        result['message'] = "Stop-loss no longer triggered after confirmation delay (price recovered)"
                        result['fresh_price'] = fresh_price
                        self.logger.info(f"Stop-loss for {ticker} no longer triggered after delay "
                                       f"(price recovered to ${fresh_price:.2f})")
                        results.append(result)
                        continue

                    # Execute limit sell at stop price (not market)
                    self.logger.warning(f"Executing stop-loss sell for {ticker}: {quantity} shares @ ${stop_info['stop_loss_price']:.2f}")

                    execution_result = self.order_executor.execute_order(
                        ticker=ticker,
                        action='SELL',
                        quantity=quantity,
                        order_type='limit',
                        limit_price=stop_info['stop_loss_price']
                    )

                    result['auto_executed'] = True
                    result['execution_result'] = execution_result
                    result['fresh_price'] = fresh_price

                    if execution_result.get('success'):
                        self.daily_auto_sells += 1
                        result['message'] = f"Stop-loss executed successfully (auto-sell #{self.daily_auto_sells})"
                        self.logger.info(f"Stop-loss executed for {ticker}: {execution_result}")
                    else:
                        result['message'] = f"Stop-loss execution failed: {execution_result.get('reason', 'unknown')}"
                        self.logger.error(f"Stop-loss execution failed for {ticker}: {execution_result}")

                    # Log to audit trail
                    self.auto_execute_log.append({
                        'timestamp': datetime.now().isoformat(),
                        'ticker': ticker,
                        'trigger_price': current_price,
                        'stop_price': stop_info['stop_loss_price'],
                        'quantity': quantity,
                        'execution_result': execution_result
                    })

                except Exception as e:
                    result['message'] = f"Stop-loss execution error: {str(e)}"
                    result['error'] = str(e)
                    self.logger.error(f"Error executing stop-loss for {ticker}: {e}")

                results.append(result)

        return results

    def get_risk_summary(self) -> Dict:
        """Get current risk management settings"""
        summary = {
            "max_position_size_pct": round(self.max_position_size * 100, 2),
            "daily_loss_limit_pct": round(self.daily_loss_limit * 100, 2),
            "absolute_max_position_pct": round(self.absolute_max_position * 100, 2),
            "absolute_daily_loss_limit_pct": round(self.absolute_daily_loss_limit * 100, 2),
            "circuit_breaker_active": self.circuit_breaker_triggered,
            "daily_starting_value": round(self.daily_starting_value, 2) if self.daily_starting_value else None
        }

        # Add auto-execute info if enabled
        if self.enable_auto_execute:
            summary.update({
                "auto_execute_enabled": True,
                "daily_auto_sells": self.daily_auto_sells,
                "max_daily_auto_sells": self.max_daily_auto_sells,
                "confirmation_delay_seconds": self.confirmation_delay_seconds,
                "market_hours": f"{self.market_open.strftime('%H:%M')} - {self.market_close.strftime('%H:%M')} ET",
                "is_market_hours": self._is_market_hours(),
                "can_auto_execute": self._can_auto_execute()[0],
                "total_auto_executions": len(self.auto_execute_log)
            })
        else:
            summary["auto_execute_enabled"] = False

        return summary


if __name__ == "__main__":
    # Quick test
    print("Testing RiskManager...")

    # Create risk manager (without auto-execute for basic tests)
    rm = RiskManager()

    print("\n1. Risk Settings:")
    print(rm.get_risk_summary())

    print("\n2. Calculate position size for AAPL @ $180, portfolio = $100k:")
    position_rec = rm.calculate_position_size(100000, "AAPL", 180.0)
    print(position_rec)

    print("\n3. Validate order to buy recommended shares:")
    valid, reason = rm.validate_order(
        "BUY", "AAPL", position_rec["recommended_shares"], 180.0,
        portfolio_value=100000,
        current_positions={},
        cash=100000
    )
    print(f"Valid: {valid}, Reason: {reason}")

    print("\n4. Check stop-loss (bought @ $180, now @ $160):")
    should_sell, info = rm.check_stop_loss("AAPL", 180.0, 160.0, stop_loss_pct=0.10)
    print(info)

    print("\n5. Check circuit breaker (portfolio dropped from $100k to $97k):")
    rm.reset_daily_limits(100000)
    triggered, info = rm.check_circuit_breaker(97000)
    print(info)

    print("\n6. Check circuit breaker (portfolio dropped from $100k to $95k):")
    triggered, info = rm.check_circuit_breaker(95000)
    print(info)

    print("\n7. Try to buy after circuit breaker:")
    valid, reason = rm.validate_order(
        "BUY", "NVDA", 10, 500.0,
        portfolio_value=95000,
        current_positions={},
        cash=50000
    )
    print(f"Valid: {valid}, Reason: {reason}")

    print("\n" + "="*70)
    print("AUTO-EXECUTE STOP-LOSS TEST (DRY RUN)")
    print("="*70)

    # Test auto-execute functionality in dry-run mode
    print("\n8. Test auto-execute stop-loss monitoring (dry run):")

    # Mock positions that would trigger stop-losses
    test_positions = {
        "AAPL": {"quantity": 50, "avg_price": 180.0},
        "TSLA": {"quantity": 20, "avg_price": 250.0},
        "NVDA": {"quantity": 10, "avg_price": 500.0}
    }

    # Mock current prices (AAPL and TSLA hit stop-loss, NVDA is fine)
    test_prices = {
        "AAPL": 160.0,  # Down 11.1% - triggers 10% stop-loss
        "TSLA": 220.0,  # Down 12% - triggers stop-loss
        "NVDA": 510.0   # Up 2% - no trigger
    }

    # Create risk manager without order executor (dry run only)
    rm_test = RiskManager(enable_auto_execute=False)

    results = rm_test.monitor_and_execute_stops(
        positions=test_positions,
        current_prices=test_prices,
        stop_loss_pct=0.10,
        dry_run=True
    )

    print(f"\nStop-loss monitoring results: {len(results)} trigger(s)")
    for i, result in enumerate(results, 1):
        print(f"\n  Trigger #{i}:")
        print(f"    Ticker: {result['ticker']}")
        print(f"    Entry: ${result['entry_price']:.2f}")
        print(f"    Current: ${result['current_price']:.2f}")
        print(f"    Loss: {result['loss_pct']:.2f}%")
        print(f"    Stop Price: ${result['stop_loss_price']:.2f}")
        print(f"    Quantity: {result['quantity']} shares")
        print(f"    Status: {result['message']}")

    print("\n" + "="*70)
    print("SAFETY MECHANISMS:")
    print("="*70)
    print("\n  1. Kill Switch: enable_auto_execute=False by default")
    print("  2. Confirmation Delay: 5-second wait before executing")
    print("  3. Price Re-check: Fetches fresh price after delay")
    print("  4. Market Hours: Only executes 9:30 AM - 4:00 PM ET")
    print("  5. Daily Limit: Max 10 auto-sells per day")
    print("  6. Limit Orders: Sells at stop price, not market")
    print("  7. Circuit Breaker: Halts if portfolio loss limit hit")
    print("  8. Audit Trail: Logs all automated actions")
    print("\n  To enable: RiskManager(enable_auto_execute=True, order_executor=executor)")
    print("="*70)
