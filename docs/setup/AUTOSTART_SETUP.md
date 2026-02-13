# AutoInvestor Auto-Start Setup Guide

The smart launcher (`start_monitor_smart.py`) will automatically:
- Start the execution monitor when markets open (9:30 AM ET)
- Stop the monitor when markets close (4:00 PM ET)
- Handle weekends and holidays
- Work even when you hit Claude account token limits

## Option 1: Manual Start (Simplest)

Just run this whenever you want monitoring active:
```bash
START_AUTOINVESTOR_SMART.bat
```

Leave it running in a terminal window. It will manage market hours automatically.

---

## Option 2: Windows Startup (Runs on boot)

### Method A: Startup Folder (Easiest)

1. Press `Win + R`
2. Type: `shell:startup` and press Enter
3. Copy `START_AUTOINVESTOR_SMART.bat` into that folder
4. Reboot - it will start automatically

**Pros:** Simple, visual confirmation in terminal
**Cons:** Terminal window stays open

### Method B: Task Scheduler (Silent background)

1. Open **Task Scheduler** (`Win + R`, type `taskschd.msc`)

2. Click **"Create Basic Task"**
   - Name: `AutoInvestor Monitor`
   - Description: `Starts trading monitor during market hours`
   - Click **Next**

3. **Trigger:** Select "When I log on"
   - Click **Next**

4. **Action:** Select "Start a program"
   - Click **Next**

5. **Program/script:** Browse to:
   ```
   <PATH_TO_PROJECT>\START_AUTOINVESTOR_SMART.bat
   ```

6. **Finish** - Check "Open Properties dialog"

7. In Properties:
   - **General tab:**
     - ☑ Run whether user is logged on or not
     - ☑ Run with highest privileges

   - **Conditions tab:**
     - ☐ Start the task only if the computer is on AC power (uncheck)

   - **Settings tab:**
     - ☑ Allow task to be run on demand
     - ☑ If the task fails, restart every: 1 minute
     - ☐ Stop the task if it runs longer than: (uncheck)

8. Click **OK** and enter your Windows password

**Pros:** Runs silently in background, survives reboots
**Cons:** Slightly more complex setup

---

## How It Works

### Market Hours Handling

The smart launcher checks:
- **Your local time:** US/Pacific (configurable in `.env`)
- **Market time:** US/Eastern (NYSE/NASDAQ)
- **Market hours:** 9:30 AM - 4:00 PM ET, Mon-Fri

**Example (you're in PST):**
```
6:30 AM PST = 9:30 AM ET → Monitor STARTS
1:00 PM PST = 4:00 PM ET → Monitor STOPS
```

### During Off-Hours

When markets are closed, the launcher:
- Checks every 60 seconds
- Displays time until next market open
- Sleeps to conserve resources
- Automatically starts monitor when market opens

### Token Limit Handling

**The key insight:** The Python monitor doesn't use Claude tokens!

- **Monitor:** Pure Python, $0 tokens
- **VIX alerts:** Written to file when regime changes
- **Strategic reviews:** Only when YOU check in (using your session)

**If you hit token limits:**
- Monitor keeps running
- VIX alerts keep triggering
- Reviews wait until your tokens reset
- You can manually check `strategy_review_needed.json`

---

## Monitoring the System

### Check if running:

**Windows:**
```bash
tasklist | findstr python
```

### Check monitor logs:
```bash
tail -f execution_log.md
```

### Check VIX alerts:
```bash
cat strategy_review_needed.json
```

### Force stop:
```bash
Ctrl+C in the terminal
# Or
taskkill /F /IM python.exe
```

---

## Testing

### Test the smart launcher:
```bash
py start_monitor_smart.py
```

You should see:
```
======================================================================
  AutoInvestor Smart Monitor Launcher
======================================================================
Local Timezone: US/Pacific
Market Timezone: US/Eastern
Market Hours: 09:30 - 16:00 ET
======================================================================

[2026-01-12 15:45:00 PST]
Market closed. Next open: Monday 2026-01-13 06:30 PST
Time until open: 14.8 hours
Checking again in 60 seconds...
```

---

## Troubleshooting

### "Python not found"
- Make sure Python is installed
- Try `python` instead of `py` in the batch file

### Monitor won't start
- Check `monitor.pid` file exists
- Delete it and restart: `del monitor.pid`
- Check execution_log.md for errors

### Wrong timezone
- Edit `.env` and set `LOCAL_TIMEZONE=US/Pacific` (or your timezone)
- See: https://en.wikipedia.org/wiki/List_of_tz_database_time_zones

### Task Scheduler not working
- Check Task History in Task Scheduler
- Make sure paths are absolute (not relative)
- Run as Administrator

---

## What Gets Logged

All activity goes to `execution_log.md`:
- Market open/close events
- Monitor start/stop
- Portfolio checks (every 5 minutes during market hours)
- VIX regime changes
- Trade executions
- Stop-loss triggers

---

## Summary

**During your session:**
- Smart launcher runs in background
- Monitor starts/stops automatically with market hours
- VIX alerts written to file
- You review alerts when you check in

**When you hit token limits:**
- Monitor keeps running (no tokens needed)
- Alerts keep triggering
- Reviews wait for your next session
- Nothing breaks!

**The system is now fully autonomous and token-limit resilient.**
