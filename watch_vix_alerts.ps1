# VIX Alert File Watcher - Triggers Claude Code when alert fires
# Run this in background to get instant notifications when VIX regime changes

$watchPath = "C:\Users\allis\desktop\get rich quick scheme\market-analysis-agent"
$alertFile = "strategy_review_needed.json"
$claudeCodePath = "claude"  # Will use PATH, or specify full path

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  AutoInvestor VIX Alert Watcher" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "Monitoring: $watchPath\$alertFile" -ForegroundColor Yellow
Write-Host "Action: Launch Claude Code for immediate analysis" -ForegroundColor Yellow
Write-Host "Press Ctrl+C to stop..." -ForegroundColor Gray
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# Create file watcher
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path = $watchPath
$watcher.Filter = $alertFile
$watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName,LastWrite'
$watcher.EnableRaisingEvents = $true

$action = {
    $timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Write-Host "[$timestamp] " -NoNewline -ForegroundColor Gray
    Write-Host "VIX ALERT DETECTED!" -ForegroundColor Red -BackgroundColor Yellow

    # Read alert details
    try {
        $alertContent = Get-Content "$using:watchPath\$using:alertFile" | ConvertFrom-Json
        Write-Host "  VIX Change: $($alertContent.vix_previous) -> $($alertContent.vix_current)" -ForegroundColor Yellow
        Write-Host "  Regime: $($alertContent.regime_previous) -> $($alertContent.regime_current)" -ForegroundColor Yellow
    } catch {
        Write-Host "  Alert file detected but couldn't read details" -ForegroundColor Gray
    }

    Write-Host "  Launching Claude Code for strategic review..." -ForegroundColor Green

    # Launch Claude Code in the project directory
    Set-Location $using:watchPath
    Start-Process $using:claudeCodePath -ArgumentList "." -WorkingDirectory $using:watchPath

    Write-Host "  Claude Code launched. Waiting for next alert..." -ForegroundColor Gray
    Write-Host ""
}

# Register event handlers
$onCreate = Register-ObjectEvent -InputObject $watcher -EventName 'Created' -Action $action
$onChange = Register-ObjectEvent -InputObject $watcher -EventName 'Changed' -Action $action

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Watcher started. Monitoring for VIX alerts..." -ForegroundColor Green
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
