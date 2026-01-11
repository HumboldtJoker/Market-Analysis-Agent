#!/bin/bash
# AutoInvestor Startup Script
# Launches Claude Code with the AutoInvestor agent configuration

# Check for required environment variables
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "WARNING: ANTHROPIC_API_KEY not set. Set with: export ANTHROPIC_API_KEY=your_key"
fi

if [ -z "$RAPIDAPI_KEY" ]; then
    echo "NOTE: RAPIDAPI_KEY not set. Congressional trades features will be unavailable."
fi

if [ -z "$ALPACA_API_KEY" ]; then
    echo "NOTE: ALPACA_API_KEY not set. Trade execution features will be unavailable."
fi

# Navigate to project directory
cd "$(dirname "$0")"

echo "🤖 Starting AutoInvestor Agent..."
echo "📊 Mode: Collaborative (AI + Human Insights)"
echo "📂 Project: Market-Analysis-Agent"
echo ""

# Launch Claude Code with project settings
# The .claude/settings.json will automatically load the autoinvestor agent
claude --setting-sources project,user --verbose

# Alternative: Explicitly specify the agent
# claude --agent autoinvestor --settings .claude/settings.json
