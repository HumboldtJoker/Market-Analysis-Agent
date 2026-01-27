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
import subprocess
from datetime import datetime, time as dt_time, date
from pathlib import Path
import pytz
import logging
from typing import Dict, List, Optional, Tuple
from dotenv import load_dotenv
import yfinance as yf
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest

# Load environment variables from .env file
load_dotenv()

from order_executor import OrderExecutor
from risk_manager import RiskManager
from autoinvestor_api import get_correlation, get_sectors

# Import strategy trigger for VIX-based reviews
try:
    from strategy_trigger import StrategyTrigger
    STRATEGY_TRIGGER_AVAILABLE = True
except ImportError:
    STRATEGY_TRIGGER_AVAILABLE = False
    print("WARNING: strategy_trigger module not available. VIX-based strategic reviews will be disabled.")

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

# VIX log path
VIX_LOG_PATH = Path('vix_log.json')


class ExecutionMonitor:
    """Autonomous trading execution monitor"""

    def __init__(self, mode: str = "alpaca", check_interval_seconds: int = 300):
        """
        Initialize execution monitor

        Args:
            mode: 'alpaca' uses Alpaca API (paper vs live determined by ALPACA_PAPER env var)
                  'local' uses local simulation (no API)
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
        self.stop_loss_pct = 0.20  # Default -20% aggressive stops
        self.dip_buy_min = 0.05  # Buy dips of 5-10%
        self.dip_buy_max = 0.10
        self.rebalance_threshold = 0.30  # Rebalance if >30% drift

        # Autonomous defensive actions (enabled by default for risk management)
        self.autonomous_defense_enabled = True

        # Thresholds config file (hot-reloaded each cycle)
        self.thresholds_file = Path(__file__).parent / 'thresholds.json'
        self.thresholds_mtime = None

        # VIX-adaptive stop-loss percentages (defaults, can be overridden by config)
        self.vix_stop_losses = {
            'CALM': 0.25,      # -25% in calm markets
            'NORMAL': 0.20,    # -20% in normal markets
            'ELEVATED': 0.15,  # -15% in elevated volatility (TIGHTEN)
            'HIGH': 0.10       # -10% in high volatility (VERY TIGHT)
        }

        # Position-specific stop-loss overrides (loaded from config)
        self.position_stop_losses = {}

        # Profit protection thresholds (trailing stops to lock in gains)
        self.profit_protection = {}

        # Dip-buying config (loaded from thresholds.json)
        self.dip_buying_enabled = False
        self.dip_buying_tickers = []

        # High-beta positions for defensive trimming (loaded from thresholds.json)
        self.high_beta_positions = {}

        # Load thresholds from config file
        self._load_thresholds()

        # Track actions
        self.check_count = 0

        # VIX monitoring state
        self.vix_enabled = STRATEGY_TRIGGER_AVAILABLE
        self.previous_vix = None
        self.previous_vix_regime = None
        self.vix_thresholds = {
            'CALM': (0, 15),
            'NORMAL': (15, 20),
            'ELEVATED': (20, 30),
            'HIGH': (30, float('inf'))
        }

        # VIX monitoring enabled - alerts written to file for Strategy Agent
        # No API calls needed - uses Claude Code session tokens
        if self.vix_enabled:
            logger.info("VIX Monitoring enabled - alerts will trigger Strategy Agent reviews")

        # Scheduled strategic reviews (proactive checks beyond VIX alerts)
        # Intervals loaded from config in _load_thresholds()
        self.review_interval_hours = 1  # Default: hourly (overridden by config)
        self.last_scheduled_review = None
        self._load_last_review_time()

        # Opportunity discovery (separate from position review)
        self.discovery_interval_hours = 4  # Default: every 4 hours (overridden by config)
        self.discovery_start_time = "06:29"  # Default: 6:29 AM PT
        self.last_discovery = None
        self._load_last_discovery_time()

        # Capital management rules (loaded from config)
        self.opportunity_reserve_pct = 0.15
        self.max_margin_pct = 0.10

        # Watchlist for opportunity scanning
        self.scan_universe = []
        self.watchlist_candidates = {}

        logger.info(f"Strategy reviews every {self.review_interval_hours} hour(s)")
        logger.info(f"Opportunity discovery every {self.discovery_interval_hours} hours starting {self.discovery_start_time}")

        # Load VIX history
        self._load_vix_history()

        logger.info("=" * 70)
        logger.info("EXECUTION MONITOR INITIALIZED")
        logger.info(f"Mode: {mode}")
        logger.info(f"Check Interval: {check_interval_seconds} seconds")
        logger.info(f"Stop-Loss: -{self.stop_loss_pct * 100}%")
        logger.info(f"VIX Monitoring: {'ENABLED' if self.vix_enabled else 'DISABLED'}")
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
        """Check all positions for stop-loss triggers using VIX-adaptive thresholds"""
        actions = []

        for pos in positions:
            ticker = pos['ticker']
            if ticker not in current_prices:
                continue

            entry_price = pos['avg_cost']
            current_price = current_prices[ticker]
            quantity = pos['quantity']

            # Get VIX-adaptive stop-loss for this position
            stop_loss_pct = self.get_stop_loss_for_position(ticker, self.previous_vix_regime)

            # Check stop-loss with adaptive threshold
            should_sell, stop_info = self.risk_manager.check_stop_loss(
                ticker, entry_price, current_price, stop_loss_pct
            )

            if should_sell:
                logger.warning(f"[ALERT] STOP-LOSS TRIGGERED: {ticker}")
                logger.info(f"   Entry: ${entry_price:.2f}")
                logger.info(f"   Current: ${current_price:.2f}")
                logger.info(f"   Loss: {stop_info['loss_pct']:.2f}%")

                # Execute sell (market order for immediate execution on defensive exits)
                result = self.executor.execute_order(
                    ticker=ticker,
                    action='SELL',
                    quantity=quantity,
                    order_type='market'
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

    def check_profit_protection(self, positions: List[Dict], current_prices: Dict[str, float]) -> List[Dict]:
        """Check positions for profit protection triggers (trailing stops to lock in gains)"""
        actions = []

        for pos in positions:
            ticker = pos['ticker']
            if ticker not in self.profit_protection:
                continue
            if ticker not in current_prices:
                continue

            protection = self.profit_protection[ticker]
            min_price = protection.get('min_price', 0)
            current_price = current_prices[ticker]
            entry_price = pos['avg_cost']
            quantity = pos['quantity']

            if current_price <= min_price:
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                reason = protection.get('reason', 'Profit protection triggered')

                logger.warning(f"[ALERT] PROFIT PROTECTION TRIGGERED: {ticker}")
                logger.info(f"   Entry: ${entry_price:.2f}")
                logger.info(f"   Current: ${current_price:.2f}")
                logger.info(f"   Min Price: ${min_price:.2f}")
                logger.info(f"   P&L at exit: {pnl_pct:+.2f}%")
                logger.info(f"   Reason: {reason}")

                # Execute sell (market order for immediate execution)
                result = self.executor.execute_order(
                    ticker=ticker,
                    action='SELL',
                    quantity=quantity,
                    order_type='market'
                )

                actions.append({
                    'type': 'PROFIT_PROTECTION_SELL',
                    'ticker': ticker,
                    'reason': reason,
                    'quantity': quantity,
                    'pnl_pct': pnl_pct,
                    'execution': result
                })

                logger.info(f"   Execution: {result['status']}")

                # Trigger strategy review if configured
                if protection.get('trigger_review', False):
                    self._trigger_profit_protection_review(ticker, current_price, pnl_pct, quantity)

        return actions

    def _trigger_profit_protection_review(self, ticker: str, exit_price: float, pnl_pct: float, quantity: float):
        """Trigger strategy review after profit protection sell"""
        try:
            proceeds = exit_price * quantity
            portfolio = self.executor.get_portfolio_summary()

            alert = {
                'timestamp': datetime.now().isoformat(),
                'alert_type': 'PROFIT_PROTECTION_REVIEW',
                'reason': f'{ticker} profit protection triggered - redeploy ${proceeds:,.0f}',
                'sold_position': {
                    'ticker': ticker,
                    'quantity': quantity,
                    'exit_price': exit_price,
                    'pnl_pct': pnl_pct,
                    'proceeds': proceeds
                },
                'portfolio_snapshot': portfolio,
                'status': 'pending'
            }

            with open('scheduled_review_needed.json', 'w') as f:
                json.dump(alert, f, indent=2, default=str)

            logger.info("")
            logger.info("=" * 70)
            logger.info(f"[STRATEGY REVIEW TRIGGERED] Redeploy {ticker} proceeds")
            logger.info(f"   Proceeds: ${proceeds:,.2f}")
            logger.info(f"   Alert written to: scheduled_review_needed.json")
            logger.info("=" * 70)
            logger.info("")

            # Invoke Claude strategy agent to process the review
            self._invoke_strategy_agent('profit_protection', ticker)

        except Exception as e:
            logger.error(f"Error triggering profit protection review: {e}", exc_info=True)

    def _invoke_strategy_agent(self, trigger_type: str, context: str = "", prompt_override: str = None):
        """
        Invoke Claude Code CLI to process a strategy review autonomously.

        This allows the monitor to trigger intelligent redeployment decisions
        without requiring user interaction.
        """
        try:
            # Use prompt override if provided (for discovery scans)
            if prompt_override:
                prompt = prompt_override
            # Build the prompt based on trigger type
            elif trigger_type == 'profit_protection':
                prompt = f"""A profit protection sell was triggered for {context}.
