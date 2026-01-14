"""
Trading Instructions Format for File-Based Strategy Execution

The Strategy Agent writes instructions to a file.
The Executor reads, validates, and executes them.
All decisions are logged for audit trail.
"""

import json
from typing import Dict, List, Optional, Literal
from datetime import datetime
from pathlib import Path


class TradingInstruction:
    """Single trade instruction"""

    def __init__(self,
                 action: Literal["BUY", "SELL"],
                 ticker: str,
                 quantity: float,
                 order_type: Literal["market", "limit"] = "market",
                 limit_price: Optional[float] = None,
                 reason: str = "",
                 target_allocation: Optional[float] = None,
                 profit_target_pct: Optional[float] = None,
                 stop_loss_pct: Optional[float] = None):
        """
        Initialize a single trade instruction

        Args:
            action: "BUY" or "SELL"
            ticker: Stock symbol
            quantity: Number of shares
            order_type: "market" or "limit"
            limit_price: Required if order_type is "limit"
            reason: Why this trade is being made (for logging)
            target_allocation: Target dollar amount (for validation)
            profit_target_pct: Take profit at this % gain (e.g., 15.0 for +15%)
            stop_loss_pct: Stop loss at this % loss (e.g., 8.0 for -8%)
        """
        self.action = action.upper()
        self.ticker = ticker.upper()
        self.quantity = quantity
        self.order_type = order_type.lower()
        self.limit_price = limit_price
        self.reason = reason
        self.target_allocation = target_allocation
        self.profit_target_pct = profit_target_pct
        self.stop_loss_pct = stop_loss_pct

        # Validate
        if self.action not in ["BUY", "SELL"]:
            raise ValueError(f"Invalid action: {action}")
        if self.order_type not in ["market", "limit"]:
            raise ValueError(f"Invalid order_type: {order_type}")
        if self.order_type == "limit" and self.limit_price is None:
            raise ValueError("limit_price required for limit orders")
        if self.quantity <= 0:
            raise ValueError(f"Invalid quantity: {quantity}")

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "action": self.action,
            "ticker": self.ticker,
            "quantity": self.quantity,
            "order_type": self.order_type,
            "limit_price": self.limit_price,
            "reason": self.reason,
            "target_allocation": self.target_allocation,
            "profit_target_pct": self.profit_target_pct,
            "stop_loss_pct": self.stop_loss_pct
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TradingInstruction':
        """Create from dictionary"""
        return cls(**data)


