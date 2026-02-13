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
from overnight_scanner import OvernightScanner

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
        self.thresholds_config = {}  # Full config dict for rotation trigger etc.

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

        # Initialize attributes BEFORE _load_thresholds() (which may override them)
        self.review_interval_hours = 1  # Default: hourly
        self.discovery_interval_hours = 4  # Default: every 4 hours
        self.discovery_start_time = "06:29"  # Default: 6:29 AM PT
        self.opportunity_reserve_pct = 0.15
        self.max_margin_pct = 0.10
        self.scan_universe = []
        self.watchlist_candidates = {}

        # Load thresholds from config file (overrides defaults above)
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

        # Load last review/discovery times from state files
        self.last_scheduled_review = None
        self._load_last_review_time()
        self.last_discovery = None
        self._load_last_discovery_time()

        # API resilience: retry logic and fallback tracking
        self.consecutive_api_failures = 0
        self.last_api_success = None
        self.max_retries = 3
        self.retry_delays = [5, 15, 45]  # seconds - exponential backoff

        # Load fallback rules config
        self.fallback_rules_enabled = True
        self._load_fallback_rules_config()

        # Defensive mode state (activated by circuit breaker)
        self.defensive_mode = False
        self.defensive_mode_entered_at = None
        self.defensive_stop_loss_pct = 0.10  # Tighter 10% stops in defensive mode
        self.defensive_loss_threshold = 0.10  # Close positions down >10%
        self.pre_defensive_portfolio_value = None

        # Overnight gap protection
        self.prior_close_value = None
        self.overnight_gap_threshold = 0.02  # 2% gap triggers defensive mode
        self.gap_check_done_today = False
        self._load_prior_close()

        # Overnight scanner for pre-market briefings
        self.overnight_scanner = OvernightScanner(executor=self.executor)
        self.last_overnight_scan = None
        self.last_premarket_briefing = None
        self._load_overnight_state()

        # Overnight scan schedule (PT times)
        self.overnight_scan_times = ["20:00", "02:00"]  # 8 PM, 2 AM PT
        self.premarket_briefing_time = "06:15"  # 6:15 AM PT
        self.weekend_briefing_time = "17:00"  # 5 PM PT Sunday for Monday prep

        # Rotation trigger state (vice index rotation during tech selloffs)
        self.rotation_mode = False
        self.rotation_entered_at = None
        self.rotation_trigger_threshold = 0.40  # 40% STRONG SELL triggers rotation
        self.rotation_recovery_threshold = 0.25  # 25% STRONG BUY exits rotation
        self._load_rotation_state()

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

    def _get_existing_short_tickers(self) -> List[str]:
        """Get list of tickers with existing short positions.

        Used to enforce hard-coded blocking of short stacking before agent invocation.
        Returns list of ticker symbols that already have short positions.
        """
        try:
            portfolio = self.executor.get_portfolio_summary()
            short_tickers = []
            for position in portfolio.get('positions', []):
                if position.get('quantity', 0) < 0:  # Negative qty = short
                    short_tickers.append(position['ticker'])
            return short_tickers
        except Exception as e:
            logger.error(f"Failed to get existing short positions: {e}")
            return []

    def _get_short_position_count(self) -> int:
        """Get count of current short positions."""
        return len(self._get_existing_short_tickers())

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

            # Determine if long or short position
            is_short = quantity < 0

            # Get VIX-adaptive stop-loss for this position
            stop_loss_pct = self.get_stop_loss_for_position(ticker, self.previous_vix_regime)

            if is_short:
                # SHORT position: stop-loss triggers if price RISES too much
                # For shorts, profit when price drops, loss when price rises
                stop_price = entry_price * (1 + stop_loss_pct)
                loss_pct = ((current_price - entry_price) / entry_price) * 100  # Positive = loss for shorts
                should_cover = current_price >= stop_price

                if should_cover:
                    logger.warning(f"[ALERT] SHORT STOP-LOSS TRIGGERED: {ticker}")
                    logger.info(f"   Short Entry: ${entry_price:.2f}")
                    logger.info(f"   Current: ${current_price:.2f}")
                    logger.info(f"   Loss: {loss_pct:.2f}%")

                    # Execute cover (buy back shares)
                    result = self.executor.execute_order(
                        ticker=ticker,
                        action='COVER',
                        quantity=abs(quantity),
                        order_type='market'
                    )

                    actions.append({
                        'type': 'STOP_LOSS_COVER',
                        'ticker': ticker,
                        'reason': f"Short stop-loss at +{stop_loss_pct*100:.0f}% (price rose to ${current_price:.2f})",
                        'quantity': abs(quantity),
                        'execution': result
                    })

                    logger.info(f"   Execution: {result['status']}")
            else:
                # LONG position: standard stop-loss (price drops)
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

    def _invoke_strategy_agent(self, trigger_type: str, context: str = "", prompt_override: str = None) -> bool:
        """
        Invoke Claude Code CLI to process a strategy review autonomously.

        Includes retry logic with exponential backoff for transient API failures.
        Falls back to rule-based decisions if all retries fail.

        Returns:
            bool: True if successful, False if all retries failed
        """
        import shutil
        import json as json_module

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
            interval_str = f"{int(self.review_interval_hours * 60)} minutes" if self.review_interval_hours < 1 else f"{self.review_interval_hours} hour(s)"

            # HARD-CODED SHORT POSITION BLOCKING
            # Get existing short tickers to prevent stacking
            existing_shorts = self._get_existing_short_tickers()
            short_count = len(existing_shorts)
            max_shorts = 2  # From thresholds.json short_selling.position_rules.max_short_positions

            if short_count >= max_shorts:
                short_block_msg = f"""
***** HARD BLOCK: NO NEW SHORTS ALLOWED *****
Current short positions: {short_count}/{max_shorts} (AT MAXIMUM)
Existing shorts: {', '.join(existing_shorts) if existing_shorts else 'none'}
DO NOT open ANY new short positions. Only manage existing shorts.
*********************************************"""
            elif existing_shorts:
                short_block_msg = f"""
***** BLOCKED TICKERS FOR SHORTING *****
Existing short positions ({short_count}/{max_shorts}): {', '.join(existing_shorts)}
DO NOT open new shorts in: {', '.join(existing_shorts)}
Only {max_shorts - short_count} new short position(s) allowed in OTHER tickers.
****************************************"""
            else:
                short_block_msg = f"""
Short positions: {short_count}/{max_shorts} (can open up to {max_shorts} new shorts)"""

            # Log the short position blocking status
            if existing_shorts:
                logger.info(f"[SHORT BLOCKING] Existing shorts: {existing_shorts} ({short_count}/{max_shorts})")
            else:
                logger.info(f"[SHORT BLOCKING] No existing shorts (0/{max_shorts})")

            prompt = f"""A scheduled strategy review is due (runs every {interval_str}).
Run /strategy-review to scan for opportunities and adjust positions as needed.
Check portfolio_health in scheduled_review_needed.json for correlation and sector data.
Also check the watchlist in thresholds.json for entry opportunities.

Capital rules:
- Maintain {self.opportunity_reserve_pct * 100:.0f}% opportunity reserve
- Max margin: {self.max_margin_pct * 100:.0f}% - clear margin ASAP when positions profit
{short_block_msg}

SHORT SELLING RULES (check thresholds.json short_selling section):
- Max 2 short positions total, max $1000 each
- Scan bearish_sectors for NEW candidates only (retail, legacy media, office REITs, fossil fuel, legacy auto)
- Look for: below 50-day SMA, RSI < 40, bearish MACD, weak fundamentals
- 10% stop-loss, 15% take-profit target
- CONSERVE DAY TRADES: Only 4 per 5 days. Prefer overnight holds. Only close same-day if stop/target hit.

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
        claude_path = shutil.which('claude') or 'claude'

        # Pass environment with auth token
        env = os.environ.copy()

        # Check which auth method is available
        has_oauth = bool(os.environ.get('CLAUDE_CODE_OAUTH_TOKEN'))
        has_api_key = bool(os.environ.get('ANTHROPIC_API_KEY')) and os.environ.get('ANTHROPIC_API_KEY') != 'your_anthropic_api_key_here'

        if not has_oauth and not has_api_key:
            logger.warning("[STRATEGY AGENT] No auth configured - need CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY")
            return False

        # Retry loop with exponential backoff
        for attempt in range(self.max_retries):
            try:
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
                    encoding='utf-8',
                    errors='replace',
                    timeout=600,
                    env=env
                )

                if result.returncode == 0:
                    # Success - reset failure counter
                    self.consecutive_api_failures = 0
                    self.last_api_success = datetime.now()

                    logger.info("[STRATEGY AGENT] Review completed successfully")
                    try:
                        output_data = json_module.loads(result.stdout)
                        cost = output_data.get('total_cost_usd', 0)
                        duration = output_data.get('duration_ms', 0) / 1000
                        response = output_data.get('result', '')
                        logger.info(f"   Duration: {duration:.1f}s | Cost: ${cost:.4f}")
                        logger.info(f"   Response: {response[:300]}...")

                        response_file = project_dir / 'last_agent_response.json'
                        with open(response_file, 'w') as f:
                            json_module.dump(output_data, f, indent=2)
                        logger.info(f"   Full response saved to: {response_file}")
                    except json_module.JSONDecodeError:
                        logger.info(f"   Output: {result.stdout[:500]}...")
                    return True
                else:
                    # Check if it's a retriable error (API 500, timeout, etc.)
                    stdout_str = result.stdout or ''
                    is_retriable = any(err in stdout_str for err in ['500', 'api_error', 'Internal server error', 'overloaded'])

                    if is_retriable and attempt < self.max_retries - 1:
                        delay = self.retry_delays[attempt]
                        logger.warning(f"[STRATEGY AGENT] API error (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s...")
                        time.sleep(delay)
                        continue
                    else:
                        # Non-retriable error or last attempt
                        logger.error(f"[STRATEGY AGENT] Failed with code {result.returncode}")
                        logger.error(f"   stdout: {result.stdout[:500] if result.stdout else '(none)'}")
                        logger.error(f"   stderr: {result.stderr[:500] if result.stderr else '(none)'}")
                        logger.error(f"   Claude path: {claude_path}")
                        logger.error(f"   Auth: OAuth={'yes' if has_oauth else 'no'}, API={'yes' if has_api_key else 'no'}")

                        if not is_retriable:
                            break  # Don't retry non-API errors

            except subprocess.TimeoutExpired:
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.warning(f"[STRATEGY AGENT] Timeout (attempt {attempt + 1}/{self.max_retries}), retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                else:
                    logger.error("[STRATEGY AGENT] Timed out after all retries")

            except FileNotFoundError:
                logger.warning("[STRATEGY AGENT] Claude CLI not found - review requires manual processing")
                break  # Can't retry if CLI not found

            except Exception as e:
                logger.error(f"[STRATEGY AGENT] Error invoking Claude: {e}", exc_info=True)
                if attempt < self.max_retries - 1:
                    delay = self.retry_delays[attempt]
                    logger.warning(f"[STRATEGY AGENT] Retrying in {delay}s...")
                    time.sleep(delay)
                    continue
                break

        # All retries exhausted - handle failure
        self.consecutive_api_failures += 1
        self._handle_api_failure(trigger_type, context)
        return False

    def _handle_api_failure(self, trigger_type: str, context: str = ""):
        """
        Handle persistent API failures - alert user and trigger fallback rules.

        Called after all retry attempts are exhausted.
        """
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "alert_type": "API_FAILURE",
            "consecutive_failures": self.consecutive_api_failures,
            "last_success": self.last_api_success.isoformat() if self.last_api_success else None,
            "trigger_type": trigger_type,
            "context": context,
            "message": f"Claude API unavailable after {self.max_retries} retries"
        }

        # Write alert file
        alert_file = Path(__file__).parent / 'api_failure_alert.json'
        with open(alert_file, 'w') as f:
            json.dump(alert_data, f, indent=2)

        logger.error(f"[API FAILURE] Claude unavailable - {self.consecutive_api_failures} consecutive failures")
        logger.error(f"   Alert written to: {alert_file}")

        # Try Windows toast notification
        try:
            from win10toast import ToastNotifier
            toaster = ToastNotifier()
            toaster.show_toast(
                "AutoInvestor Alert",
                f"Claude API down - falling back to rules ({self.consecutive_api_failures} failures)",
                duration=10,
                threaded=True
            )
        except ImportError:
            pass  # win10toast not installed
        except Exception as e:
            logger.warning(f"Could not show toast notification: {e}")

        # Trigger fallback rules if enabled and we've had multiple failures
        if self.fallback_rules_enabled and self.consecutive_api_failures >= 2:
            logger.info("[API FAILURE] Triggering fallback rules engine")
            self._execute_fallback_rules()

    def _execute_fallback_rules(self):
        """
        Execute deterministic trading rules when Claude is unavailable.

        These rules provide basic portfolio protection without AI:
        - RSI-based profit taking
        - Position size limits
        - Cash reserve enforcement
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("[FALLBACK RULES] Executing rule-based decisions (Claude unavailable)")
        logger.info("=" * 70)

        try:
            portfolio = self.executor.get_portfolio_summary()
            if not portfolio or not portfolio.get('positions'):
                logger.warning("[FALLBACK RULES] No portfolio data available")
                return

            actions_taken = []
            total_value = portfolio['total_value']
            cash = portfolio['cash']
            cash_pct = (cash / total_value) * 100 if total_value > 0 else 0

            # Get rule thresholds from config
            rsi_rules = self.fallback_rules.get('rsi_profit_taking', {})
            extreme_rules = self.fallback_rules.get('extreme_overbought', {})
            size_rules = self.fallback_rules.get('position_size_limit', {})
            cash_rules = self.fallback_rules.get('cash_reserve_floor', {})

            for pos in portfolio.get('positions', []):
                ticker = pos['ticker']
                qty = pos['quantity']
                pl_pct = pos.get('unrealized_pl_percent', 0)
                position_value = pos.get('market_value', 0)
                position_pct = (position_value / total_value) * 100 if total_value > 0 else 0
                current_price = pos.get('current_price', 0)

                # Get RSI for this ticker
                rsi = self._get_rsi_for_ticker(ticker)

                # Rule 1: RSI Profit Taking (RSI > 80 and profit > 20%)
                rsi_threshold = rsi_rules.get('rsi_threshold', 80)
                min_profit = rsi_rules.get('min_profit_pct', 20)
                trim_pct = rsi_rules.get('trim_pct', 0.25)

                if rsi and rsi > rsi_threshold and pl_pct > min_profit:
                    trim_qty = int(qty * trim_pct)
                    if trim_qty >= 1:
                        logger.info(f"[FALLBACK] Rule 1 triggered: {ticker} RSI={rsi:.1f}, P/L=+{pl_pct:.1f}% -> Trim {trim_pct*100:.0f}%")
                        try:
                            self.executor.execute_order(ticker, 'SELL', trim_qty, 'market')
                            actions_taken.append(f"Trimmed {ticker} {trim_pct*100:.0f}% (RSI {rsi:.0f}, +{pl_pct:.0f}% profit)")
                        except Exception as e:
                            logger.error(f"[FALLBACK] Failed to execute trim for {ticker}: {e}")
                        continue  # Don't apply multiple rules to same position

                # Rule 2: Extreme Overbought (RSI > 85 and profit > 30%)
                extreme_rsi = extreme_rules.get('rsi_threshold', 85)
                extreme_profit = extreme_rules.get('min_profit_pct', 30)
                extreme_trim = extreme_rules.get('trim_pct', 0.30)

                if rsi and rsi > extreme_rsi and pl_pct > extreme_profit:
                    trim_qty = int(qty * extreme_trim)
                    if trim_qty >= 1:
                        logger.info(f"[FALLBACK] Rule 2 triggered: {ticker} RSI={rsi:.1f}, P/L=+{pl_pct:.1f}% -> Trim {extreme_trim*100:.0f}%")
                        try:
                            self.executor.execute_order(ticker, 'SELL', trim_qty, 'market')
                            actions_taken.append(f"Trimmed {ticker} {extreme_trim*100:.0f}% (extreme overbought)")
                        except Exception as e:
                            logger.error(f"[FALLBACK] Failed to execute trim for {ticker}: {e}")
                        continue

                # Rule 3: Position Size Limit (position > 35% of portfolio)
                max_position = size_rules.get('max_position_pct', 35)
                target_position = size_rules.get('target_position_pct', 30)

                if position_pct > max_position:
                    target_value = total_value * (target_position / 100)
                    trim_value = position_value - target_value
                    trim_qty = int(trim_value / current_price) if current_price > 0 else 0
                    if trim_qty >= 1:
                        logger.info(f"[FALLBACK] Rule 3 triggered: {ticker} at {position_pct:.1f}% -> Trim to {target_position}%")
                        try:
                            self.executor.execute_order(ticker, 'SELL', trim_qty, 'market')
                            actions_taken.append(f"Trimmed {ticker} to {target_position}% (position limit)")
                        except Exception as e:
                            logger.error(f"[FALLBACK] Failed to execute trim for {ticker}: {e}")

            # Rule 4: Cash Reserve Floor (cash < 8% and best performer > 25% gain)
            min_cash = cash_rules.get('min_cash_pct', 8)
            min_profit_to_trim = cash_rules.get('min_profit_to_trim', 25)
            reserve_trim = cash_rules.get('trim_pct', 0.15)

            if cash_pct < min_cash and not actions_taken:
                # Find best performer
                positions = portfolio.get('positions', [])
                if positions:
                    best_pos = max(positions, key=lambda p: p.get('unrealized_pl_percent', 0))
                    if best_pos.get('unrealized_pl_percent', 0) > min_profit_to_trim:
                        ticker = best_pos['ticker']
                        qty = best_pos['quantity']
                        trim_qty = int(qty * reserve_trim)
                        if trim_qty >= 1:
                            logger.info(f"[FALLBACK] Rule 4 triggered: Cash={cash_pct:.1f}% -> Trim {ticker} {reserve_trim*100:.0f}%")
                            try:
                                self.executor.execute_order(ticker, 'SELL', trim_qty, 'market')
                                actions_taken.append(f"Trimmed {ticker} {reserve_trim*100:.0f}% (cash reserve)")
                            except Exception as e:
                                logger.error(f"[FALLBACK] Failed to execute trim for {ticker}: {e}")

            # Log summary
            if actions_taken:
                logger.info(f"[FALLBACK RULES] Executed {len(actions_taken)} actions:")
                for action in actions_taken:
                    logger.info(f"   - {action}")
                self._save_fallback_actions(actions_taken)
            else:
                logger.info("[FALLBACK RULES] No rule conditions met - portfolio OK")

        except Exception as e:
            logger.error(f"[FALLBACK RULES] Error executing fallback rules: {e}", exc_info=True)

    def _get_rsi_for_ticker(self, ticker: str) -> Optional[float]:
        """Get current RSI for a ticker"""
        try:
            from autoinvestor_api import get_technical_indicators
            indicators = get_technical_indicators(ticker)
            if indicators:
                return indicators.get('rsi')
        except Exception as e:
            logger.warning(f"Could not get RSI for {ticker}: {e}")
        return None

    def _save_fallback_actions(self, actions: list):
        """Save fallback actions to file for audit trail"""
        try:
            fallback_file = Path(__file__).parent / 'fallback_actions.json'
            with open(fallback_file, 'w') as f:
                json.dump({
                    "timestamp": datetime.now().isoformat(),
                    "actions": actions,
                    "reason": "Claude API unavailable",
                    "consecutive_failures": self.consecutive_api_failures
                }, f, indent=2)
            logger.info(f"[FALLBACK] Actions saved to: {fallback_file}")
        except Exception as e:
            logger.error(f"Could not save fallback actions: {e}")

    def _enter_defensive_mode(self, daily_loss_pct: float, portfolio_value: float):
        """
        Enter defensive mode when circuit breaker triggers.

        Instead of halting trading, we:
        1. Run emergency news scan
        2. Close positions down >10%
        3. Close all shorts (they spike in selloffs)
        4. Keep strong performers
        5. Invoke agent to pick safe haven for excess capital
        6. Continue monitoring with tighter stops
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("[DEFENSIVE MODE] CIRCUIT BREAKER TRIGGERED - ENTERING DEFENSIVE MODE")
        logger.info(f"   Daily Loss: {daily_loss_pct:.2f}%")
        logger.info(f"   Portfolio Value: ${portfolio_value:,.2f}")
        logger.info("=" * 70)

        self.defensive_mode = True
        self.defensive_mode_entered_at = datetime.now()
        self.pre_defensive_portfolio_value = portfolio_value

        actions_taken = []

        try:
            # 1. Emergency news scan
            logger.info("[DEFENSIVE MODE] Running emergency news scan...")
            try:
                news_data = self.overnight_scanner.scan_overnight_news()
                breaking_count = len(news_data.get('breaking_news', []))
                logger.info(f"[DEFENSIVE MODE] News scan complete - {breaking_count} breaking news items")
            except Exception as e:
                logger.error(f"[DEFENSIVE MODE] News scan failed: {e}")
                news_data = {}

            # 2. Get current positions and identify defensive actions
            portfolio = self.executor.get_portfolio_summary()
            positions = portfolio.get('positions', [])
            total_value = portfolio['total_value']
            cash = portfolio['cash']

            positions_to_close = []
            shorts_to_close = []
            strong_performers = []

            for pos in positions:
                ticker = pos['ticker']
                qty = pos['quantity']
                pl_pct = pos.get('unrealized_pl_percent', 0)

                if qty < 0:  # Short position
                    shorts_to_close.append({
                        'ticker': ticker,
                        'qty': abs(qty),
                        'pl_pct': pl_pct,
                        'value': abs(pos.get('market_value', 0))
                    })
                elif pl_pct < -self.defensive_loss_threshold * 100:  # Down >10%
                    positions_to_close.append({
                        'ticker': ticker,
                        'qty': qty,
                        'pl_pct': pl_pct,
                        'value': pos.get('market_value', 0)
                    })
                elif pl_pct > 5:  # Strong performers (>5% gain)
                    strong_performers.append({
                        'ticker': ticker,
                        'qty': qty,
                        'pl_pct': pl_pct,
                        'value': pos.get('market_value', 0)
                    })

            # 3. Close losing positions (down >10%)
            for pos in positions_to_close:
                logger.info(f"[DEFENSIVE MODE] Closing losing position: {pos['ticker']} ({pos['pl_pct']:.1f}%)")
                try:
                    self.executor.execute_order(pos['ticker'], 'SELL', int(pos['qty']), 'market')
                    actions_taken.append(f"Closed {pos['ticker']} (down {abs(pos['pl_pct']):.1f}%)")
                except Exception as e:
                    logger.error(f"[DEFENSIVE MODE] Failed to close {pos['ticker']}: {e}")

            # 4. Close all shorts
            for pos in shorts_to_close:
                logger.info(f"[DEFENSIVE MODE] Closing short: {pos['ticker']} ({pos['pl_pct']:.1f}%)")
                try:
                    self.executor.execute_order(pos['ticker'], 'BUY', int(pos['qty']), 'market')
                    actions_taken.append(f"Closed short {pos['ticker']}")
                except Exception as e:
                    logger.error(f"[DEFENSIVE MODE] Failed to close short {pos['ticker']}: {e}")

            # 5. Calculate capital for safe haven
            # Refresh portfolio after closes
            import time
            time.sleep(2)  # Wait for orders to fill
            updated_portfolio = self.executor.get_portfolio_summary()
            new_cash = updated_portfolio['cash']
            new_total = updated_portfolio['total_value']

            # Calculate opportunity reserve
            opportunity_reserve = new_total * self.opportunity_reserve_pct
            excess_cash = new_cash - opportunity_reserve

            logger.info(f"[DEFENSIVE MODE] Post-defensive state:")
            logger.info(f"   Cash: ${new_cash:,.2f}")
            logger.info(f"   Opportunity Reserve: ${opportunity_reserve:,.2f}")
            logger.info(f"   Excess for safe haven: ${excess_cash:,.2f}")

            # 6. Invoke agent for safe haven selection if we have excess capital
            if excess_cash > 1000:
                self._invoke_defensive_agent(
                    daily_loss_pct=daily_loss_pct,
                    news_data=news_data,
                    excess_cash=excess_cash,
                    strong_performers=strong_performers,
                    actions_taken=actions_taken
                )
            else:
                logger.info("[DEFENSIVE MODE] No excess capital for safe haven - holding cash")

            # 7. Log summary
            logger.info("")
            logger.info("=" * 70)
            logger.info("[DEFENSIVE MODE] DEFENSIVE ACTIONS COMPLETE")
            logger.info(f"   Positions closed: {len(positions_to_close)}")
            logger.info(f"   Shorts closed: {len(shorts_to_close)}")
            logger.info(f"   Strong performers kept: {len(strong_performers)}")
            logger.info(f"   Now using {self.defensive_stop_loss_pct*100:.0f}% stops (tighter)")
            logger.info("   Monitoring continues - will exit defensive mode when loss < 1%")
            logger.info("=" * 70)

            # Save defensive mode state
            self._save_defensive_state(actions_taken, daily_loss_pct)

        except Exception as e:
            logger.error(f"[DEFENSIVE MODE] Error entering defensive mode: {e}", exc_info=True)

    def _invoke_defensive_agent(self, daily_loss_pct: float, news_data: dict,
                                 excess_cash: float, strong_performers: list,
                                 actions_taken: list):
        """Invoke strategy agent to select safe haven for excess capital."""

        # Build context for agent
        breaking_news = news_data.get('breaking_news', [])[:5]  # Top 5 breaking news
        news_summary = "\n".join([
            f"- {item.get('headline', 'No headline')}"
            for item in breaking_news
        ]) if breaking_news else "No breaking news"

        strong_list = ", ".join([
            f"{p['ticker']} (+{p['pl_pct']:.1f}%)"
            for p in strong_performers[:5]
        ]) if strong_performers else "None"

        prompt = f"""DEFENSIVE MODE ACTIVATED - Circuit breaker triggered at {daily_loss_pct:.2f}% daily loss.

