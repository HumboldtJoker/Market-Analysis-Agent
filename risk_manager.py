"""
Risk Manager for AutoInvestor

Handles position sizing, stop-losses, and circuit breakers to protect capital.
"""

from typing import Dict, Optional, Tuple
from investor_profile import InvestorProfile


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

    def __init__(self, investor_profile: Optional[InvestorProfile] = None):
        """
        Initialize risk manager

        Args:
            investor_profile: Optional investor profile for personalized risk settings
        """
        self.profile = investor_profile

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

    def get_risk_summary(self) -> Dict:
        """Get current risk management settings"""
        return {
            "max_position_size_pct": round(self.max_position_size * 100, 2),
            "daily_loss_limit_pct": round(self.daily_loss_limit * 100, 2),
            "absolute_max_position_pct": round(self.absolute_max_position * 100, 2),
            "absolute_daily_loss_limit_pct": round(self.absolute_daily_loss_limit * 100, 2),
            "circuit_breaker_active": self.circuit_breaker_triggered,
            "daily_starting_value": round(self.daily_starting_value, 2) if self.daily_starting_value else None
        }


if __name__ == "__main__":
    # Quick test
    print("Testing RiskManager...")

    # Create risk manager
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