class TradingInstructionSet:
    """Complete set of trading instructions from Strategy Agent"""

    def __init__(self,
                 strategy_type: str,
                 instructions: List[TradingInstruction],
                 use_margin: bool = False,
                 reason: str = "",
                 market_context: Optional[Dict] = None):
        """
        Initialize a set of trading instructions

        Args:
            strategy_type: Name of strategy (e.g., "aggressive_momentum", "defensive_rotation")
            instructions: List of TradingInstruction objects
            use_margin: Whether margin is allowed for this deployment
            reason: Overall rationale for this set of trades
            market_context: Optional market conditions that led to this decision
        """
        self.strategy_type = strategy_type
        self.instructions = instructions
        self.use_margin = use_margin
        self.reason = reason
        self.market_context = market_context or {}
        self.timestamp = datetime.now().isoformat()
        self.status = "pending"
        self.validation_result = None
        self.execution_results = []

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "timestamp": self.timestamp,
            "strategy_type": self.strategy_type,
            "reason": self.reason,
            "use_margin": self.use_margin,
            "market_context": self.market_context,
            "instructions": [instr.to_dict() for instr in self.instructions],
            "status": self.status,
            "validation_result": self.validation_result,
            "execution_results": self.execution_results
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'TradingInstructionSet':
        """Create from dictionary"""
        instructions = [TradingInstruction.from_dict(instr)
                       for instr in data.get("instructions", [])]

        obj = cls(
            strategy_type=data["strategy_type"],
            instructions=instructions,
            use_margin=data.get("use_margin", False),
            reason=data.get("reason", ""),
            market_context=data.get("market_context", {})
        )

        # Restore saved state
        if "timestamp" in data:
            obj.timestamp = data["timestamp"]
        if "status" in data:
            obj.status = data["status"]
        if "validation_result" in data:
            obj.validation_result = data["validation_result"]
        if "execution_results" in data:
            obj.execution_results = data["execution_results"]

        return obj

    def save(self, filepath: str = "trading_instructions.json"):
        """Save instructions to file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str = "trading_instructions.json") -> Optional['TradingInstructionSet']:
        """Load instructions from file"""
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid trading instructions file: {e}")

    def archive(self, archive_dir: str = "trading_instructions_history"):
        """
        Archive this instruction set to history directory

        Saves with timestamp in filename for audit trail
        """
        Path(archive_dir).mkdir(exist_ok=True)

        # Create filename with timestamp
        timestamp_str = self.timestamp.replace(":", "-").replace(".", "-")
        filename = f"{archive_dir}/instructions_{timestamp_str}.json"

        with open(filename, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

        return filename

    def get_total_deployment(self) -> float:
        """Calculate total dollar deployment from BUY instructions"""
        total = 0.0
        for instr in self.instructions:
            if instr.action == "BUY" and instr.target_allocation:
                total += instr.target_allocation
        return total

    def get_buy_instructions(self) -> List[TradingInstruction]:
        """Get only BUY instructions"""
        return [i for i in self.instructions if i.action == "BUY"]

    def get_sell_instructions(self) -> List[TradingInstruction]:
        """Get only SELL instructions"""
        return [i for i in self.instructions if i.action == "SELL"]

    def summary(self) -> str:
        """Generate human-readable summary"""
        buys = self.get_buy_instructions()
        sells = self.get_sell_instructions()

        summary = [
            f"Strategy: {self.strategy_type}",
            f"Timestamp: {self.timestamp}",
            f"Status: {self.status}",
            f"",
            f"Reason: {self.reason}",
            f"",
            f"Instructions:",
            f"  BUY: {len(buys)} orders",
            f"  SELL: {len(sells)} orders",
            f"",
        ]

        if buys:
            summary.append("BUY Orders:")
            for instr in buys:
                allocation = f"${instr.target_allocation:,.0f}" if instr.target_allocation else "N/A"
                summary.append(f"  {instr.ticker}: {instr.quantity:.2f} shares ({allocation}) - {instr.reason}")

        if sells:
            summary.append("")
            summary.append("SELL Orders:")
            for instr in sells:
                summary.append(f"  {instr.ticker}: {instr.quantity:.2f} shares - {instr.reason}")

        return "\n".join(summary)


# Example usage
if __name__ == "__main__":
    # Example: Create trading instructions
    instructions = TradingInstructionSet(
        strategy_type="aggressive_momentum",
        reason="Initial deployment of $200k aggressive portfolio with 15% profit targets",
        use_margin=True,
        market_context={
            "vix": 15.98,
            "regime": "BULLISH",
            "market_open": True
        },
        instructions=[
            TradingInstruction(
                action="BUY",
                ticker="MU",
                quantity=84.48,
                order_type="market",
                reason="HIGH conviction - explosive momentum, RSI 69.74",
                target_allocation=28000,
                profit_target_pct=15.0,
                stop_loss_pct=8.0
            ),
            TradingInstruction(
                action="BUY",
                ticker="AMD",
                quantity=117.34,
                order_type="market",
                reason="HIGH conviction - perfect setup, bullish MACD crossover",
                target_allocation=26000,
                profit_target_pct=15.0,
                stop_loss_pct=8.0
            ),
            TradingInstruction(
                action="SELL",
                ticker="NVDA",
                quantity=50.0,
                order_type="market",
                reason="Hit 15% profit target - take profits on half position"
            )
        ]
    )

    # Save to file
    instructions.save("trading_instructions.json")

    # Print summary
    print(instructions.summary())

    # Load and verify
    loaded = TradingInstructionSet.load("trading_instructions.json")
    print("\nLoaded successfully:")
    print(f"  Strategy: {loaded.strategy_type}")
    print(f"  Instructions: {len(loaded.instructions)}")