Run /strategy-review to analyze the portfolio and redeploy the proceeds.
Check portfolio correlation and sector concentration before adding positions.
Execute trades as recommended by the strategy review skill."""
            elif trigger_type == 'scheduled':
                prompt = f"""A scheduled strategy review is due (runs every {self.review_interval_hours} hour(s)).
Run /strategy-review to scan for opportunities and adjust positions as needed.
Check portfolio_health in scheduled_review_needed.json for correlation and sector data.
Also check the watchlist in thresholds.json for entry opportunities.

Capital rules:
- Maintain {self.opportunity_reserve_pct * 100:.0f}% opportunity reserve
- Max margin: {self.max_margin_pct * 100:.0f}% - clear margin ASAP when positions profit

Address any concentration risks or high-correlation pairs flagged in the alert."""
            elif trigger_type == 'vix_alert':
                prompt = f"""VIX regime changed: {context}
Run /strategy-review to assess defensive posture and adjust positions if needed.
Check portfolio correlation - high-correlation positions amplify risk during volatility."""
            else:
                prompt = "Run /strategy-review to process the pending alert."

            logger.info("")
            logger.info("=" * 70)
            logger.info("[INVOKING STRATEGY AGENT] Claude Code CLI")
            logger.info(f"   Trigger: {trigger_type}")
            logger.info(f"   Prompt: {prompt[:80]}...")
            logger.info("=" * 70)

            # Get project directory for working directory
            project_dir = Path(__file__).parent

            # Invoke Claude Code CLI
            # -p flag enables print mode (non-interactive, outputs to stdout)
            # --dangerously-skip-permissions needed for autonomous operation
            # --output-format json for structured output with cost tracking
            import shutil
            import json as json_module
            claude_path = shutil.which('claude') or 'claude'

            # Pass environment with auth token
            # Supports both CLAUDE_CODE_OAUTH_TOKEN (subscription) and ANTHROPIC_API_KEY (API)
            env = os.environ.copy()

            # Check which auth method is available
            has_oauth = bool(os.environ.get('CLAUDE_CODE_OAUTH_TOKEN'))
            has_api_key = bool(os.environ.get('ANTHROPIC_API_KEY')) and os.environ.get('ANTHROPIC_API_KEY') != 'your_anthropic_api_key_here'

            if not has_oauth and not has_api_key:
                logger.warning("[STRATEGY AGENT] No auth configured - need CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY")
                return

            result = subprocess.run(
                [
                    claude_path,
                    '-p', prompt,
                    '--allowedTools', 'Bash,Read,Write,Edit,Glob,Grep,Task',
                    '--dangerously-skip-permissions',
                    '--output-format', 'json'
                ],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout for complex reviews
                env=env  # Pass auth token from .env
            )

            if result.returncode == 0:
                logger.info("[STRATEGY AGENT] Review completed successfully")
                # Parse JSON output for metrics
                try:
                    output_data = json_module.loads(result.stdout)
                    cost = output_data.get('total_cost_usd', 0)
                    duration = output_data.get('duration_ms', 0) / 1000
                    response = output_data.get('result', '')
                    logger.info(f"   Duration: {duration:.1f}s | Cost: ${cost:.4f}")
                    logger.info(f"   Response: {response[:300]}...")

                    # Save full response to file for review
                    response_file = project_dir / 'last_agent_response.json'
                    with open(response_file, 'w') as f:
                        json_module.dump(output_data, f, indent=2)
                    logger.info(f"   Full response saved to: {response_file}")
                except json_module.JSONDecodeError:
                    logger.info(f"   Output: {result.stdout[:500]}...")
            else:
                logger.error(f"[STRATEGY AGENT] Failed with code {result.returncode}")
                logger.error(f"   stdout: {result.stdout[:500] if result.stdout else '(none)'}")
                logger.error(f"   stderr: {result.stderr[:500] if result.stderr else '(none)'}")
                logger.error(f"   Claude path: {claude_path}")
                logger.error(f"   Auth: OAuth={'yes' if has_oauth else 'no'}, API={'yes' if has_api_key else 'no'}")

        except subprocess.TimeoutExpired:
            logger.error("[STRATEGY AGENT] Timed out after 5 minutes")
        except FileNotFoundError:
            logger.warning("[STRATEGY AGENT] Claude CLI not found - review requires manual processing")
        except Exception as e:
            logger.error(f"[STRATEGY AGENT] Error invoking Claude: {e}", exc_info=True)

    def check_dip_buying(self, positions: List[Dict], current_prices: Dict[str, float]) -> List[Dict]:
        """Check for dip-buying opportunities on configured tickers"""
        actions = []

        # Skip if dip-buying disabled or no tickers configured
        if not self.dip_buying_enabled or not self.dip_buying_tickers:
            return actions

        portfolio = self.executor.get_portfolio_summary()
        cash = portfolio['cash']

        for pos in positions:
            ticker = pos['ticker']
            if ticker not in self.dip_buying_tickers:
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

    def _load_thresholds(self):
        """Load thresholds from config file (hot-reload support)"""
        try:
            if not self.thresholds_file.exists():
                logger.warning(f"Thresholds file not found: {self.thresholds_file}")
                return False

            # Check if file has been modified
            current_mtime = self.thresholds_file.stat().st_mtime
            if self.thresholds_mtime == current_mtime:
                return False  # No changes

            # Load config
            with open(self.thresholds_file, 'r') as f:
                config = json.load(f)

            # Update position-specific thresholds
            if 'position_stop_losses' in config:
                self.position_stop_losses = {
                    ticker: entry['threshold'] if isinstance(entry, dict) else entry
                    for ticker, entry in config['position_stop_losses'].items()
                }
                if self.thresholds_mtime is not None:  # Only log on reload, not initial load
                    logger.info(f"[HOT RELOAD] Updated position thresholds: {list(self.position_stop_losses.keys())}")

            # Update default stop loss
            if 'default_stop_loss' in config:
                self.stop_loss_pct = config['default_stop_loss']

            # Update VIX-based thresholds
            if 'vix_stop_losses' in config:
                self.vix_stop_losses.update(config['vix_stop_losses'])

            # Update profit protection thresholds (trailing stops to lock in gains)
            if 'profit_protection' in config:
                self.profit_protection = config['profit_protection']
                if self.thresholds_mtime is not None:
                    logger.info(f"[HOT RELOAD] Updated profit protection: {list(self.profit_protection.keys())}")

            # Update dip-buying config
            if 'dip_buying' in config:
                dip_config = config['dip_buying']
                self.dip_buying_enabled = dip_config.get('enabled', False)
                self.dip_buying_tickers = dip_config.get('tickers', [])
                self.dip_buy_min = dip_config.get('min_dip_pct', 0.05)
                self.dip_buy_max = dip_config.get('max_dip_pct', 0.10)

            # Update high-beta positions for defensive actions
            if 'high_beta_positions' in config:
                self.high_beta_positions = config['high_beta_positions'].get('positions', {})

            # Update review intervals
            if 'review_intervals' in config:
                intervals = config['review_intervals']
                old_review = self.review_interval_hours
                self.review_interval_hours = intervals.get('strategy_review_hours', 1)
                self.discovery_interval_hours = intervals.get('discovery_interval_hours', 4)
                self.discovery_start_time = intervals.get('discovery_start_time', '06:29')
                if self.thresholds_mtime is not None and old_review != self.review_interval_hours:
                    logger.info(f"[HOT RELOAD] Strategy review interval: {self.review_interval_hours}h")

            # Update capital management rules
            if 'capital_management' in config:
                cap_mgmt = config['capital_management']
                self.opportunity_reserve_pct = cap_mgmt.get('opportunity_reserve_pct', 0.15)
                self.max_margin_pct = cap_mgmt.get('max_margin_pct', 0.10)

            # Update watchlist and scan universe
            if 'watchlist' in config:
                watchlist = config['watchlist']
                self.scan_universe = watchlist.get('scan_universe', [])
                self.watchlist_candidates = watchlist.get('candidates', {})

            self.thresholds_mtime = current_mtime
            return True

        except Exception as e:
            logger.error(f"Error loading thresholds: {e}")
            return False

    def _load_vix_history(self):
        """Load VIX history from log file"""
        if VIX_LOG_PATH.exists():
            try:
                with open(VIX_LOG_PATH, 'r') as f:
                    vix_data = json.load(f)
                    if vix_data and len(vix_data) > 0:
                        last_entry = vix_data[-1]
                        self.previous_vix = last_entry.get('vix')
                        self.previous_vix_regime = last_entry.get('regime')
                        logger.info(f"Loaded VIX history: Last VIX={self.previous_vix:.2f}, Regime={self.previous_vix_regime}")
            except Exception as e:
                logger.warning(f"Failed to load VIX history: {e}")
        else:
            # Initialize empty log
            with open(VIX_LOG_PATH, 'w') as f:
                json.dump([], f)
            logger.info("Initialized new VIX log file")

    def _save_vix_data(self, vix: float, regime: str):
        """Save VIX data to log file"""
        try:
            # Load existing data
            vix_log = []
            if VIX_LOG_PATH.exists():
                with open(VIX_LOG_PATH, 'r') as f:
                    vix_log = json.load(f)

            # Append new entry
            vix_log.append({
                'timestamp': datetime.now().isoformat(),
                'vix': vix,
                'regime': regime
            })

            # Keep only last 1000 entries
            if len(vix_log) > 1000:
                vix_log = vix_log[-1000:]

            # Save
            with open(VIX_LOG_PATH, 'w') as f:
                json.dump(vix_log, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to save VIX data: {e}")

    def get_vix_regime(self, vix: float) -> str:
        """
        Determine VIX regime based on level

        Args:
            vix: Current VIX level

        Returns:
            Regime name (CALM, NORMAL, ELEVATED, HIGH)
        """
        for regime, (low, high) in self.vix_thresholds.items():
            if low <= vix < high:
                return regime
        return 'HIGH'  # Default if above all thresholds

    def check_vix_regime(self) -> Optional[Tuple[float, str, bool]]:
        """
        Check current VIX level and regime, detect threshold crossings

        Returns:
            Tuple of (vix_level, regime, threshold_crossed) or None if failed
        """
        if not self.vix_enabled:
            return None

        try:
            # Fetch VIX from Yahoo Finance
            vix_ticker = yf.Ticker("^VIX")
            vix_data = vix_ticker.history(period="1d")

            if vix_data.empty:
                logger.warning("Failed to fetch VIX data")
                return None

            # Get latest VIX value
            vix_level = float(vix_data['Close'].iloc[-1])

            # Determine regime
            current_regime = self.get_vix_regime(vix_level)

            # Check for threshold crossing
            threshold_crossed = False
            if self.previous_vix is not None and self.previous_vix_regime is not None:
                # Check for major regime changes
                if self.previous_vix_regime != current_regime:
                    # Significant regime changes that warrant review:
                    # - Any transition to/from ELEVATED or HIGH
                    # - Moving up: NORMAL → ELEVATED, ELEVATED → HIGH
                    # - Moving down: HIGH → ELEVATED, ELEVATED → NORMAL
                    significant_changes = [
                        ('NORMAL', 'ELEVATED'),
                        ('ELEVATED', 'HIGH'),
                        ('HIGH', 'ELEVATED'),
                        ('ELEVATED', 'NORMAL'),
                        ('CALM', 'NORMAL'),
                        ('NORMAL', 'CALM')
                    ]

                    if (self.previous_vix_regime, current_regime) in significant_changes:
                        threshold_crossed = True
                        logger.warning(f"[VIX REGIME CHANGE] {self.previous_vix_regime} → {current_regime}")

            # Log VIX data
            logger.info(f"VIX: {vix_level:.2f} (Regime: {current_regime})")
            self._save_vix_data(vix_level, current_regime)

            return (vix_level, current_regime, threshold_crossed)

        except Exception as e:
            logger.error(f"Error checking VIX regime: {e}")
            return None

    def trigger_strategic_review_for_vix(self, vix_level: float, regime: str):
        """
        Create alert for strategic review based on VIX regime change

        Instead of calling Anthropic API, writes alert to file for Strategy Agent
        to process during regular check-ins (uses Claude Code session tokens)

        Args:
            vix_level: Current VIX level
            regime: Current regime
        """
        try:
            logger.info("")
            logger.info("=" * 70)
            logger.info("[VIX ALERT] REGIME CHANGE DETECTED - STRATEGIC REVIEW NEEDED")
            logger.info("=" * 70)

            # Get current portfolio context
            portfolio = self.executor.get_portfolio_summary()

            # Create alert for Strategy Agent
            alert = {
                'timestamp': datetime.now().isoformat(),
                'alert_type': 'VIX_REGIME_CHANGE',
                'vix_current': vix_level,
                'vix_previous': self.previous_vix,
                'regime_current': regime,
                'regime_previous': self.previous_vix_regime,
                'portfolio_snapshot': portfolio,
                'status': 'pending'
            }

            # Write alert to file
            alert_file = 'strategy_review_needed.json'
            with open(alert_file, 'w') as f:
                json.dump(alert, f, indent=2)

            logger.info(f"VIX: {self.previous_vix:.2f} ({self.previous_vix_regime}) → {vix_level:.2f} ({regime})")
            logger.info(f"Alert written to: {alert_file}")
            logger.info("=" * 70)
            logger.info("")

            # Invoke Claude strategy agent to process the review
            self._invoke_strategy_agent('vix_alert', f"{self.previous_vix_regime} -> {regime}")

        except Exception as e:
            logger.error(f"Error triggering strategic review: {e}", exc_info=True)

    def _load_last_review_time(self):
        """Load timestamp of last scheduled review"""
        review_file = 'last_review.json'
        try:
            if Path(review_file).exists():
                with open(review_file, 'r') as f:
                    data = json.load(f)
                    self.last_scheduled_review = datetime.fromisoformat(data['timestamp'])
                    logger.info(f"Last scheduled review: {self.last_scheduled_review.strftime('%Y-%m-%d %H:%M')}")
            else:
                logger.info("No previous scheduled review found - will trigger on first check")
        except Exception as e:
            logger.warning(f"Could not load last review time: {e}")

    def _save_last_review_time(self):
        """Save timestamp of completed scheduled review"""
        review_file = 'last_review.json'
        try:
            with open(review_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'review_type': 'scheduled'
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save review time: {e}")

    def _load_last_discovery_time(self):
        """Load timestamp of last opportunity discovery"""
        discovery_file = 'last_discovery.json'
        try:
            if Path(discovery_file).exists():
                with open(discovery_file, 'r') as f:
                    data = json.load(f)
                    self.last_discovery = datetime.fromisoformat(data['timestamp'])
                    logger.info(f"Last discovery scan: {self.last_discovery.strftime('%Y-%m-%d %H:%M')}")
            else:
                logger.info("No previous discovery scan found")
        except Exception as e:
            logger.warning(f"Could not load last discovery time: {e}")

    def _save_last_discovery_time(self):
        """Save timestamp of completed discovery scan"""
        discovery_file = 'last_discovery.json'
        try:
            with open(discovery_file, 'w') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'scan_type': 'opportunity_discovery'
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save discovery time: {e}")

    def check_if_review_due(self) -> bool:
        """
        Check if scheduled strategic review is due

        Returns:
            True if review needed, False otherwise
        """
        if self.last_scheduled_review is None:
            # No previous review - trigger first one
            return True

        now = datetime.now(self.eastern_tz)
        hours_since_review = (now.replace(tzinfo=None) - self.last_scheduled_review).total_seconds() / 3600

        # Standard check: has interval elapsed?
        if hours_since_review >= self.review_interval_hours:
            return True

        # End-of-day check: trigger early if next review would fall after close
        # If within 30 mins of close AND next review would be after close, trigger now
        mins_to_close = (datetime.combine(now.date(), self.market_close) - now.replace(tzinfo=None)).total_seconds() / 60
        hours_until_next_review = self.review_interval_hours - hours_since_review

        if 0 < mins_to_close <= 30 and hours_until_next_review * 60 > mins_to_close:
            logger.info(f"[END-OF-DAY REVIEW] Triggering early - next review would be after close")
            return True

        return False

    def check_if_discovery_due(self) -> bool:
        """
        Check if opportunity discovery scan is due

        Discovery runs on a separate (longer) interval than strategy reviews,
        starting at a configured time (default 6:29 AM PT for fresh pre-market news).

        Returns:
            True if discovery needed, False otherwise
        """
        now = datetime.now(self.eastern_tz)

        # Parse discovery start time
        try:
            start_hour, start_min = map(int, self.discovery_start_time.split(':'))
        except:
            start_hour, start_min = 6, 29

        # Check if we're past today's first discovery window
        discovery_start = now.replace(hour=start_hour + 3, minute=start_min, second=0, microsecond=0)  # +3 for PT->ET

        if self.last_discovery is None:
            # No previous discovery - trigger if we're in a valid window
            # Check if current time aligns with discovery interval
            current_hour_et = now.hour
            hours_from_start = (current_hour_et - (start_hour + 3)) % 24
            if hours_from_start % self.discovery_interval_hours == 0:
                return True
            return False

        hours_since_discovery = (now.replace(tzinfo=None) - self.last_discovery).total_seconds() / 3600

        # Has discovery interval elapsed?
        if hours_since_discovery >= self.discovery_interval_hours:
            return True

        return False

    def trigger_scheduled_review(self):
        """
        Trigger scheduled strategic review (proactive check)

        Unlike VIX alerts (reactive to regime changes), scheduled reviews
        proactively scan for:
        - Emergent opportunities outside current strategy
        - Portfolio drift detection
        - News events that don't move VIX
        - AI sector trends and breakouts
        """
        try:
            logger.info("")
            logger.info("=" * 70)
            logger.info("[SCHEDULED REVIEW] PROACTIVE STRATEGIC CHECK")
            logger.info("=" * 70)

            # Get current portfolio context
            portfolio = self.executor.get_portfolio_summary()

            # Get portfolio health metrics (correlation and sector analysis)
            tickers = [p['ticker'] for p in portfolio.get('positions', [])]
            portfolio_health = {}

            if len(tickers) >= 2:
                try:
                    correlation = get_correlation(tickers)
                    portfolio_health['correlation'] = {
                        'diversification_score': correlation.get('diversification_score', 0),
                        'avg_correlation': correlation.get('avg_correlation', 0),
                        'assessment': correlation.get('assessment', 'UNKNOWN'),
                        'high_correlation_pairs': correlation.get('high_correlation_pairs', [])
                    }
                except Exception as e:
                    logger.warning(f"Could not get correlation data: {e}")
                    portfolio_health['correlation'] = {'error': str(e)}

            if len(tickers) >= 1:
                try:
                    sectors = get_sectors(tickers)
                    portfolio_health['sectors'] = {
                        'diversification_score': sectors.get('diversification_score', 0),
                        'largest_sector': sectors.get('largest_sector', 'Unknown'),
                        'largest_sector_pct': sectors.get('largest_sector_pct', 0),
                        'assessment': sectors.get('assessment', 'UNKNOWN'),
                        'concentration_risks': sectors.get('concentration_risks', [])
                    }
                except Exception as e:
                    logger.warning(f"Could not get sector data: {e}")
                    portfolio_health['sectors'] = {'error': str(e)}

            # Log portfolio health summary
            if portfolio_health.get('correlation'):
                corr = portfolio_health['correlation']
                logger.info(f"Portfolio Correlation: {corr.get('assessment', 'N/A')} (score: {corr.get('diversification_score', 0)}/100)")
            if portfolio_health.get('sectors'):
                sect = portfolio_health['sectors']
                logger.info(f"Sector Concentration: {sect.get('assessment', 'N/A')} (largest: {sect.get('largest_sector', 'N/A')} @ {sect.get('largest_sector_pct', 0):.1f}%)")

            # Create scheduled review alert
            alert = {
                'timestamp': datetime.now().isoformat(),
                'alert_type': 'SCHEDULED_REVIEW',
                'interval_hours': self.review_interval_hours,
                'reason': 'Proactive market opportunity scan',
                'portfolio_snapshot': portfolio,
                'portfolio_health': portfolio_health,
                'current_vix': self.previous_vix if self.previous_vix else 'N/A',
                'vix_regime': self.previous_vix_regime if self.previous_vix_regime else 'N/A',
                'status': 'pending'
            }

            # Write alert to file
            alert_file = 'scheduled_review_needed.json'
            with open(alert_file, 'w') as f:
                json.dump(alert, f, indent=2)

            logger.info(f"Review interval: Every {self.review_interval_hours} hours")
            logger.info(f"Alert written to: {alert_file}")
            logger.info("=" * 70)
            logger.info("")

            # Update last review time
            self.last_scheduled_review = datetime.now()
            self._save_last_review_time()

            # Invoke Claude strategy agent to process the review
            self._invoke_strategy_agent('scheduled')

        except Exception as e:
            logger.error(f"Error triggering scheduled review: {e}", exc_info=True)

    def trigger_discovery(self):
        """
        Trigger opportunity discovery scan

        Separate from strategy review - this scans the broader AI ecosystem
        for emerging opportunities, not just current positions. Runs less
        frequently (every 4 hours) and updates the watchlist.
        """
        try:
            logger.info("")
            logger.info("=" * 70)
            logger.info("[OPPORTUNITY DISCOVERY] SCANNING AI ECOSYSTEM")
            logger.info("=" * 70)

            if not self.scan_universe:
                logger.warning("No scan_universe configured in thresholds.json - skipping discovery")
                return

            # Get current portfolio for context
            portfolio = self.executor.get_portfolio_summary()
            current_holdings = [p['ticker'] for p in portfolio.get('positions', [])]

            # Build discovery prompt
            prompt = f"""Run an opportunity discovery scan for the AI ecosystem.

