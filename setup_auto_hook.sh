#!/bin/bash
# Setup script to enable automatic AutoInvestor detection

echo "Setting up AutoInvestor automatic directory detection..."
echo ""

# Detect shell configuration file
if [ -f ~/.bashrc ]; then
    SHELL_CONFIG=~/.bashrc
elif [ -f ~/.bash_profile ]; then
    SHELL_CONFIG=~/.bash_profile
elif [ -f ~/.zshrc ]; then
    SHELL_CONFIG=~/.zshrc
else
    echo "❌ Could not find shell configuration file (.bashrc, .bash_profile, or .zshrc)"
    exit 1
fi

echo "Found shell config: $SHELL_CONFIG"
echo ""

# Check if hook is already installed
if grep -q "check_autoinvestor_dir" "$SHELL_CONFIG"; then
    echo "✓ AutoInvestor hook already installed in $SHELL_CONFIG"
    exit 0
fi

# Add hook to shell configuration
cat << 'EOF' >> "$SHELL_CONFIG"

# ──────────────────────────────────────────────────────────
# AutoInvestor Auto-Detection Hook
# Automatically detects when you cd into Market-Analysis-Agent
# ──────────────────────────────────────────────────────────

function check_autoinvestor_dir() {
  if [[ -f ".claude_hook" && "$AUTOINVESTOR_LOADED" != "1" ]]; then
    source .claude_hook
  fi

  # Clear the loaded flag when leaving the directory
  if [[ "$AUTOINVESTOR_LOADED" == "1" && ! -f ".claude_hook" ]]; then
    unset AUTOINVESTOR_LOADED
    unset CLAUDE_AGENT
    unset CLAUDE_SETTINGS_SOURCES
  fi
}

# Run check after every command (directory change)
PROMPT_COMMAND="${PROMPT_COMMAND:+$PROMPT_COMMAND; }check_autoinvestor_dir"

EOF

echo "✅ AutoInvestor hook installed successfully!"
echo ""
echo "To activate the hook:"
echo "  source $SHELL_CONFIG"
echo ""
echo "Or restart your terminal."
echo ""
echo "Then, whenever you cd into Market-Analysis-Agent, you'll see:"
echo "  🤖 AutoInvestor Environment Detected"
echo ""
echo "And starting Claude with 'claude' will automatically use project settings."
