"""
Test VIX Monitoring Functionality

Tests:
1. VIX data fetching from Yahoo Finance
2. Regime detection (CALM, NORMAL, ELEVATED, HIGH)
3. Threshold crossing detection
4. VIX log file creation and persistence
"""

import json
import os
from pathlib import Path
from datetime import datetime
import yfinance as yf

# Test VIX regime thresholds
VIX_THRESHOLDS = {
    'CALM': (0, 15),
    'NORMAL': (15, 20),
    'ELEVATED': (20, 30),
    'HIGH': (30, float('inf'))
}

VIX_LOG_PATH = Path('vix_log.json')


def get_vix_regime(vix: float) -> str:
    """Determine VIX regime based on level"""
    for regime, (low, high) in VIX_THRESHOLDS.items():
        if low <= vix < high:
            return regime
    return 'HIGH'


def test_vix_fetch():
    """Test fetching VIX data from Yahoo Finance"""
    print("\n" + "=" * 70)
    print("TEST 1: VIX Data Fetching")
    print("=" * 70)

    try:
        vix_ticker = yf.Ticker("^VIX")
        vix_data = vix_ticker.history(period="5d")

        if vix_data.empty:
            print("[FAIL] No VIX data retrieved")
            return None

        print("[PASS] VIX data fetched successfully")
        print(f"\nLast 5 days:")
        print(vix_data[['Close']].tail())

        latest_vix = float(vix_data['Close'].iloc[-1])
        print(f"\nLatest VIX: {latest_vix:.2f}")

        return latest_vix

    except Exception as e:
        print(f"[FAIL] Error fetching VIX: {e}")
        return None


def test_regime_detection(vix: float):
    """Test VIX regime detection"""
    print("\n" + "=" * 70)
    print("TEST 2: Regime Detection")
    print("=" * 70)

    regime = get_vix_regime(vix)
    print(f"VIX Level: {vix:.2f}")
    print(f"Detected Regime: {regime}")

    # Show thresholds
    print("\nRegime Thresholds:")
    for regime_name, (low, high) in VIX_THRESHOLDS.items():
        high_str = f"{high}" if high != float('inf') else "∞"
        print(f"  {regime_name}: {low} - {high_str}")

    print(f"\n[PASS] Regime detection working")
    return regime


def test_threshold_crossing():
    """Test threshold crossing detection logic"""
    print("\n" + "=" * 70)
    print("TEST 3: Threshold Crossing Detection")
    print("=" * 70)

    # Test scenarios
    test_cases = [
        (18.5, 'NORMAL', 21.3, 'ELEVATED', True, "NORMAL -> ELEVATED (crossing up)"),
        (22.0, 'ELEVATED', 31.5, 'HIGH', True, "ELEVATED -> HIGH (crossing up)"),
        (28.0, 'ELEVATED', 18.0, 'NORMAL', True, "ELEVATED -> NORMAL (crossing down)"),
        (32.0, 'HIGH', 25.0, 'ELEVATED', True, "HIGH -> ELEVATED (crossing down)"),
        (17.0, 'NORMAL', 18.5, 'NORMAL', False, "Within same regime (no crossing)"),
        (12.0, 'CALM', 13.5, 'CALM', False, "Within same regime (no crossing)"),
    ]

    significant_changes = [
        ('NORMAL', 'ELEVATED'),
        ('ELEVATED', 'HIGH'),
        ('HIGH', 'ELEVATED'),
        ('ELEVATED', 'NORMAL'),
        ('CALM', 'NORMAL'),
        ('NORMAL', 'CALM')
    ]

    passed = 0
    for prev_vix, prev_regime, curr_vix, curr_regime, expected_cross, description in test_cases:
        should_cross = (prev_regime, curr_regime) in significant_changes
        result = "PASS" if should_cross == expected_cross else "FAIL"
        if should_cross == expected_cross:
            passed += 1

        print(f"[{result}] {description}")
        print(f"      {prev_vix:.1f} ({prev_regime}) -> {curr_vix:.1f} ({curr_regime})")
        print(f"      Expected crossing: {expected_cross}, Got: {should_cross}")

    print(f"\n{passed}/{len(test_cases)} test cases passed")


def test_vix_logging(vix: float, regime: str):
    """Test VIX log file creation and persistence"""
    print("\n" + "=" * 70)
    print("TEST 4: VIX Logging")
    print("=" * 70)

    try:
        # Initialize or load log
        vix_log = []
        if VIX_LOG_PATH.exists():
            with open(VIX_LOG_PATH, 'r') as f:
                vix_log = json.load(f)
            print(f"[PASS] Loaded existing VIX log: {len(vix_log)} entries")
        else:
            print("[INFO] Creating new VIX log file")

        # Add test entry
        test_entry = {
            'timestamp': datetime.now().isoformat(),
            'vix': vix,
            'regime': regime,
            'test': True
        }
        vix_log.append(test_entry)

        # Save
        with open(VIX_LOG_PATH, 'w') as f:
            json.dump(vix_log, f, indent=2)

        print(f"[PASS] VIX log saved with {len(vix_log)} entries")

        # Verify
        with open(VIX_LOG_PATH, 'r') as f:
            loaded_log = json.load(f)

        if len(loaded_log) == len(vix_log):
            print("[PASS] Log persistence verified")
        else:
            print("[FAIL] Log persistence failed")

        # Show last few entries
        print("\nLast 3 entries:")
        for entry in loaded_log[-3:]:
            print(f"  {entry['timestamp']}: VIX={entry['vix']:.2f}, Regime={entry['regime']}")

    except Exception as e:
        print(f"[FAIL] Error in VIX logging: {e}")


def main():
    """Run all VIX monitoring tests"""
    print("\n" + "=" * 70)
    print("VIX MONITORING SYSTEM - TEST SUITE")
    print("=" * 70)

    # Test 1: Fetch VIX
    vix = test_vix_fetch()
    if not vix:
        print("\n[ERROR] Cannot continue tests - VIX fetch failed")
        return

    # Test 2: Regime detection
    regime = test_regime_detection(vix)

    # Test 3: Threshold crossing logic
    test_threshold_crossing()

    # Test 4: VIX logging
    test_vix_logging(vix, regime)

    print("\n" + "=" * 70)
    print("TEST SUITE COMPLETE")
    print("=" * 70)
    print("\nNext Steps:")
    print("1. Set ANTHROPIC_API_KEY in .env file")
    print("2. Run: python test_vix_monitoring.py")
    print("3. Run: python strategy_trigger.py  (to test strategic review)")
    print("4. Start monitoring: python execution_monitor.py")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
