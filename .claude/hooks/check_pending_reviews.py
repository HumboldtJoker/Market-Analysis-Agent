#!/usr/bin/env python3
"""
UserPromptSubmit hook: Check for pending strategy reviews
Injects context about pending alerts so Claude is aware on every interaction
"""
import json
import sys
import os
from pathlib import Path

def main():
    # Get project directory
    project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')
    if not project_dir:
        # Try to find it from the input
        try:
            input_data = json.load(sys.stdin)
            project_dir = input_data.get('cwd', '')
        except:
            sys.exit(0)

    project_path = Path(project_dir)

    # Files to check for pending reviews
    alert_files = [
        ('scheduled_review_needed.json', 'SCHEDULED_REVIEW'),
        ('strategy_review_needed.json', 'VIX_ALERT'),
    ]

    pending_alerts = []

    for filename, alert_type in alert_files:
        filepath = project_path / filename
        if filepath.exists():
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                if data.get('status') == 'pending':
                    alert_info = {
                        'type': data.get('alert_type', alert_type),
                        'timestamp': data.get('timestamp', 'unknown'),
                        'reason': data.get('reason', 'Review needed'),
                    }

                    # Add specific details based on alert type
                    if 'sold_position' in data:
                        alert_info['sold_position'] = data['sold_position']
                    if 'current_vix' in data:
                        alert_info['vix'] = data['current_vix']
                    if 'vix_regime' in data:
                        alert_info['regime'] = data['vix_regime']

                    pending_alerts.append(alert_info)
            except Exception as e:
                pass  # Silently ignore parse errors

    # If there are pending alerts, output context for Claude
    if pending_alerts:
        output = {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "pendingReviews": pending_alerts,
                "message": f"ATTENTION: {len(pending_alerts)} pending strategy review(s) require processing."
            }
        }
        print(json.dumps(output))

    sys.exit(0)

if __name__ == '__main__':
    main()
