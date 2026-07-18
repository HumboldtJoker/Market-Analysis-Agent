"""Sovereign execution — turn signals into orders, enforce stops. PAPER FIRST.

Safety rails:
  - Refuses to run against a live account unless SOVEREIGN_LIVE_CONFIRM=yes
    is explicitly set (belt and suspenders on top of ALPACA_PAPER).
  - Circuit breaker checked before anything.
  - Only trades when the market is open (fractional orders require DAY/market).
  - Every order is logged to sovereign_state/trade_log.jsonl with the full
    reasoning chain — signal components, risk sizing math, thesis.

Commands:
    python3 sovereign_execute.py execute   # act on the latest scan's signals
    python3 sovereign_execute.py manage    # enforce synthetic stops/targets
    python3 sovereign_execute.py status    # positions vs tracked state
"""

import argparse
import json
import logging
import os
from datetime import datetime

from sovereign_config import (RESULTS_DIR, RISK, STATE_DIR, alpaca_keys, load_json)
from risk_engine import (check_circuit_breaker, clear_position, evaluate_exits,
                         load_positions_state, record_entry, size_position)
from sovereign_alerts import alert

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("execute")

TRADE_LOG = STATE_DIR / "trade_log.jsonl"


def _trading_client():
    from alpaca.trading.client import TradingClient
    key, secret, paper = alpaca_keys()
    if not paper and os.environ.get("SOVEREIGN_LIVE_CONFIRM", "") != "yes":
        raise RuntimeError(
            "ALPACA_PAPER=false but SOVEREIGN_LIVE_CONFIRM is not 'yes'. "
            "Refusing to trade live money. The strategy proves itself on paper first.")
    return TradingClient(key, secret, paper=paper), paper


def _log_trade(record: dict):
    record["timestamp"] = datetime.now().isoformat()
    with open(TRADE_LOG, "a") as f:
        f.write(json.dumps(record, default=str) + "\n")


def _latest_scan() -> dict:
    scans = sorted(RESULTS_DIR.glob("scan_*.json"), reverse=True)
    return load_json(scans[0], {}) if scans else {}


def _latest_signals() -> dict:
    snaps = sorted(RESULTS_DIR.glob("signals_*.json"), reverse=True)
    return load_json(snaps[0], {}) if snaps else {}


def _market_open(client) -> bool:
    try:
        return client.get_clock().is_open
    except Exception as e:
        log.warning("Clock check failed: %s", e)
        return False


def _submit_notional_buy(client, ticker: str, notional: float):
    from alpaca.trading.enums import OrderSide, TimeInForce
    from alpaca.trading.requests import MarketOrderRequest
    order = client.submit_order(MarketOrderRequest(
        symbol=ticker, notional=round(notional, 2),
        side=OrderSide.BUY, time_in_force=TimeInForce.DAY))
    return order


def _submit_sell_all(client, ticker: str):
    return client.close_position(ticker)