## Your Mission
Scan these tickers for STRONG BUY opportunities: {', '.join(self.scan_universe)}

Current holdings (already own): {', '.join(current_holdings)}

## Capital Constraints
- Cash available: ${portfolio.get('cash', 0):,.2f}
- {'ON MARGIN - prioritize clearing before new positions' if portfolio.get('cash', 0) < 0 else 'Cash available for new positions'}
- Opportunity reserve target: {self.opportunity_reserve_pct * 100:.0f}% of portfolio

## Analysis Required
For each ticker in scan_universe:
1. Get current technicals (RSI, MACD, SMA trends)
2. Check if STRONG BUY signal
3. If promising, note entry criteria

## Output Required
Update the watchlist with top opportunities:
- Ticker, signal strength, target entry price, reasoning
- Rank by conviction
- Note which current holdings to potentially trim to fund new positions

Focus on finding the BEST opportunities in the AI ecosystem right now.
"""

            # Write discovery alert
            alert = {
                'timestamp': datetime.now().isoformat(),
                'alert_type': 'OPPORTUNITY_DISCOVERY',
                'scan_universe': self.scan_universe,
                'current_holdings': current_holdings,
                'portfolio_cash': portfolio.get('cash', 0),
                'on_margin': portfolio.get('cash', 0) < 0,
                'status': 'pending'
            }

            alert_file = 'discovery_needed.json'
            with open(alert_file, 'w') as f:
                json.dump(alert, f, indent=2)

            logger.info(f"Scanning {len(self.scan_universe)} tickers")
            logger.info(f"Current holdings: {', '.join(current_holdings)}")
            logger.info(f"Alert written to: {alert_file}")
            logger.info("=" * 70)

            # Update last discovery time
            self.last_discovery = datetime.now()
            self._save_last_discovery_time()

            # Invoke Claude for discovery scan
            self._invoke_strategy_agent('discovery', prompt_override=prompt)

        except Exception as e:
            logger.error(f"Error triggering discovery: {e}", exc_info=True)

    def get_stop_loss_for_position(self, ticker: str, vix_regime: str = None) -> float:
        """
        Get VIX-adaptive stop-loss percentage for a specific position

        Args:
            ticker: Stock ticker symbol
            vix_regime: Current VIX regime (CALM/NORMAL/ELEVATED/HIGH)

        Returns:
            Stop-loss percentage (e.g., 0.15 for -15%)
        """
        # Check if position has specific override (for extreme beta stocks)
        if ticker in self.position_stop_losses:
            return self.position_stop_losses[ticker]

        # Use VIX-adaptive stop-loss if regime known
        if vix_regime and vix_regime in self.vix_stop_losses:
            return self.vix_stop_losses[vix_regime]

        # Default to base stop-loss
        return self.stop_loss_pct

    def execute_autonomous_defensive_actions(self, vix_regime: str):
        """
        Execute autonomous defensive actions based on VIX regime
        WITHOUT waiting for human approval

        This implements risk management to protect capital when user unavailable.

        Actions in ELEVATED regime (VIX 20-30):
        - Trim 50% of extreme beta positions (beta >2.0)
        - Tighten stop-losses to -15% (from -20%)

        Actions in HIGH regime (VIX >30):
        - Exit all extreme beta positions (beta >2.0)
        - Tighten stop-losses to -10%
        - Move to 70%+ cash position
        """
        if not self.autonomous_defense_enabled:
            logger.info("[AUTONOMOUS DEFENSE] Disabled - skipping defensive actions")
            return

        # Skip if no high-beta positions configured
        if not self.high_beta_positions:
            logger.info("[AUTONOMOUS DEFENSE] No high-beta positions configured - skipping")
            return

        logger.info(f"[AUTONOMOUS DEFENSE] VIX REGIME: {vix_regime}")

        portfolio = self.executor.get_portfolio_summary()
        positions = portfolio['positions']
        actions_taken = []

        # ELEVATED regime (VIX 20-30): Trim extreme beta positions
        if vix_regime == 'ELEVATED':
            logger.info("[ELEVATED REGIME] Implementing defensive trims:")

            for pos in positions:
                ticker = pos['ticker']
                if ticker not in self.high_beta_positions:
                    continue

                beta_info = self.high_beta_positions[ticker]

                # Trim 50% of extreme beta positions (beta >2.0)
                if beta_info['extreme'] and beta_info['beta'] > 2.0:
                    quantity = pos['quantity']
                    trim_qty = quantity * 0.5  # 50% trim

                    logger.info(f"[TRIM] {ticker} (beta {beta_info['beta']}): Selling 50% ({trim_qty:.4f} shares)")
                    logger.info(f"   Reason: Extreme beta risk in elevated volatility")
                    logger.info(f"   Current position: {quantity} shares")

                    # Execute trim
                    result = self.executor.execute_order(
                        ticker=ticker,
                        action='SELL',
                        quantity=trim_qty,
                        order_type='market'
                    )

                    actions_taken.append({
                        'type': 'DEFENSIVE_TRIM',
                        'ticker': ticker,
                        'quantity': trim_qty,
                        'reason': f'Extreme beta {beta_info["beta"]} in ELEVATED VIX',
                        'execution': result
                    })

                    logger.info(f"   Execution: {result['status']}")

                    # Set tighter stop-loss for remaining position
                    self.position_stop_losses[ticker] = 0.10  # -10% for extreme beta
                    logger.info(f"   New stop-loss: -10% (tightened from -20%)")

        # HIGH regime (VIX >30): Exit extreme beta entirely
        elif vix_regime == 'HIGH':
            logger.info("[HIGH REGIME] Implementing emergency defensive measures:")

            for pos in positions:
                ticker = pos['ticker']
                if ticker not in self.high_beta_positions:
                    continue

                beta_info = self.high_beta_positions[ticker]

                # Exit entire extreme beta positions
                if beta_info['extreme'] and beta_info['beta'] > 2.0:
                    quantity = pos['quantity']

                    logger.warning(f"[EXIT] {ticker} (beta {beta_info['beta']}): Selling 100% ({quantity:.4f} shares)")
                    logger.warning(f"   Reason: UNACCEPTABLE risk in HIGH volatility regime")

                    # Execute full exit
                    result = self.executor.execute_order(
                        ticker=ticker,
                        action='SELL',
                        quantity=quantity,
                        order_type='market'
                    )

                    actions_taken.append({
                        'type': 'DEFENSIVE_EXIT',
                        'ticker': ticker,
                        'quantity': quantity,
                        'reason': f'Extreme beta {beta_info["beta"]} in HIGH VIX',
                        'execution': result
                    })

                    logger.warning(f"   Execution: {result['status']}")

            # Tighten all remaining stops to -10%
            logger.info("[HIGH REGIME] All stop-losses tightened to -10%")
            self.stop_loss_pct = 0.10

        # Summary
        if actions_taken:
            logger.info("")
            logger.info(f"[AUTONOMOUS DEFENSE] {len(actions_taken)} defensive actions executed")
            logger.info("   These actions protect capital when user unavailable")
            logger.info("   Strategy Agent will review on next check-in")
        else:
            logger.info("[AUTONOMOUS DEFENSE] No defensive actions needed at this time")

        logger.info("=" * 70)
        logger.info("")

        return actions_taken

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

                # Hot-reload thresholds from config file
                self._load_thresholds()

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

                # Check VIX regime
                vix_result = self.check_vix_regime()
                current_vix_regime = None
                if vix_result:
                    vix_level, vix_regime, threshold_crossed = vix_result
                    current_vix_regime = vix_regime

                    # Trigger strategic review if regime crossed threshold
                    if threshold_crossed:
                        self.trigger_strategic_review_for_vix(vix_level, vix_regime)

                        # Execute autonomous defensive actions IMMEDIATELY
                        # Don't wait for Strategy Agent - protect capital now
                        if vix_regime in ['ELEVATED', 'HIGH']:
                            logger.info("[AUTONOMOUS] VIX regime change detected - executing defensive actions")
                            self.execute_autonomous_defensive_actions(vix_regime)

                    # Update previous VIX for next check
                    self.previous_vix = vix_level
                    self.previous_vix_regime = vix_regime

                # Check if scheduled review is due (proactive position checks)
                if self.check_if_review_due():
                    self.trigger_scheduled_review()

                # Check if opportunity discovery is due (broader market scan)
                if self.check_if_discovery_due():
                    self.trigger_discovery()

                # Display current status
                logger.info("\nCurrent Positions:")
                for pos in positions:
                    ticker = pos['ticker']
                    price = current_prices.get(ticker, pos['current_price'])
                    entry = pos['avg_cost']
                    pnl_pct = ((price - entry) / entry) * 100

                    # Get VIX-adaptive stop-loss for this position
                    stop_loss_pct = self.get_stop_loss_for_position(ticker, current_vix_regime)
                    stop_loss = entry * (1 - stop_loss_pct)

                    status = "[OK]" if price > stop_loss else "[NEAR STOP]"
                    stop_label = f"-{int(stop_loss_pct * 100)}%"
                    logger.info(f"  {ticker}: ${price:.2f} (entry: ${entry:.2f}, P&L: {pnl_pct:+.2f}%, stop: ${stop_loss:.2f} {stop_label}) {status}")

                # Check for actions
                actions = []

                # 1. Check stop-losses
                stop_loss_actions = self.check_stop_losses(positions, current_prices)
                actions.extend(stop_loss_actions)

                # 2. Check profit protection (trailing stops to lock in gains)
                profit_protection_actions = self.check_profit_protection(positions, current_prices)
                actions.extend(profit_protection_actions)

                # 3. Check dip-buying opportunities
                dip_buy_actions = self.check_dip_buying(positions, current_prices)
                actions.extend(dip_buy_actions)

                # 4. Check circuit breaker
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
        logger.info(f"MONITORING SESSION COMPLETE - {self.check_count} checks")


def main():
    """Entry point for execution monitor"""
    print("AutoInvestor Execution Monitor - Press Ctrl+C to stop")

    # Initialize and start monitoring (mode="alpaca" uses Alpaca API, paper vs live per ALPACA_PAPER env)
    monitor = ExecutionMonitor(mode="alpaca", check_interval_seconds=300)

    try:
        monitor.monitoring_loop()
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")


if __name__ == "__main__":
    main()
