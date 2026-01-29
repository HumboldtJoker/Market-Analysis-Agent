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

    def __init__(self, mode: str = "local", portfolio_manager: Optional[PortfolioManager] = None):
        """
        Initialize order executor

        Args:
            mode: Trading mode
                - 'local': Fully simulated trading (no API calls)
                - 'alpaca': Use Alpaca API (paper vs live determined by ALPACA_PAPER env var)
                - 'paper'/'live': Deprecated aliases for 'local'/'alpaca'
            portfolio_manager: Existing PortfolioManager instance (optional)
        """
        self.mode = mode.lower()

        # Backward compatibility: map old names to new names
        mode_aliases = {'paper': 'local', 'live': 'alpaca'}
        if self.mode in mode_aliases:
            import logging
            logging.warning(
                f"mode='{self.mode}' is deprecated. Use mode='{mode_aliases[self.mode]}' instead."
            )
            self.mode = mode_aliases[self.mode]

        if self.mode not in ['local', 'alpaca']:
            raise ValueError(f"Invalid mode: {mode}. Must be 'local' or 'alpaca'")

        # Portfolio manager
        if portfolio_manager:
            self.portfolio = portfolio_manager
        else:
            self.portfolio = PortfolioManager(mode=self.mode)

        # Alpaca client (live mode only)
        self.alpaca_client = None
        if self.mode == "alpaca":
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

        # Valid actions: BUY/SELL for longs, SHORT/COVER for shorts
        if action not in ['BUY', 'SELL', 'SHORT', 'COVER']:
            raise ValueError(f"Invalid action: {action}. Use BUY, SELL, SHORT, or COVER")

        if quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}")

        # Security validation: prevent dangerous orders
        current_price = self.get_current_price(ticker)
        order_value = quantity * current_price

        # 1. Sanity check: reject absurdly large quantities (> 100,000 shares)
        if quantity > 100000:
            raise ValueError(f"Order quantity {quantity} exceeds maximum allowed (100,000 shares)")

        # 2. For SELL: verify we own enough shares (long position)
        if action == "SELL":
            position = self.portfolio.get_position(ticker)
            if position is None:
                raise ValueError(f"Cannot sell {ticker}: no position held")
            if position.quantity < 0:
                raise ValueError(f"Cannot SELL {ticker}: position is short. Use COVER to close shorts")
            if quantity > position.quantity:
                raise ValueError(
                    f"Cannot sell {quantity} shares of {ticker}: only own {position.quantity:.4f} shares"
                )

        # 3. For BUY: verify we have enough cash (with 5% buffer for slippage)
        if action == "BUY":
            required_cash = order_value * 1.05  # 5% buffer
            available_cash = self.portfolio.cash
            if required_cash > available_cash and available_cash > 0:
                max_shares = (available_cash * 0.95) / current_price
                raise ValueError(
                    f"Insufficient cash for {quantity} shares of {ticker} "
                    f"(~${order_value:,.0f}): only ${available_cash:,.0f} available. "
                    f"Max buy: {max_shares:.2f} shares"
                )

        # 4. For SHORT: verify margin requirements and no existing long position
        if action == "SHORT":
            position = self.portfolio.get_position(ticker)
            if position is not None and position.quantity > 0:
                raise ValueError(
                    f"Cannot SHORT {ticker}: already have long position of {position.quantity:.4f} shares. "
                    f"SELL the long first, then SHORT."
                )
            # Margin requirement: need ~150% of order value as collateral (Reg T)
            # We check for 50% margin requirement (the borrowed portion)
            margin_required = order_value * 0.50
            available_cash = self.portfolio.cash
            if margin_required > available_cash:
                raise ValueError(
                    f"Insufficient margin for shorting {quantity} shares of {ticker}. "
                    f"Need ${margin_required:,.0f} margin (50%), have ${available_cash:,.0f}"
                )

        # 5. For COVER: verify we have a short position to close
        if action == "COVER":
            position = self.portfolio.get_position(ticker)
            if position is None:
                raise ValueError(f"Cannot COVER {ticker}: no position held")
            if position.quantity >= 0:
                raise ValueError(f"Cannot COVER {ticker}: position is long, not short. Use SELL instead")
            if quantity > abs(position.quantity):
                raise ValueError(
                    f"Cannot cover {quantity} shares of {ticker}: only short {abs(position.quantity):.4f} shares"
                )

        # 4. Single order size limit: warn if > 25% of portfolio (but allow it)
        portfolio_value = self.portfolio.get_portfolio_value() + self.portfolio.cash
        if portfolio_value > 0 and order_value > portfolio_value * 0.25:
            import logging
            logging.warning(
                f"Large order: {ticker} {action} ${order_value:,.0f} is "
                f"{(order_value/portfolio_value)*100:.1f}% of portfolio"
            )

        if self.mode == "local":
            return self._execute_paper_order(ticker, action, quantity, order_type, limit_price)
        else:
            return self._execute_live_order(ticker, action, quantity, order_type, limit_price)

    def _execute_paper_order(self, ticker: str, action: str, quantity: float,
                            order_type: str, limit_price: Optional[float]) -> Dict:
        """Execute order in paper mode (simulated)"""

        # Get current market price
        current_price = self.get_current_price(ticker)

        # Determine execution price
        # BUY/COVER = buying shares, SELL/SHORT = selling shares
        is_buying = action in ["BUY", "COVER"]

        if order_type == "market":
            # Market orders execute at current price
            # Add slippage simulation (0.05% for market orders)
            slippage = 0.0005
            if is_buying:
                execution_price = current_price * (1 + slippage)
            else:
                execution_price = current_price * (1 - slippage)
        elif order_type == "limit":
            if not limit_price:
                raise ValueError("Limit price required for limit orders")

            # Check if limit order would fill
            if is_buying and current_price > limit_price:
                return {
                    "success": False,
                    "status": "rejected",
                    "reason": f"Limit {action.lower()} price ${limit_price:.2f} below market ${current_price:.2f}",
                    "ticker": ticker,
                    "action": action,
                    "quantity": quantity
                }
            elif not is_buying and current_price < limit_price:
                return {
                    "success": False,
                    "status": "rejected",
                    "reason": f"Limit {action.lower()} price ${limit_price:.2f} above market ${current_price:.2f}",
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
            # BUY/COVER -> buy shares, SELL/SHORT -> sell shares
            order_side = OrderSide.BUY if action in ["BUY", "COVER"] else OrderSide.SELL

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
        if self.mode == "alpaca" and self.alpaca_client:
            # Sync before returning summary
            self._sync_alpaca_state()

        return self.portfolio.get_portfolio_summary()

    def get_portfolio_value(self) -> float:
        """Get total portfolio value"""
        if self.mode == "alpaca" and self.alpaca_client:
            # Sync before returning value
            self._sync_alpaca_state()

        return self.portfolio.get_portfolio_value()

    def get_position(self, ticker: str) -> Optional[Dict]:
        """Get current position for a ticker"""
        if self.mode == "alpaca" and self.alpaca_client:
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
        if self.mode == "alpaca" and self.alpaca_client:
            # Sync before returning cash
            self._sync_alpaca_state()

        return self.portfolio.cash

    def validate_deployment(self, planned_trades: Dict[str, float],
                          use_margin: bool = False) -> Dict:
        """
        Validate if a set of planned trades can be executed within account limits

        SAFETY CHECK: Prevents over-deployment and margin violations
        Call this BEFORE executing any bulk strategy deployment

        Args:
            planned_trades: Dict of {ticker: dollar_amount} for planned positions
            use_margin: If True, allows using margin (2x buying power)
                       If False, limits to cash only

        Returns:
            Dict with validation results:
            {
                "valid": bool,
                "account_cash": float,
                "account_equity": float,
                "buying_power": float,
                "total_deployment": float,
                "available_after": float,
                "margin_used": float,
                "warnings": list,
                "errors": list
            }
        """
        # Get current account state
        if self.mode == "alpaca" and self.alpaca_client:
            account = self.alpaca_client.get_account()
            cash = float(account.cash)
            equity = float(account.equity)
            buying_power = float(account.buying_power)
        else:
            # Paper mode
            cash = self.portfolio.cash
            equity = self.portfolio.get_portfolio_value()
            buying_power = cash  # No margin in paper mode by default

        # Calculate total deployment
        total_deployment = sum(planned_trades.values())

        # Determine available capital
        if use_margin:
            available_capital = buying_power
        else:
            available_capital = cash

        # Calculate what will remain
        available_after = available_capital - total_deployment
        margin_used = max(0, total_deployment - cash)

        # Validation checks
        errors = []
        warnings = []
        valid = True

        # ERROR: Exceeds available capital
        if total_deployment > available_capital:
            errors.append(
                f"Deployment ${total_deployment:,.0f} exceeds "
                f"{'buying power' if use_margin else 'cash'} ${available_capital:,.0f}"
            )
            valid = False

        # ERROR: Would result in negative cash without margin approval
        if not use_margin and total_deployment > cash:
            errors.append(
                f"Deployment ${total_deployment:,.0f} exceeds cash ${cash:,.0f}. "
                "Set use_margin=True to allow margin usage"
            )
            valid = False

        # WARNING: Using significant margin
        if margin_used > 0:
            margin_pct = (margin_used / equity) * 100
            if margin_pct > 50:
                warnings.append(
                    f"High margin usage: ${margin_used:,.0f} ({margin_pct:.0f}% of equity)"
                )
            else:
                warnings.append(
                    f"Using margin: ${margin_used:,.0f} ({margin_pct:.0f}% of equity)"
                )

        # WARNING: Low cash buffer remaining
        cash_buffer_pct = (available_after / equity) * 100 if equity > 0 else 0
        if valid and cash_buffer_pct < 10:
            warnings.append(
                f"Low cash buffer: ${available_after:,.0f} ({cash_buffer_pct:.0f}% of equity)"
            )

        return {
            "valid": valid,
            "account_cash": cash,
            "account_equity": equity,
            "buying_power": buying_power,
            "total_deployment": total_deployment,
            "available_after": available_after,
            "margin_used": margin_used,
            "margin_pct": (margin_used / equity * 100) if equity > 0 else 0,
            "warnings": warnings,
            "errors": errors
        }

    def execute_instructions(self, instructions_file: str = "trading_instructions.json",
                            auto_archive: bool = True) -> Dict:
        """
        Execute a set of trading instructions from file

        SAFETY: Validates entire instruction set before executing any trades
        LOGGING: Archives instructions and logs all results

        Args:
            instructions_file: Path to trading instructions JSON file
            auto_archive: Automatically archive instructions after execution

        Returns:
            Dict with execution results:
            {
                "success": bool,
                "validation": dict,
                "execution_results": list,
                "final_portfolio": dict,
                "errors": list
            }
        """
        from trading_instructions import TradingInstructionSet
        from strategy_logger import StrategyReviewLogger

        logger = StrategyReviewLogger()

        # Load instructions
        try:
            instruction_set = TradingInstructionSet.load(instructions_file)
            if instruction_set is None:
                return {
                    "success": False,
                    "error": f"Instructions file not found: {instructions_file}",
                    "validation": None,
                    "execution_results": [],
                    "final_portfolio": None,
                    "errors": [f"File not found: {instructions_file}"]
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load instructions: {e}",
                "validation": None,
                "execution_results": [],
                "final_portfolio": None,
                "errors": [str(e)]
            }

        # Check if already executed
        if instruction_set.status == "completed":
            return {
                "success": False,
                "error": "Instructions already executed",
                "validation": None,
                "execution_results": instruction_set.execution_results,
                "final_portfolio": None,
                "errors": ["Instructions already executed"]
            }

        # Build validation dict from BUY instructions
        planned_trades = {}
        for instr in instruction_set.get_buy_instructions():
            if instr.target_allocation:
                planned_trades[instr.ticker] = instr.target_allocation

        # VALIDATE before executing
        validation = self.validate_deployment(planned_trades, use_margin=instruction_set.use_margin)
        instruction_set.validation_result = validation

        if not validation["valid"]:
            instruction_set.status = "validation_failed"
            instruction_set.save(instructions_file)

            return {
                "success": False,
                "error": "Validation failed",
                "validation": validation,
                "execution_results": [],
                "final_portfolio": None,
                "errors": validation["errors"]
            }

        # EXECUTE all instructions
        execution_results = []
        errors = []

        # Execute SELL orders first (free up cash)
        for instr in instruction_set.get_sell_instructions():
            try:
                result = self.execute_order(
                    ticker=instr.ticker,
                    action=instr.action,
                    quantity=instr.quantity,
                    order_type=instr.order_type,
                    limit_price=instr.limit_price
                )
                execution_results.append({
                    "ticker": instr.ticker,
                    "action": instr.action,
                    "quantity": instr.quantity,
                    "status": result.get("status", "unknown"),
                    "reason": instr.reason
                })
            except Exception as e:
                errors.append(f"SELL {instr.ticker}: {e}")
                execution_results.append({
                    "ticker": instr.ticker,
                    "action": instr.action,
                    "quantity": instr.quantity,
                    "status": "error",
                    "error": str(e),
                    "reason": instr.reason
                })

        # Execute BUY orders
        for instr in instruction_set.get_buy_instructions():
            try:
                result = self.execute_order(
                    ticker=instr.ticker,
                    action=instr.action,
                    quantity=instr.quantity,
                    order_type=instr.order_type,
                    limit_price=instr.limit_price
                )
                execution_results.append({
                    "ticker": instr.ticker,
                    "action": instr.action,
                    "quantity": instr.quantity,
                    "status": result.get("status", "unknown"),
                    "reason": instr.reason
                })
            except Exception as e:
                errors.append(f"BUY {instr.ticker}: {e}")
                execution_results.append({
                    "ticker": instr.ticker,
                    "action": instr.action,
                    "quantity": instr.quantity,
                    "status": "error",
                    "error": str(e),
                    "reason": instr.reason
                })

        # Update instruction set
        instruction_set.execution_results = execution_results
        instruction_set.status = "completed" if not errors else "completed_with_errors"
        instruction_set.save(instructions_file)

        # Get final portfolio state
        final_portfolio = self.get_portfolio_summary()

        # Log execution results
        logger.log_execution_result(
            instructions_file=instructions_file,
            execution_summary={
                "total_instructions": len(instruction_set.instructions),
                "successful": len([r for r in execution_results if r["status"] in ["filled", "partially_filled"]]),
                "failed": len([r for r in execution_results if r["status"] == "error"])
            },
            final_portfolio=final_portfolio,
            errors=errors
        )

        # Archive instructions
        if auto_archive:
            instruction_set.archive()

        return {
            "success": len(errors) == 0,
            "validation": validation,
            "execution_results": execution_results,
            "final_portfolio": final_portfolio,
            "errors": errors
        }


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