def execute():
    client, paper = _trading_client()
    account = client.get_account()

    if check_circuit_breaker(account):
        log.error("HALTED — circuit breaker active. No new entries today.")
        alert("Circuit breaker active", ["No new entries today."], level="critical")
        return

    if not _market_open(client):
        log.info("Market closed — fractional orders need an open market. Skipping.")
        return

    scan = _latest_scan()
    sigs = _latest_signals()
    if not scan or not sigs:
        log.info("No recent scan/signal snapshot. Run a scan first.")
        return
    scan_age_h = (datetime.now()
                  - datetime.fromisoformat(sigs["timestamp"])).total_seconds() / 3600
    if scan_age_h > 4:
        log.info("Signal snapshot is %.1fh old — stale, skipping execution.", scan_age_h)
        return

    positions = client.get_all_positions()
    equity = float(account.equity)
    cash = float(account.cash)
    regime_mult = (scan.get("macro") or {}).get("exposure_multiplier", 0.75)

    theses = {t["ticker"]: t for t in scan.get("theses", [])}
    from sovereign_pipeline import SECTOR_MAP

    candidates = []
    for ticker, s in sigs.get("signals", {}).items():
        if s["conviction"] not in ("high", "medium"):
            continue
        th = theses.get(ticker, {})
        if th.get("direction") != "buy":
            continue  # Claude veto: composite hot but thesis says no → no trade
        candidates.append((s["score"], ticker, s, th))
    candidates.sort(reverse=True)

    if not candidates:
        log.info("No candidates pass composite+thesis agreement. Patience is a position.")
        return

    placed = []
    for score, ticker, s, th in candidates:
        earnings_flag = any("Earnings" in f for f in s.get("risk_flags", []))
        entry = float(th.get("entry_price") or 0)
        stop = float(th.get("stop_loss") or 0)
        stop_pct = (entry - stop) / entry if entry > 0 and 0 < stop < entry else RISK["stop_loss_pct"]

        sizing = size_position(equity, cash, s["conviction"], regime_mult,
                               positions, SECTOR_MAP, ticker,
                               stop_pct=stop_pct, earnings_imminent=earnings_flag)
        if sizing["notional"] <= 0:
            log.info("SKIP %s: %s", ticker, "; ".join(sizing["reasons"]))
            continue

        try:
            order = _submit_notional_buy(client, ticker, sizing["notional"])
        except Exception as e:
            log.error("Order failed for %s: %s", ticker, e)
            continue

        stop_price = round(entry * (1 - stop_pct), 2) if entry > 0 else 0
        target = float(th.get("target") or 0) or round(entry * (1 + RISK["target_pct"]), 2)
        record_entry(ticker, entry, sizing["notional"], stop_price, target,
                     reason=th.get("reasoning", ""))
        _log_trade({"action": "buy", "ticker": ticker, "notional": sizing["notional"],
                    "composite": score, "conviction": s["conviction"],
                    "sizing": sizing["reasons"], "stop": stop_price, "target": target,
                    "thesis": th.get("reasoning", ""), "order_id": str(order.id),
                    "paper": paper})
        placed.append(f"{ticker} ${sizing['notional']:.2f} (stop {stop_price}, target {target})")
        log.info("BUY %s $%.2f — %s", ticker, sizing["notional"], "; ".join(sizing["reasons"]))
        try:
            from sovereign_memory import SovereignMemory
            mem = SovereignMemory()
            mem.write_entry(ticker, entry, s["conviction"],
                            th.get("reasoning", ""), str(s.get("explain", "")),
                            SECTOR_MAP.get(ticker, ""), score)
            mem.close()
        except Exception as e:
            log.debug("Memory write failed: %s", e)
        cash -= sizing["notional"]

    if placed:
        alert("Orders placed" + (" [PAPER]" if paper else " [LIVE]"),
              placed, level="signal", dedupe=False)


def manage():
    client, paper = _trading_client()
    account = client.get_account()
    check_circuit_breaker(account)  # trips halt for today if breached

    positions = client.get_all_positions()
    if not positions:
        log.info("No positions to manage.")
        return

    # Evaluate first so untracked positions get adopted (stop/target recorded)
    # even outside market hours; orders only go out when the market is open.
    actions = evaluate_exits(positions)
    if not _market_open(client):
        if actions:
            log.info("Market closed — %d exit(s) queue for the next open session.", len(actions))
        return

    for action in actions:
        ticker = action["ticker"]
        try:
            _submit_sell_all(client, ticker)
        except Exception as e:
            log.error("Exit failed for %s: %s", ticker, e)
            continue
        clear_position(ticker)
        _log_trade({"action": "sell", "ticker": ticker, "why": action["why"], "paper": paper})
        log.info("SELL %s — %s", ticker, action["why"])
        alert(f"Exit: {ticker}", [action["why"]], level="warning", dedupe=False)
        try:
            from sovereign_memory import SovereignMemory
            why = action.get("why", "")
            reason = "stop" if "STOP" in why.upper() else "target" if "TARGET" in why.upper() else "manual"
            exit_price = 0
            import re
            price_match = re.search(r"(\d+\.?\d*)\s*[<>=]", why)
            if price_match:
                exit_price = float(price_match.group(1))
            mem = SovereignMemory()
            mem.write_exit(ticker, exit_price, reason, 0)
            mem.close()
        except Exception as e:
            log.debug("Memory exit write failed: %s", e)


def status():
    client, paper = _trading_client()
    account = client.get_account()
    positions = client.get_all_positions()
    state = load_positions_state()

    print(f"\nSOVEREIGN EXECUTION STATUS — {'PAPER' if paper else 'LIVE'}")
    print(f"Equity ${float(account.equity):.2f} | Cash ${float(account.cash):.2f} | "
          f"Halted: {load_json(STATE_DIR / 'halt.json', {}).get('date') == datetime.now().strftime('%Y-%m-%d')}")
    for p in positions:
        st = state.get(p.symbol, {})
        print(f"  {p.symbol:6s} {float(p.qty):.4f} @ {float(p.avg_entry_price):.2f} → "
              f"{float(p.current_price):.2f} ({float(p.unrealized_plpc) * 100:+.1f}%) "
              f"| stop {st.get('stop', '—')} target {st.get('target', '—')}"
              f"{' [trail armed]' if st.get('trail_armed') else ''}")
    orphans = [s for s in state if s not in {p.symbol for p in positions}]
    if orphans:
        print(f"  Orphan state (no live position): {', '.join(orphans)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sovereign execution")
    parser.add_argument("command", choices=["execute", "manage", "status"])
    args = parser.parse_args()
    {"execute": execute, "manage": manage, "status": status}[args.command]()
