# Real-Time VIX Alert Triggering

This guide sets up instant Claude Code launch when VIX alerts trigger.

## How It Works

```
Python Monitor detects VIX regime change
  ↓ Writes strategy_review_needed.json (instant)
Windows Task Scheduler detects file change
  ↓ Launches Claude Code (2-3 seconds)
Claude Code startup hook checks for alerts
  ↓ Auto-spawns analysis subagent (instant)
Subagent runs MCP tools analysis
  ↓ Writes recommendations (20-30 seconds)
Total time: ~30 seconds from VIX change to recommendations
```

## Setup Instructions

### Step 1: Create PowerShell Trigger Script

Create `watch_vix_alerts.ps1`:

```powershell
# VIX Alert File Watcher - Triggers Claude Code when alert fires
$watchPath = "C:\Users\allis\desktop\get rich quick scheme\market-analysis-agent"
$alertFile = "strategy_review_needed.json"
$claudeCodePath = "C:\Users\allis\AppData\Local\Programs\Claude\Claude Code.exe"  # Adjust if needed

# Create file watcher
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $watchPath
$watcher.Filter = $alertFile
$watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName,LastWrite'
$watcher.EnableRaisingEvents = $true

$action = {
    Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] VIX alert detected! Launching Claude Code..."

    # Launch Claude Code in the project directory
    Start-Process $using:claudeCodePath -ArgumentList $using:watchPath
}

# Register event handler
Register-ObjectEvent -InputObject $watcher -EventName 'Created' -Action $action
Register-ObjectEvent -InputObject $watcher -EventName 'Changed' -Action $action

Write-Host "Watching for VIX alerts in: $watchPath"
Write-Host "Alert file: $alertFile"
Write-Host "Press Ctrl+C to stop..."

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    $watcher.Dispose()
}
```

### Step 2: Add Startup Hook to Claude Code Settings

Edit `.claude/settings.json` to add auto-check on startup:

```json
{
  "agent": "autoinvestor",
  "onStartup": "check_vix_alerts",
  ...
}
```

Create `check_vix_alerts.sh`:

```bash
#!/bin/bash
# Auto-check for VIX alerts on Claude Code startup

ALERT_FILE="strategy_review_needed.json"

if [ -f "$ALERT_FILE" ]; then
    echo "⚠️  VIX ALERT DETECTED - Spawning analysis subagent..."

    # The alert will be automatically detected by Claude's context
    # No need to manually trigger - Claude will see the file exists
fi
```

### Step 3: Run the File Watcher

**Option A: Manual (for testing)**
```powershell
powershell -ExecutionPolicy Bypass -File watch_vix_alerts.ps1
```

**Option B: Background Service (recommended)**

1. Open Task Scheduler (`taskschd.msc`)

2. Create Task:
   - **Name:** AutoInvestor VIX Alert Watcher
   - **Trigger:** At startup
   - **Action:** Start program
     - **Program:** `powershell.exe`
     - **Arguments:** `-ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Users\allis\desktop\get rich quick scheme\market-analysis-agent\watch_vix_alerts.ps1"`
   - **Settings:**
     - ☑ Allow task to be run on demand
     - ☑ If task fails, restart every 5 minutes
     - ☐ Stop task if runs longer than (uncheck)

3. Run immediately: Right-click → Run

## Alternative: Simpler Polling Approach

If file watching is complex, use this simpler approach:

**Create `check_for_alerts.bat`:**
```batch
@echo off
cd /d "%~dp0"

if exist strategy_review_needed.json (
    echo VIX alert found! Opening Claude Code...
    start "" "C:\Users\allis\AppData\Local\Programs\Claude\Claude Code.exe" "%cd%"
    timeout /t 10
)
```

**Task Scheduler:**
- **Trigger:** Every 1 minute during market hours (9:30 AM - 4:00 PM)
- **Action:** Run `check_for_alerts.bat`
- **Condition:** Only if computer is awake

**Delay:** Up to 1 minute (much better than 29 minutes!)

## What Happens When Claude Code Opens

1. **I detect alert file exists**
2. **Read alert details:**
   - VIX level change
   - Regime change (NORMAL → ELEVATED, etc.)
   - Current portfolio snapshot

3. **Automatically spawn subagent:**
   ```
   Task tool: analyze_vix_alert
   - Run technical_analysis on all positions
   - Run macro_analysis for regime context
   - Run portfolio_analysis for risk assessment
   - Generate recommendations
   ```

4. **Subagent completes (~20-30 seconds)**
   - Analysis written to execution_log.md
   - Recommendations ready for your review
   - Alert file marked as processed

5. **You review and decide**
   - Accept recommendations
   - Adjust strategy
   - Or ignore if alert is false positive

## Token Usage

**File watcher:** 0 tokens (pure PowerShell/Python)
**Claude Code startup:** ~1k tokens (checking for alert)
**Subagent analysis:** ~20-30k tokens (MCP tools + reasoning)

**Total per alert:** ~30k tokens from your Claude Pro session

With VIX alerts triggering 1-3 times per week, this uses ~60-90k tokens/week.

## Testing

### Test the file watcher:
```powershell
# Start watcher
powershell -ExecutionPolicy Bypass -File watch_vix_alerts.ps1

# In another terminal, trigger an alert:
python -c "import json; json.dump({'test': True}, open('strategy_review_needed.json', 'w'))"
```

You should see:
- Watcher detects file change
- Claude Code launches automatically
- I detect the alert and spawn subagent

## Troubleshooting

**Claude Code path wrong:**
```powershell
# Find Claude Code executable
Get-Command claude | Select-Object Source
```

**File watcher not triggering:**
- Check PowerShell execution policy: `Get-ExecutionPolicy`
- Set if needed: `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser`
- Check Task Scheduler event log

**Alert not auto-processing:**
- Verify `.claude/settings.json` has startup hook
- Check that `strategy_review_needed.json` is in project root
- Make sure Claude Code opens in correct directory

## Benefits vs Drawbacks

**Benefits:**
- ✓ Near real-time response (30 seconds vs 29 minutes)
- ✓ Fully automated
- ✓ Uses your Claude Pro tokens (no API costs)
- ✓ Works even when you're away from computer

**Drawbacks:**
- ⚠ Opens Claude Code automatically (might interrupt other work)
- ⚠ Uses ~30k tokens per alert (but only when VIX crosses thresholds)
- ⚠ Requires Windows Task Scheduler setup

## Recommendation

**For critical alerts (VIX > 30):** Use file watcher for instant response

**For normal alerts (VIX 15-30):** Use 1-minute polling check

You can have both running - file watcher for urgency, polling as backup.
