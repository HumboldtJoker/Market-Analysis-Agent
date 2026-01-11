"""
Order Executor for AutoInvestor

Executes trades in both paper (simulated) and live (Alpaca API) modes.
"""

import os
from typing import Dict, Optional
from datetime import datetime
import yfinance as yf

try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest
    from alpaca.trading.enums import OrderSide, TimeInForce
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False

from portfolio_manager import PortfolioManager


class OrderExecutor:
    """
    Executes buy/sell orders in paper or live mode

    Paper Mode:
    - Fetches real-time prices from Yahoo Finance
    - Simulates order execution with portfolio manager

    Live Mode:
    - Executes real orders via Alpaca API
    - Syncs with Alpaca account state
    """

    def __init__(self, mode: str = "paper", portfolio_manager: Optional[PortfolioManager] = None):
        """
        Initialize order executor

        Args:
            mode: 'paper' for simulated trading, 'live' for real trading
            portfolio_manager: Existing PortfolioManager instance (optional)
        """
        self.mode = mode.lower()

        if self.mode not in ['paper', 'live']:
            raise ValueError(f"Invalid mode: {mode}. Must be 'paper' or 'live'")

        # Portfolio manager
        if portfolio_manager:
            self.portfolio = portfolio_manager
        else:
            self.portfolio = PortfolioManager(mode=self.mode)

        # Alpaca client (live mode only)
        self.alpaca_client = None
        if self.mode == "live":
            if not ALPACA_AVAILABLE:
                raise ImportError(
                    "Alpaca SDK not installed. Run: pip install alpaca-py"
                )

            # Get Alpaca credentials from environment
            api_key = os.environ.get("ALPACA_API_KEY")
            api_secret = os.environ.get("ALPACA_SECRET_KEY")
            paper_mode = os.environ.get("ALPACA_PAPER", "true").lower() == "true"

            if not api_key or not api_secret:
                raise ValueError(
                    "Alpaca credentials not found. Set ALPACA_API_KEY and "
                    "ALPACA_SECRET_KEY environment variables."
                )

            # Initialize Alpaca client
            self.alpaca_client = TradingClient(
                api_key=api_key,
                secret_key=api_secret,
                paper=paper_mode
            )

            # Sync initial account state
            self._sync_alpaca_state()

    def get_current_price(self, ticker: str) -> float:
        """
        Get current market price for a ticker

        Args:
            ticker: Stock symbol

        Returns:
            Current price

        Raises:
            ValueError: If price cannot be fetched
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            # Try multiple price fields
            price = (
                info.get('currentPrice') or
                info.get('regularMarketPrice') or
                info.get('previousClose')
            )

            if not price:
                raise ValueError(f"Could not fetch price for {ticker}")

            return float(price)

        except Exception as e:
            raise ValueError(f"Error fetching price for {ticker}: {str(e)}")

    def execute_order(self, ticker: str, action: str, quantity: float,
                     order_type: str = "market", limit_price: Optional[float] = None) -> Dict:
        """
        Execute a buy or sell order

        Args:
            ticker: Stock symbol
            action: 'BUY' or 'SELL'
            quantity: Number of shares (fractional shares supported for market orders)
            order_type: 'market' or 'limit' (default: 'market')
            limit_price: Price for limit orders (ignored for market orders)

        Returns:
            Dict with order details and execution status

        Raises:
            ValueError: If order cannot be executed
        """
        action = action.upper()

        if action not in ['BUY', 'SELL']:
            raise ValueError(f"Invalid action: {action}")

        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}")

        if self.mode == "paper":
            return self._execute_paper_order(ticker, action, quantity, order_type, limit_price)
        else:
            return self._execute_live_order(ticker, action, quantity, order_type, limit_price)

    def _execute_paper_order(self, ticker: str, action: str, quantity: float,
                            order_type: str, limit_price: Optional[float]) -> Dict:
        """Execute order in paper mode (simulated)"""

        # Get current market price
        current_price = self.get_current_price(ticker)

        # Determine execution price
        if order_type == "market":
            # Market orders execute at current price
            # Add slippage simulation (0.05% for market orders)
            slippage = 0.0005
            if action == "BUY":
                execution_price = current_price * (1 + slippage)
            else:
                execution_price = current_price * (1 - slippage)
        elif order_type == "limit":
            if not limit_price:
                raise ValueError("Limit price required for limit orders")

            # Check if limit order would fill
            if action == "BUY" and current_price > limit_price:
                return {
                    "success": False,
                    "status": "rejected",
                    "reason": f"Limit buy price ${limit_price:.2f} below market ${current_price:.2f}",
                    "ticker": ticker,
                    "action": action,
                    "quantity": quantity
                }
            elif action == "SELL" and current_price < limit_price:
                return {
                    "success": False,
                    "status": "rejected",
                    "reason": f"Limit sell price ${limit_price:.2f} above market ${current_price:.2f}",
                    "ticker": ticker,
                    "action": action,
                    "quantity": quantity
                }

            execution_price = limit_price
        else:
            raise ValueError(f"Invalid order type: {order_type}")

        # Execute trade via portfolio manager
        try:
            result = self.portfolio.execute_trade(
                ticker=ticker,
                action=action,
                quantity=quantity,
                price=execution_price,
                commission=0.0  # No commission in paper mode
            )

            # Update current price in portfolio
            self.portfolio.update_prices({ticker: current_price})

            return {
                "success": True,
                "status": "filled",
                "mode": "paper",
                "ticker": ticker,
                "action": action,
                "quantity": quantity,
                "order_type": order_type,
                "execution_price": round(execution_price, 2),
                "market_price": round(current_price, 2),
                "timestamp": result["trade"]["timestamp"],
                "portfolio_value": result["portfolio_value"],
                "cash_remaining": result["cash"]
            }

        except ValueError as e:
            return {
                "success": False,
                "status": "rejected",
                "reason": str(e),
                "ticker": ticker,
                "action": action,
                "quantity": quantity
            }

    def _execute_live_order(self, ticker: str, action: str, quantity: float,
                           order_type: str, limit_price: Optional[float]) -> Dict:
        """Execute order in live mode via Alpaca API"""

        if not self.alpaca_client:
            raise ValueError("Alpaca client not initialized")

        try:
            # Prepare order request
            order_side = OrderSide.BUY if action == "BUY" else OrderSide.SELL

            if order_type == "market":
                # Market order
                order_data = MarketOrderRequest(
                    symbol=ticker,
                    qty=quantity,
                    side=order_side,
                    time_in_force=TimeInForce.DAY
                )
            elif order_type == "limit":
                if not limit_price:
                    raise ValueError("Limit price required for limit orders")

                # Import LimitOrderRequest
                from alpaca.trading.requests import LimitOrderRequest

                order_data = LimitOrderRequest(
                    symbol=ticker,
                    qty=quantity,
                    side=order_side,
                    time_in_force=TimeInForce.DAY,
                    limit_price=limit_price
                )
            else:
                raise ValueError(f"Invalid order type: {order_type}")

            # Submit order to Alpaca
            order = self.alpaca_client.submit_order(order_data)

            # Wait briefly for fill (market orders usually fill immediately)
            import time
            time.sleep(1)

            # Get order status
            order_status = self.alpaca_client.get_order_by_id(order.id)

            # Sync portfolio state
            self._sync_alpaca_state()

            return {
                "success": True,
                "status": order_status.status.value,
                "mode": "live",
                "order_id": order.id,
                "ticker": ticker,
                "action": action,
                "quantity": quantity,
                "order_type": order_type,
                "filled_qty": float(order_status.filled_qty) if order_status.filled_qty else 0,
                "filled_avg_price": float(order_status.filled_avg_price) if order_status.filled_avg_price else None,
                "timestamp": order.created_at.isoformat(),
                "portfolio_value": self.get_portfolio_value()
            }

        except Exception as e:
            return {
                "success": False,
                "status": "error",
                "reason": str(e),
                "ticker": ticker,
                "action": action,
                "quantity": quantity
            }

    def _sync_alpaca_state(self) -> None:
        """Sync portfolio state with Alpaca account (live mode only)"""
        if not self.alpaca_client:
            return

        try:
            # Get account info
            account = self.alpaca_client.get_account()

            # Update cash (buying power)
            self.portfolio.cash = float(account.cash)
            self.portfolio.initial_cash = float(account.initial_cash) if hasattr(account, 'initial_cash') else float(account.cash)

            # Get all positions
            alpaca_positions = self.alpaca_client.get_all_positions()

            # Clear current positions
            self.portfolio.positions = {}

            # Import Position from portfolio_manager
            from portfolio_manager import Position

            # Add positions from Alpaca
            for pos in alpaca_positions:
                ticker = pos.symbol
                quantity = float(pos.qty)
                avg_cost = float(pos.avg_entry_price)
                current_price = float(pos.current_price)

                self.portfolio.positions[ticker] = Position(
                    ticker=ticker,
                    quantity=quantity,
                    avg_cost=avg_cost,
                    current_price=current_price
                )

        except Exception as e:
            print(f"Warning: Could not sync Alpaca state: {e}")

    def get_portfolio_summary(self) -> Dict:
        """Get current portfolio summary"""
        if self.mode == "live" and self.alpaca_client:
            # Sync before returning summary
            self._sync_alpaca_state()

        return self.portfolio.get_portfolio_summary()

    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        if self.mode == "live" and self.alpaca_client:
            # Sync before returning value
            self._sync_alpaca_state()

        return self.portfolio.get_portfolio_value()

    def get_position(self, ticker: str) -> Optional[Dict]:
        """Get current position for a ticker"""
        if self.mode == "live" and self.alpaca_client:
            # Sync before returning position
            self._sync_alpaca_state()

        pos = self.portfolio.get_position(ticker)
        if pos:
            return {
                "ticker": pos.ticker,
                "quantity": pos.quantity,
                "avg_cost": round(pos.avg_cost, 2),
                "current_price": round(pos.current_price, 2),
                "market_value": round(pos.market_value, 2),
                "unrealized_pl": round(pos.unrealized_pl, 2),
                "unrealized_pl_percent": round(pos.unrealized_pl_percent, 2)
            }
        return None

    def get_buying_power(self) -> float:
        """Get available buying power (cash)"""
        if self.mode == "live" and self.alpaca_client:
            # Sync before returning cash
            self._sync_alpaca_state()

        return self.portfolio.cash


if __name__ == "__main__":
    # Quick test (paper mode)
    print("Testing OrderExecutor (Paper Mode)...")

    # Create executor
    executor = OrderExecutor(mode="paper")

    print("\n1. Initial Portfolio:")
    print(executor.get_portfolio_summary())

    print("\n2. Getting current price for AAPL...")
    aapl_price = executor.get_current_price("AAPL")
    print(f"AAPL current price: ${aapl_price:.2f}")

    print("\n3. Buying 10 shares of AAPL (market order)...")
    result = executor.execute_order("AAPL", "BUY", 10, order_type="market")
    print(result)

    print("\n4. Buying 5 shares of NVDA (market order)...")
    result = executor.execute_order("NVDA", "BUY", 5, order_type="market")
    print(result)

    print("\n5. Portfolio Summary:")
    print(executor.get_portfolio_summary())

    print("\n6. Getting AAPL position:")
    position = executor.get_position("AAPL")
    print(position)

    print("\n7. Selling 5 shares of AAPL...")
    result = executor.execute_order("AAPL", "SELL", 5, order_type="market")
    print(result)

    print("\n8. Final Portfolio:")
    print(executor.get_portfolio_summary())
