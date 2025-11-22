# Contributing to AutoInvestor

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help make this tool better for everyone

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your environment (Python version, OS, etc.)

### Suggesting Features

Feature requests are welcome! Please open an issue describing:
- The problem you're trying to solve
- Your proposed solution
- Why this would be valuable to other users

### Pull Requests

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Test thoroughly**: Ensure existing tests pass and add new ones if needed
5. **Commit with clear messages**: `git commit -m "Add feature: brief description"`
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Open a pull request**

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/autoinvestor.git
cd autoinvestor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up API key
export ANTHROPIC_API_KEY="your-key-here"
```

## Code Style

- Follow PEP 8 Python style guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and modular

## Testing

Before submitting a PR:
1. Test with multiple stock tickers
2. Verify all tools return correct data
3. Check for API errors and edge cases
4. Test with different investor profiles

## Areas for Contribution

We especially welcome contributions in:

### High Priority
- **Additional data sources**: Integrate Alpha Vantage, IEX Cloud, or other APIs
- **Technical indicators**: SMA, RSI, MACD, Bollinger Bands
- **Sentiment analysis**: News sentiment, social media analysis
- **Performance tracking**: Portfolio tracking and backtesting

### Medium Priority
- **Paper trading**: Simulated trading with performance tracking
- **Multi-stock analysis**: Compare multiple stocks simultaneously
- **Visualization**: Charts and graphs for analysis results
- **Export functionality**: Save reports as PDF or HTML

### Documentation
- **Tutorials**: Step-by-step guides for specific use cases
- **Videos**: Screencasts demonstrating features
- **Translations**: Documentation in other languages

## Financial Advice Disclaimer

**Important**: This tool provides data analysis, NOT financial advice.

When contributing:
- Never present analysis as investment advice
- Always include appropriate disclaimers
- Emphasize the importance of due diligence
- Remind users to consult licensed professionals

## Questions?

Open an issue or reach out to the maintainers.

Thank you for contributing! 🎉