MARKET CONTEXT:
{news_summary}

DEFENSIVE ACTIONS TAKEN:
{chr(10).join(f'- {a}' for a in actions_taken) if actions_taken else '- None yet'}

CURRENT STRONG PERFORMERS:
{strong_list}

CAPITAL AVAILABLE: ${excess_cash:,.2f} (after opportunity reserve)

YOUR TASK:
1. Analyze the news - is this a market-wide selloff or position-specific?
2. Assess recovery likelihood
3. Choose a SAFE HAVEN for the excess capital:
   - Option A: Add to a current strong performer (less volatile, already winning)
   - Option B: Buy SPY/QQQ (broad market, diversified)
   - Option C: Buy defensive sector (XLU utilities, XLP consumer staples)
   - Option D: Hold cash (if expecting further downside)

Execute your chosen safe haven trade. Be conservative - we're in defensive mode.
Do NOT open any new speculative positions or shorts."""

        logger.info("[DEFENSIVE MODE] Invoking strategy agent for safe haven selection...")
        self._invoke_strategy_agent('defensive', 'Circuit breaker - safe haven selection', prompt_override=prompt)

    def _check_exit_defensive_mode(self, current_portfolio_value: float) -> bool:
        """
        Check if we should exit defensive mode.

        Exit conditions:
        - Daily loss recovered to <1%
        - New trading day started
        """
        if not self.defensive_mode:
            return False

        # Check if new trading day
        if self.defensive_mode_entered_at:
            now = datetime.now(self.eastern_tz)
            entered_date = self.defensive_mode_entered_at.date()
            if hasattr(self.defensive_mode_entered_at, 'astimezone'):
                entered_date = self.defensive_mode_entered_at.astimezone(self.eastern_tz).date()

            if now.date() > entered_date:
                logger.info("[DEFENSIVE MODE] New trading day - exiting defensive mode")
                self._exit_defensive_mode("New trading day")
                return True

        # Check if loss recovered
        if self.pre_defensive_portfolio_value:
            recovery_pct = (current_portfolio_value - self.pre_defensive_portfolio_value) / self.pre_defensive_portfolio_value * 100
            # We entered at ~2% loss, exit when recovered to <1% loss from that point
            if recovery_pct > 1.0:
                logger.info(f"[DEFENSIVE MODE] Loss recovered ({recovery_pct:.2f}%) - exiting defensive mode")
                self._exit_defensive_mode(f"Loss recovered to {recovery_pct:.2f}%")
                return True

        return False

    def _exit_defensive_mode(self, reason: str):
        """Exit defensive mode and return to normal trading."""
        logger.info("")
        logger.info("=" * 70)
        logger.info(f"[DEFENSIVE MODE] EXITING DEFENSIVE MODE")
        logger.info(f"   Reason: {reason}")
        logger.info(f"   Duration: {datetime.now() - self.defensive_mode_entered_at if self.defensive_mode_entered_at else 'Unknown'}")
        logger.info("   Returning to normal stop-loss levels")
        logger.info("=" * 70)

        self.defensive_mode = False
        self.defensive_mode_entered_at = None
        self.pre_defensive_portfolio_value = None

        # Save exit state
        try:
            state_file = Path(__file__).parent / 'defensive_mode_state.json'
            with open(state_file, 'w') as f:
                json.dump({
                    "active": False,
                    "exited_at": datetime.now().isoformat(),
                    "exit_reason": reason
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save defensive mode exit state: {e}")

    def _save_defensive_state(self, actions: list, daily_loss_pct: float):
        """Save defensive mode state to file."""
        try:
            state_file = Path(__file__).parent / 'defensive_mode_state.json'
            with open(state_file, 'w') as f:
                json.dump({
                    "active": True,
                    "entered_at": self.defensive_mode_entered_at.isoformat() if self.defensive_mode_entered_at else None,
                    "trigger_loss_pct": daily_loss_pct,
                    "pre_defensive_value": self.pre_defensive_portfolio_value,
                    "actions_taken": actions,
                    "stop_loss_pct": self.defensive_stop_loss_pct
                }, f, indent=2)
            logger.info(f"[DEFENSIVE MODE] State saved to: {state_file}")
        except Exception as e:
            logger.error(f"Could not save defensive mode state: {e}")

    def _get_current_stop_loss(self) -> float:
        """Get the current stop-loss percentage based on mode."""
        if self.defensive_mode:
            return self.defensive_stop_loss_pct
        return self.stop_loss_pct

    def _load_prior_close(self):
        """Load prior day's closing portfolio value from file."""
        try:
            state_file = Path(__file__).parent / 'prior_close_state.json'
            if state_file.exists():
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    self.prior_close_value = data.get('prior_close_value')
                    close_date = data.get('close_date')
                    logger.info(f"Loaded prior close: ${self.prior_close_value:,.2f} from {close_date}")
        except Exception as e:
            logger.warning(f"Could not load prior close state: {e}")
            self.prior_close_value = None

    def _save_prior_close(self, portfolio_value: float):
        """Save current portfolio value as prior close for next day's gap check."""
        try:
            state_file = Path(__file__).parent / 'prior_close_state.json'
            with open(state_file, 'w') as f:
                json.dump({
                    "prior_close_value": portfolio_value,
                    "close_date": datetime.now().strftime("%Y-%m-%d"),
                    "close_time": datetime.now().isoformat()
                }, f, indent=2)
            self.prior_close_value = portfolio_value
            logger.info(f"[MARKET CLOSE] Saved prior close: ${portfolio_value:,.2f}")
        except Exception as e:
            logger.error(f"Could not save prior close state: {e}")

    def _check_overnight_gap(self, current_portfolio_value: float) -> bool:
        """
        Check for overnight gap at market open.

        If portfolio opens down more than threshold from prior close,
        trigger defensive mode immediately.

        Returns:
            True if gap protection triggered, False otherwise
        """
        # Only check once per day, at/near market open
        if self.gap_check_done_today:
            return False

        # Need prior close to compare
        if not self.prior_close_value:
            logger.info("[GAP CHECK] No prior close available - skipping gap check")
            self.gap_check_done_today = True
            return False

        # Calculate overnight gap
        gap_pct = (current_portfolio_value - self.prior_close_value) / self.prior_close_value

        logger.info(f"[GAP CHECK] Prior close: ${self.prior_close_value:,.2f} | Current: ${current_portfolio_value:,.2f} | Gap: {gap_pct*100:.2f}%")

        self.gap_check_done_today = True

        # Check if gap exceeds threshold (negative = gap down)
        if gap_pct < -self.overnight_gap_threshold:
            logger.warning(f"[GAP PROTECTION] Overnight gap of {gap_pct*100:.2f}% exceeds -{self.overnight_gap_threshold*100:.0f}% threshold!")

            # Trigger defensive mode
            self._enter_defensive_mode(
                daily_loss_pct=abs(gap_pct) * 100,
                portfolio_value=current_portfolio_value
            )
            return True

        logger.info(f"[GAP CHECK] Gap within acceptable range - no action needed")
        return False

    def _reset_daily_gap_check(self):
        """Reset the gap check flag for a new trading day."""
        self.gap_check_done_today = False

    def _load_rotation_state(self):
        """Load rotation mode state from file."""
        try:
            state_file = Path(__file__).parent / 'rotation_state.json'
            if state_file.exists():
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    self.rotation_mode = data.get('rotation_mode', False)
                    if data.get('rotation_entered_at'):
                        self.rotation_entered_at = datetime.fromisoformat(data['rotation_entered_at'])
                    if self.rotation_mode:
                        logger.info(f"Loaded rotation state: ACTIVE since {self.rotation_entered_at}")
        except Exception as e:
            logger.warning(f"Could not load rotation state: {e}")
            self.rotation_mode = False

    def _save_rotation_state(self):
        """Save rotation mode state to file."""
        try:
            state_file = Path(__file__).parent / 'rotation_state.json'
            data = {
                'rotation_mode': self.rotation_mode,
                'rotation_entered_at': self.rotation_entered_at.isoformat() if self.rotation_entered_at else None,
                'last_updated': datetime.now().isoformat()
            }
            with open(state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save rotation state: {e}")

    def _check_rotation_trigger(self, positions: List[Dict]) -> Dict:
        """
        Check if rotation trigger conditions are met.
        Returns dict with rotation status and signal breakdown.
        """
        if not self.thresholds_config.get('rotation_trigger', {}).get('enabled', False):
            return {'triggered': False, 'reason': 'Rotation trigger disabled'}

        rotation_config = self.thresholds_config.get('rotation_trigger', {})
        trigger_threshold = rotation_config.get('strong_sell_threshold_pct', 0.40)
        recovery_threshold = rotation_config.get('recovery_threshold_pct', 0.25)

        # Count signals from positions
        total_positions = len([p for p in positions if p.get('quantity', 0) > 0])  # Long positions only
        if total_positions == 0:
            return {'triggered': False, 'reason': 'No positions to evaluate'}

        # Get technical signals for each position
        strong_sell_count = 0
        strong_buy_count = 0
        signals = {}

        for pos in positions:
            if pos.get('quantity', 0) <= 0:  # Skip shorts
                continue
            ticker = pos.get('ticker')
            try:
                from autoinvestor_api import get_technical_indicators
                tech = get_technical_indicators(ticker)
                signal = tech.get('signal', 'HOLD')
                signals[ticker] = signal

                if signal in ['STRONG SELL', 'SELL']:
                    strong_sell_count += 1
                elif signal in ['STRONG BUY', 'BUY']:
                    strong_buy_count += 1
            except Exception as e:
                signals[ticker] = 'UNKNOWN'

        strong_sell_pct = strong_sell_count / total_positions if total_positions > 0 else 0
        strong_buy_pct = strong_buy_count / total_positions if total_positions > 0 else 0

        result = {
            'total_positions': total_positions,
            'strong_sell_count': strong_sell_count,
            'strong_buy_count': strong_buy_count,
            'strong_sell_pct': strong_sell_pct,
            'strong_buy_pct': strong_buy_pct,
            'signals': signals,
            'trigger_threshold': trigger_threshold,
            'recovery_threshold': recovery_threshold
        }

        # Check if we should enter rotation mode
        if not self.rotation_mode and strong_sell_pct >= trigger_threshold:
            result['triggered'] = True
            result['action'] = 'ENTER_ROTATION'
            result['reason'] = f"{strong_sell_pct*100:.0f}% positions STRONG SELL (threshold: {trigger_threshold*100:.0f}%)"
            return result

        # Check if we should exit rotation mode
        if self.rotation_mode:
            # Exit if recovery threshold met
            if strong_buy_pct >= recovery_threshold:
                result['triggered'] = True
                result['action'] = 'EXIT_ROTATION'
                result['reason'] = f"{strong_buy_pct*100:.0f}% positions STRONG BUY (recovery threshold: {recovery_threshold*100:.0f}%)"
                return result

            # Exit if max days exceeded
            max_days = rotation_config.get('exit_conditions', {}).get('max_rotation_days', 10)
            if self.rotation_entered_at:
                days_in_rotation = (datetime.now() - self.rotation_entered_at).days
                if days_in_rotation >= max_days:
                    result['triggered'] = True
                    result['action'] = 'EXIT_ROTATION'
                    result['reason'] = f"Max rotation period exceeded ({days_in_rotation} days)"
                    return result

            result['triggered'] = False
            result['reason'] = f"In rotation mode - waiting for recovery ({strong_buy_pct*100:.0f}% STRONG BUY, need {recovery_threshold*100:.0f}%)"
            return result

        result['triggered'] = False
        result['reason'] = f"Normal mode - {strong_sell_pct*100:.0f}% STRONG SELL (threshold: {trigger_threshold*100:.0f}%)"
        return result

    def _enter_rotation_mode(self, rotation_check: Dict):
        """Enter rotation mode - rotate from STRONG SELL tech to vice index."""
        logger.info("=" * 70)
        logger.info("[ROTATION MODE] ENTERING VICE INDEX ROTATION")
        logger.info(f"   Reason: {rotation_check.get('reason', 'Unknown')}")
        logger.info(f"   Signals: {rotation_check.get('signals', {})}")
        logger.info("=" * 70)

        self.rotation_mode = True
        self.rotation_entered_at = datetime.now()
        self._save_rotation_state()

        # Invoke strategy agent with rotation context
        vice_config = self.thresholds_config.get('rotation_trigger', {}).get('vice_index', {})
        vice_tickers = vice_config.get('tickers', [])

        rotation_prompt = f"""ROTATION MODE ACTIVATED - Tech selloff detected.

{rotation_check.get('strong_sell_pct', 0)*100:.0f}% of positions showing STRONG SELL signals.

ROTATION INSTRUCTIONS:
1. Sell positions with STRONG SELL signals (preserve STRONG BUY positions)
2. Rotate proceeds into vice index stocks: {', '.join(vice_tickers)}
3. Max 25% of portfolio in vice stocks
4. Prefer high-dividend names (MO, PM, BTI)

Vice categories:
- Tobacco: MO, PM, BTI (defensive, high yield)
- Alcohol: STZ, TAP (consumer staples)
- Gambling: LVS, MGM, WYNN, CZR, DKNG

Run /strategy-review with rotation mode active."""

        self._invoke_strategy_agent('rotation', rotation_prompt)

    def _exit_rotation_mode(self, rotation_check: Dict):
        """Exit rotation mode - rotate back to tech."""
        logger.info("=" * 70)
        logger.info("[ROTATION MODE] EXITING - Returning to tech focus")
        logger.info(f"   Reason: {rotation_check.get('reason', 'Unknown')}")
        logger.info("=" * 70)

        self.rotation_mode = False
        self.rotation_entered_at = None
        self._save_rotation_state()

        # Invoke strategy agent to rotate back
        exit_prompt = f"""ROTATION MODE ENDED - Tech recovery detected.

{rotation_check.get('strong_buy_pct', 0)*100:.0f}% of positions showing STRONG BUY signals.

EXIT ROTATION INSTRUCTIONS:
1. Evaluate vice index positions for exit
2. Rotate proceeds back into AI/tech ecosystem per strategy_focus
3. Prioritize STRONG BUY signals from watchlist

Run /strategy-review to execute rotation exit."""

        self._invoke_strategy_agent('rotation_exit', exit_prompt)

    def check_dip_buying(self, positions: List[Dict], current_prices: Dict[str, float]) -> List[Dict]:
        """Check for dip-buying opportunities on configured tickers"""
        actions = []

        # Skip if in defensive mode - no new buys allowed
        if self.defensive_mode:
            return actions

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

            # Store full config for rotation trigger and other features
            self.thresholds_config = config

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

    def _load_fallback_rules_config(self):
        """Load fallback rules configuration from thresholds.json"""
        try:
            if not self.thresholds_file.exists():
                # Use defaults
                self.fallback_rules = {
                    'enabled': True,
                    'rsi_profit_taking': {'rsi_threshold': 80, 'min_profit_pct': 20, 'trim_pct': 0.25},
                    'extreme_overbought': {'rsi_threshold': 85, 'min_profit_pct': 30, 'trim_pct': 0.30},
                    'position_size_limit': {'max_position_pct': 35, 'target_position_pct': 30},
                    'cash_reserve_floor': {'min_cash_pct': 8, 'min_profit_to_trim': 25, 'trim_pct': 0.15}
                }
                return

            with open(self.thresholds_file, 'r') as f:
                config = json.load(f)

            if 'fallback_rules' in config:
                self.fallback_rules = config['fallback_rules']
                self.fallback_rules_enabled = self.fallback_rules.get('enabled', True)
            else:
                # Use defaults if not in config
                self.fallback_rules = {
                    'enabled': True,
                    'rsi_profit_taking': {'rsi_threshold': 80, 'min_profit_pct': 20, 'trim_pct': 0.25},
                    'extreme_overbought': {'rsi_threshold': 85, 'min_profit_pct': 30, 'trim_pct': 0.30},
                    'position_size_limit': {'max_position_pct': 35, 'target_position_pct': 30},
                    'cash_reserve_floor': {'min_cash_pct': 8, 'min_profit_to_trim': 25, 'trim_pct': 0.15}
                }
        except Exception as e:
            logger.warning(f"Error loading fallback rules config: {e} - using defaults")
            self.fallback_rules = {
                'enabled': True,
                'rsi_profit_taking': {'rsi_threshold': 80, 'min_profit_pct': 20, 'trim_pct': 0.25},
                'extreme_overbought': {'rsi_threshold': 85, 'min_profit_pct': 30, 'trim_pct': 0.30},
                'position_size_limit': {'max_position_pct': 35, 'target_position_pct': 30},
                'cash_reserve_floor': {'min_cash_pct': 8, 'min_profit_to_trim': 25, 'trim_pct': 0.15}
            }

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
                    # - Moving up: NORMAL -> ELEVATED, ELEVATED -> HIGH
                    # - Moving down: HIGH -> ELEVATED, ELEVATED -> NORMAL
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
                        logger.warning(f"[VIX REGIME CHANGE] {self.previous_vix_regime} -> {current_regime}")

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

            logger.info(f"VIX: {self.previous_vix:.2f} ({self.previous_vix_regime}) -> {vix_level:.2f} ({regime})")
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

    def _load_overnight_state(self):
        """Load overnight scanner state"""
        state_file = 'overnight_state.json'
        try:
            if Path(state_file).exists():
                with open(state_file, 'r') as f:
                    data = json.load(f)
                    if 'last_overnight_scan' in data:
                        self.last_overnight_scan = datetime.fromisoformat(data['last_overnight_scan'])
                    if 'last_premarket_briefing' in data:
                        self.last_premarket_briefing = datetime.fromisoformat(data['last_premarket_briefing'])
                    logger.info(f"Loaded overnight state - last scan: {self.last_overnight_scan}, last briefing: {self.last_premarket_briefing}")
        except Exception as e:
            logger.warning(f"Could not load overnight state: {e}")

    def _save_overnight_state(self):
        """Save overnight scanner state"""
        state_file = 'overnight_state.json'
        try:
            with open(state_file, 'w') as f:
                json.dump({
                    'last_overnight_scan': self.last_overnight_scan.isoformat() if self.last_overnight_scan else None,
                    'last_premarket_briefing': self.last_premarket_briefing.isoformat() if self.last_premarket_briefing else None
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save overnight state: {e}")

    def _check_overnight_schedule(self):
        """
        Check if overnight news scan or pre-market briefing is due.
        Runs during non-market hours.
        """
        pacific_tz = pytz.timezone('US/Pacific')
        now_pt = datetime.now(pacific_tz)
        current_time_str = now_pt.strftime("%H:%M")
        today = now_pt.date()

        # Check for overnight scan times (8 PM, 2 AM PT)
        for scan_time in self.overnight_scan_times:
            scan_hour, scan_min = map(int, scan_time.split(':'))

            # Check if we're within 5 minutes of scan time
            scan_datetime = now_pt.replace(hour=scan_hour, minute=scan_min, second=0, microsecond=0)
            time_diff = abs((now_pt - scan_datetime).total_seconds())

            if time_diff < 300:  # Within 5 minutes
                # Check if already scanned today at this time
                if self.last_overnight_scan:
                    last_scan_pt = self.last_overnight_scan.astimezone(pacific_tz) if self.last_overnight_scan.tzinfo else pacific_tz.localize(self.last_overnight_scan)
                    hours_since_scan = (now_pt - last_scan_pt).total_seconds() / 3600

                    if hours_since_scan < 4:  # Don't scan if scanned within 4 hours
                        return

                logger.info("")
                logger.info("=" * 70)
                logger.info("[OVERNIGHT SCAN] Running scheduled overnight news scan")
                logger.info(f"   Time: {current_time_str} PT")
                logger.info("=" * 70)

                try:
                    self.overnight_scanner.scan_overnight_news()
                    self.overnight_scanner.get_earnings_calendar()
                    self.last_overnight_scan = datetime.now()
                    self._save_overnight_state()
                    logger.info("[OVERNIGHT SCAN] Complete")
                except Exception as e:
                    logger.error(f"[OVERNIGHT SCAN] Error: {e}")

                return

        # Check for pre-market briefing time (6:15 AM PT)
        brief_hour, brief_min = map(int, self.premarket_briefing_time.split(':'))
        brief_datetime = now_pt.replace(hour=brief_hour, minute=brief_min, second=0, microsecond=0)
        time_diff = abs((now_pt - brief_datetime).total_seconds())

        if time_diff < 300:  # Within 5 minutes
            # Check if already briefed today
            if self.last_premarket_briefing:
                last_brief_pt = self.last_premarket_briefing.astimezone(pacific_tz) if self.last_premarket_briefing.tzinfo else pacific_tz.localize(self.last_premarket_briefing)
                if last_brief_pt.date() == today:
                    return  # Already briefed today

            logger.info("")
            logger.info("=" * 70)
            logger.info("[PRE-MARKET BRIEFING] Generating morning briefing and invoking strategy agent")
            logger.info(f"   Time: {current_time_str} PT")
            logger.info("=" * 70)

            try:
                # Generate briefing
                briefing = self.overnight_scanner.generate_premarket_briefing()

                # Get agent prompt
                prompt = self.overnight_scanner.get_premarket_agent_prompt()

                # Invoke strategy agent
                self._invoke_strategy_agent('premarket', 'Pre-market overnight analysis', prompt_override=prompt)

                self.last_premarket_briefing = datetime.now()
                self._save_overnight_state()
                logger.info("[PRE-MARKET BRIEFING] Complete")
            except Exception as e:
                logger.error(f"[PRE-MARKET BRIEFING] Error: {e}")

        # Check for Sunday weekend briefing (5 PM PT Sunday for Monday prep)
        is_sunday = now_pt.weekday() == 6
        if is_sunday:
            brief_hour, brief_min = map(int, self.weekend_briefing_time.split(':'))
            weekend_brief_datetime = now_pt.replace(hour=brief_hour, minute=brief_min, second=0, microsecond=0)
            time_diff = abs((now_pt - weekend_brief_datetime).total_seconds())

            # Debug logging for weekend briefing check (when near target time)
            if time_diff < 600:  # Within 10 minutes of target
                logger.info(f"[WEEKEND DEBUG] Sunday {current_time_str} PT | Target: {self.weekend_briefing_time} | time_diff: {time_diff:.0f}s | will_trigger: {time_diff < 300}")

            if time_diff < 300:  # Within 5 minutes
                # Check if already ran today
                last_weekend = getattr(self, 'last_weekend_briefing', None)
                if last_weekend:
                    last_weekend_pt = last_weekend.astimezone(pacific_tz) if last_weekend.tzinfo else pacific_tz.localize(last_weekend)
                    if last_weekend_pt.date() == today:
                        return

                logger.info("")
                logger.info("=" * 70)
                logger.info("[WEEKEND BRIEFING] Generating Monday preparation briefing")
                logger.info(f"   Time: {current_time_str} PT (Sunday)")
                logger.info("=" * 70)

                try:
                    briefing = self.overnight_scanner.generate_weekend_briefing()
                    self.last_weekend_briefing = datetime.now()
                    logger.info("[WEEKEND BRIEFING] Complete - Monday brief ready")
                except Exception as e:
                    logger.error(f"[WEEKEND BRIEFING] Error: {e}")

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

            # Update last review time (use Eastern time to match check_if_review_due)
            self.last_scheduled_review = datetime.now(self.eastern_tz).replace(tzinfo=None)
            self._save_last_review_time()

            # Check rotation trigger before invoking agent
            positions = portfolio.get('positions', [])
            rotation_check = self._check_rotation_trigger(positions)

            if rotation_check.get('triggered'):
                action = rotation_check.get('action')
                if action == 'ENTER_ROTATION':
                    self._enter_rotation_mode(rotation_check)
                    return  # Agent invoked by rotation mode
                elif action == 'EXIT_ROTATION':
                    self._exit_rotation_mode(rotation_check)
                    return  # Agent invoked by rotation exit

            # Log rotation status if in rotation mode
            if self.rotation_mode:
                logger.info(f"[ROTATION MODE] Active - {rotation_check.get('reason', '')}")

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

## Analysis Required - LONG Opportunities
For each ticker in scan_universe:
1. Get current technicals (RSI, MACD, SMA trends)
2. Check if STRONG BUY signal
3. If promising, note entry criteria

## SHORT SELLING - Test Mode Active (check thresholds.json)
ALSO scan for SHORT candidates from weak sectors:
- Traditional Retail (M, GPS, VFC)
- Legacy Media (PARA, WBD)
- Office REITs (MPW)
- Fossil Fuel (SLB, OXY)
- Legacy Auto (non-EV)

Short criteria: below 200-day SMA, RSI < 40, bearish MACD, weak fundamentals
- $2500 test allocation total, max $1000 per position
- 10% stop-loss, 15% take-profit
- Use SHORT to open, COVER to close

## Output Required
Update the watchlist with top opportunities:
- LONG: Ticker, signal strength, target entry price, reasoning
- SHORT: Ticker, bearish signal, entry price, stop-loss level
- Rank by conviction
- Note which current holdings to potentially trim to fund new positions

Focus on finding the BEST opportunities - both long AND short.
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
        # In defensive mode, use tighter stops for everything
        if self.defensive_mode:
            return self.defensive_stop_loss_pct

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

                    # If we were just in market hours, save prior close
                    if self.check_count > 0 and not self.gap_check_done_today:
                        # We just exited market hours - this shouldn't happen normally
                        # But handle gracefully
                        pass
                    elif self.check_count > 0:
                        # Market just closed - save portfolio value for tomorrow's gap check
                        try:
                            portfolio = self.executor.get_portfolio_summary()
                            self._save_prior_close(portfolio['total_value'])
                            # Reset for next day
                            self._reset_daily_gap_check()
                            self.check_count = 0
                        except Exception as e:
                            logger.error(f"Could not save prior close: {e}")

                    logger.info(f"Outside market hours ({now.strftime('%H:%M')} ET) - sleeping...")

                    # Check overnight schedule (news scans, pre-market briefing)
                    self._check_overnight_schedule()

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

                # Check for overnight gap on first check of the day
                if self.check_count == 1 or not self.gap_check_done_today:
                    gap_triggered = self._check_overnight_gap(portfolio['total_value'])
                    if gap_triggered:
                        # Defensive mode entered, refresh portfolio after defensive trades
                        portfolio = self.executor.get_portfolio_summary()
                        positions = portfolio['positions']

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
                    quantity = pos['quantity']
                    is_short = quantity < 0

                    # Get VIX-adaptive stop-loss for this position
                    stop_loss_pct = self.get_stop_loss_for_position(ticker, current_vix_regime)

                    if is_short:
                        # Short position: profit when price drops, loss when rises
                        pnl_pct = ((entry - price) / entry) * 100  # Inverted for shorts
                        stop_loss = entry * (1 + stop_loss_pct)  # Stop ABOVE entry
                        status = "[OK]" if price < stop_loss else "[NEAR STOP]"
                        stop_label = f"+{int(stop_loss_pct * 100)}%"
                        pos_type = "SHORT"
                    else:
                        # Long position: profit when price rises
                        pnl_pct = ((price - entry) / entry) * 100
                        stop_loss = entry * (1 - stop_loss_pct)  # Stop BELOW entry
                        status = "[OK]" if price > stop_loss else "[NEAR STOP]"
                        stop_label = f"-{int(stop_loss_pct * 100)}%"
                        pos_type = ""

                    pos_prefix = f"{pos_type} " if pos_type else ""
                    logger.info(f"  {pos_prefix}{ticker}: ${price:.2f} (entry: ${entry:.2f}, P&L: {pnl_pct:+.2f}%, stop: ${stop_loss:.2f} {stop_label}) {status}")

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

                if breaker_triggered and not self.defensive_mode:
                    # Enter defensive mode instead of halting
                    self._enter_defensive_mode(
                        daily_loss_pct=breaker_info['daily_loss_pct'],
                        portfolio_value=updated_portfolio['total_value']
                    )
                    # Continue monitoring, don't break

                # Check if we should exit defensive mode
                if self.defensive_mode:
                    self._check_exit_defensive_mode(updated_portfolio['total_value'])

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
