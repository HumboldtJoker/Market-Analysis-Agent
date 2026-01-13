#!/usr/bin/env python3
"""
Smart Market Monitor Launcher
Starts execution monitor only during market hours and handles restarts
"""

import os
import sys
import time
import subprocess
import signal
from datetime import datetime, time as dt_time
from pathlib import Path
import pytz
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Configuration
MONITOR_SCRIPT = "execution_monitor.py"
LOCAL_TIMEZONE = os.environ.get('LOCAL_TIMEZONE', 'US/Pacific')  # PST by default
MARKET_TIMEZONE = 'US/Eastern'  # NYSE/NASDAQ
MARKET_OPEN = dt_time(9, 30)   # 9:30 AM ET
MARKET_CLOSE = dt_time(16, 0)  # 4:00 PM ET
CHECK_INTERVAL = 60  # Check every minute

# PID file for process tracking
PID_FILE = Path('monitor.pid')

def is_market_open():
    """Check if market is currently open"""
    eastern = pytz.timezone(MARKET_TIMEZONE)
    now_et = datetime.now(eastern)
    current_time = now_et.time()

    # Check if weekend
    if now_et.weekday() >= 5:  # Saturday=5, Sunday=6
        return False

    # Check if within market hours
    return MARKET_OPEN <= current_time <= MARKET_CLOSE

def get_time_until_market_open():
    """Get seconds until next market open"""
    eastern = pytz.timezone(MARKET_TIMEZONE)
    local_tz = pytz.timezone(LOCAL_TIMEZONE)

    now_et = datetime.now(eastern)
    now_local = datetime.now(local_tz)

    # If weekend, wait until Monday
    if now_et.weekday() == 5:  # Saturday
        days_until_monday = 2
    elif now_et.weekday() == 6:  # Sunday
        days_until_monday = 1
    else:
        days_until_monday = 0

    # Calculate next market open
    next_open = now_et.replace(hour=9, minute=30, second=0, microsecond=0)

    if days_until_monday > 0:
        next_open = next_open.replace(day=now_et.day + days_until_monday)
    elif now_et.time() >= MARKET_CLOSE:
        # After market close, next open is tomorrow
        next_open = next_open.replace(day=now_et.day + 1)

    time_until = (next_open - now_et).total_seconds()

    # Convert to local time for display
    next_open_local = next_open.astimezone(local_tz)

    return time_until, next_open_local

def is_monitor_running():
    """Check if monitor is already running"""
    if not PID_FILE.exists():
        return False

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        # Check if process exists (Windows-compatible)
        try:
            subprocess.run(['tasklist', '/FI', f'PID eq {pid}'],
                         capture_output=True, check=True, text=True)
            return True
        except:
            return False
    except:
        return False

def start_monitor():
    """Start the execution monitor"""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting execution monitor...")

    # Start monitor as subprocess
    process = subprocess.Popen(
        [sys.executable, MONITOR_SCRIPT],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )

    # Save PID
    with open(PID_FILE, 'w') as f:
        f.write(str(process.pid))

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitor started (PID: {process.pid})")
    return process

def stop_monitor():
    """Stop the execution monitor"""
    if not PID_FILE.exists():
        return

    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Stopping monitor (PID: {pid})...")

        if sys.platform == 'win32':
            subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                         capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)

        PID_FILE.unlink()
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Monitor stopped")
    except Exception as e:
        print(f"Error stopping monitor: {e}")
        if PID_FILE.exists():
            PID_FILE.unlink()

def main():
    """Main loop - keeps monitor running during market hours"""
    print("=" * 70)
    print("  AutoInvestor Smart Monitor Launcher")
    print("=" * 70)
    print(f"Local Timezone: {LOCAL_TIMEZONE}")
    print(f"Market Timezone: {MARKET_TIMEZONE}")
    print(f"Market Hours: {MARKET_OPEN.strftime('%H:%M')} - {MARKET_CLOSE.strftime('%H:%M')} ET")
    print("=" * 70)
    print()

    monitor_process = None

    try:
        while True:
            market_open = is_market_open()
            monitor_running = is_monitor_running()

            eastern = pytz.timezone(MARKET_TIMEZONE)
            local_tz = pytz.timezone(LOCAL_TIMEZONE)
            now_et = datetime.now(eastern)
            now_local = datetime.now(local_tz)

            if market_open:
                # Market is open
                if not monitor_running:
                    print(f"\n[{now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}]")
                    print(f"Market OPEN ({now_et.strftime('%H:%M %Z')}) - Starting monitor...")
                    monitor_process = start_monitor()
                else:
                    # Monitor already running, just check occasionally
                    pass
            else:
                # Market is closed
                if monitor_running:
                    print(f"\n[{now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}]")
                    print(f"Market CLOSED ({now_et.strftime('%H:%M %Z')}) - Stopping monitor...")
                    stop_monitor()
                    monitor_process = None

                # Calculate time until next open
                seconds_until_open, next_open_local = get_time_until_market_open()
                hours_until = seconds_until_open / 3600

                print(f"\n[{now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}]")
                print(f"Market closed. Next open: {next_open_local.strftime('%A %Y-%m-%d %H:%M %Z')}")
                print(f"Time until open: {hours_until:.1f} hours")
                print(f"Checking again in {CHECK_INTERVAL} seconds...")

            # Sleep and check again
            time.sleep(CHECK_INTERVAL)

    except KeyboardInterrupt:
        print("\n\nShutdown requested...")
        if monitor_running:
            stop_monitor()
        print("Goodbye!")
    except Exception as e:
        print(f"\nError in main loop: {e}")
        if monitor_running:
            stop_monitor()
        raise

if __name__ == "__main__":
    main()
