# Strategic Alert File Watcher - Triggers Claude Code for VIX + Scheduled Reviews
# Run this in background to get instant notifications for any strategic review needed

$watchPath = "C:\Users\allis\desktop\get rich quick scheme\market-analysis-agent"
$vixAlertFile = "strategy_review_needed.json"
$scheduledAlertFile = "scheduled_review_needed.json"
$claudeCodePath = "claude"  # Will use PATH, or specify full path

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  AutoInvestor Strategic Alert Watcher" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Monitoring: $watchPath" -ForegroundColor Yellow
Write-Host "  - VIX alerts: $vixAlertFile" -ForegroundColor Yellow
Write-Host "  - Scheduled reviews: $scheduledAlertFile" -ForegroundColor Yellow
Write-Host "Action: Launch Claude Code for immediate analysis" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop..." -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Create file watcher for directory (watches all .json files)
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $watchPath
$watcher.Filter = "*_needed.json"  # Watches both alert files
$watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName,LastWrite'
$watcher.EnableRaisingEvents = $true

$action = {
    param($source, $e)

    $filename = $e.Name
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

    # Check which alert type
    if ($filename -eq $using:vixAlertFile) {
        Write-Host "[$timestamp] " -NoNewline -ForegroundColor Gray
        Write-Host "VIX ALERT DETECTED!" -ForegroundColor Red -BackgroundColor Yellow

        # Read VIX alert details
        try {
            $alertContent = Get-Content "$using:watchPath\$filename" | ConvertFrom-Json
            Write-Host "  Type: VIX Regime Change" -ForegroundColor Yellow
            Write-Host "  VIX Change: $($alertContent.vix_previous) -> $($alertContent.vix_current)" -ForegroundColor Yellow
            Write-Host "  Regime: $($alertContent.regime_previous) -> $($alertContent.regime_current)" -ForegroundColor Yellow
        } catch {
            Write-Host "  Alert file detected but couldn't read details" -ForegroundColor Gray
        }
    }
    elseif ($filename -eq $using:scheduledAlertFile) {
        Write-Host "[$timestamp] " -NoNewline -ForegroundColor Gray
        Write-Host "SCHEDULED REVIEW ALERT!" -ForegroundColor Blue -BackgroundColor White

        # Read scheduled review details
        try {
            $alertContent = Get-Content "$using:watchPath\$filename" | ConvertFrom-Json
            Write-Host "  Type: Proactive Opportunity Scan" -ForegroundColor Cyan
            Write-Host "  Interval: Every $($alertContent.interval_hours) hours" -ForegroundColor Cyan
            Write-Host "  VIX: $($alertContent.current_vix) ($($alertContent.vix_regime))" -ForegroundColor Cyan
        } catch {
            Write-Host "  Alert file detected but couldn't read details" -ForegroundColor Gray
        }
    }
    else {
        return  # Not an alert file we care about
    }

    Write-Host "  Launching Claude Code for strategic analysis..." -ForegroundColor Green

    # Launch Claude Code in the project directory
    Set-Location $using:watchPath
    Start-Process $using:claudeCodePath -ArgumentList "." -WorkingDirectory $using:watchPath

    Write-Host "  Claude Code launched. Waiting for next alert..." -ForegroundColor Gray
    Write-Host ""
}

# Register event handlers
$onCreate = Register-ObjectEvent -InputObject $watcher -EventName 'Created' -Action $action
$onChange = Register-ObjectEvent -InputObject $watcher -EventName 'Changed' -Action $action

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Watcher started. Monitoring for all strategic alerts..." -ForegroundColor Green
Write-Host ""

# Keep script running
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "Shutting down watcher..." -ForegroundColor Yellow
    Unregister-Event -SourceIdentifier $onCreate.Name
    Unregister-Event -SourceIdentifier $onChange.Name
    $watcher.Dispose()
    Write-Host "Watcher stopped." -ForegroundColor Gray
}
