"""
Technical Indicators Module for AutoInvestor

Provides technical analysis tools using historical price data:
- Simple Moving Averages (SMA)
- Relative Strength Index (RSI)
- Moving Average Convergence Divergence (MACD)
- Bollinger Bands

All indicators use yfinance for historical data retrieval.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, Optional
from datetime import datetime, timedelta

# Bollinger Bands volatility thresholds
BOLLINGER_NARROW_BANDWIDTH = 10  # Below this = low volatility, potential breakout
BOLLINGER_WIDE_BANDWIDTH = 20    # Above this = high volatility


def get_technical_indicators(ticker: str, period: str = "6mo") -> Dict:
    """
    Calculate comprehensive technical indicators for a stock

    Args:
        ticker: Stock symbol (e.g., 'AAPL')
        period: Historical period ('1mo', '3mo', '6mo', '1y', '2y', '5y')

    Returns:
        Dict containing all technical indicators with interpretation
    """
    try:
        # Fetch historical data
        stock = yf.Ticker(ticker)
        hist = stock.history(period=period)

        if hist.empty:
            return {"error": f"No historical data available for {ticker}"}

        # Calculate all indicators
        sma_data = calculate_sma(hist)
        rsi_data = calculate_rsi(hist)
        macd_data = calculate_macd(hist)
        bb_data = calculate_bollinger_bands(hist)

        # Get current price
        current_price = hist['Close'].iloc[-1]

        # Combine all indicators
        result = {
            "ticker": ticker,
            "current_price": round(current_price, 2),
            "period": period,
            "data_points": len(hist),
            "latest_date": hist.index[-1].strftime('%Y-%m-%d'),
            "sma": sma_data,
            "rsi": rsi_data,
            "macd": macd_data,
            "bollinger_bands": bb_data,
            "overall_signal": _generate_overall_signal(sma_data, rsi_data, macd_data, bb_data)
        }

        return result

    except Exception as e:
        return {"error": f"Failed to calculate technical indicators: {str(e)}"}


def calculate_sma(hist: pd.DataFrame, periods: list = [20, 50, 200]) -> Dict:
    """
    Calculate Simple Moving Averages

    Args:
        hist: Historical price dataframe from yfinance
        periods: List of periods to calculate (default: 20, 50, 200 days)

    Returns:
        Dict with SMA values and signals
    """
    close = hist['Close']
    current_price = close.iloc[-1]

    smas = {}
    for period in periods:
        if len(close) >= period:
            sma_value = close.rolling(window=period).mean().iloc[-1]
            smas[f'sma_{period}'] = round(sma_value, 2)

            # Calculate distance from current price
            distance = ((current_price - sma_value) / sma_value) * 100
            smas[f'sma_{period}_distance'] = round(distance, 2)

    # Generate signals
    signals = []

    # Golden Cross / Death Cross (50-day vs 200-day)
    if 'sma_50' in smas and 'sma_200' in smas:
        if smas['sma_50'] > smas['sma_200']:
            signals.append("Golden Cross: 50-day SMA above 200-day SMA (bullish)")
        else:
            signals.append("Death Cross: 50-day SMA below 200-day SMA (bearish)")

    # Price vs SMA signals
    if 'sma_50' in smas:
        if current_price > smas['sma_50']:
            signals.append("Price above 50-day SMA (bullish)")
        else:
            signals.append("Price below 50-day SMA (bearish)")

    if 'sma_200' in smas:
        if current_price > smas['sma_200']:
            signals.append("Price above 200-day SMA (long-term bullish)")
        else:
            signals.append("Price below 200-day SMA (long-term bearish)")

    smas['signals'] = signals
    return smas


def calculate_rsi(hist: pd.DataFrame, period: int = 14) -> Dict:
    """
    Calculate Relative Strength Index

    Args:
        hist: Historical price dataframe from yfinance
        period: RSI period (default: 14 days)

    Returns:
        Dict with RSI value and interpretation
    """
    close = hist['Close']

    # Calculate price changes
    delta = close.diff()

    # Separate gains and losses
    gains = delta.where(delta > 0, 0)
    losses = -delta.where(delta < 0, 0)

    # Calculate average gains and losses
    avg_gains = gains.rolling(window=period).mean()
    avg_losses = losses.rolling(window=period).mean()

    # Calculate RS and RSI
    # Prevent division by zero if stock only has gains (no losses)
    avg_losses_safe = avg_losses.replace(0, 1e-10)
    rs = avg_gains / avg_losses_safe
    rsi = 100 - (100 / (1 + rs))

    current_rsi = rsi.iloc[-1]

    # Handle NaN case (insufficient data for RSI calculation)
    if pd.isna(current_rsi):
        return {
            "error": f"Insufficient data to calculate RSI for {ticker}. Need at least {period} days of price history."
        }

    # Interpret RSI
    if current_rsi >= 70:
        signal = "Overbought (RSI >= 70) - potential sell signal"
        sentiment = "bearish"
    elif current_rsi <= 30:
        signal = "Oversold (RSI <= 30) - potential buy signal"
        sentiment = "bullish"
    elif current_rsi > 50:
        signal = "Bullish momentum (RSI > 50)"
        sentiment = "bullish"
    else:
        signal = "Bearish momentum (RSI < 50)"
        sentiment = "bearish"

    return {
        "rsi_14": round(current_rsi, 2),
        "signal": signal,
        "sentiment": sentiment
    }


def calculate_macd(hist: pd.DataFrame,
                   fast: int = 12,
                   slow: int = 26,
                   signal: int = 9) -> Dict:
    """
    Calculate MACD (Moving Average Convergence Divergence)

    Args:
        hist: Historical price dataframe from yfinance
        fast: Fast EMA period (default: 12)
        slow: Slow EMA period (default: 26)
        signal: Signal line period (default: 9)

    Returns:
        Dict with MACD values and signals
    """
    close = hist['Close']

    # Calculate EMAs
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()

    # Calculate MACD line
    macd_line = ema_fast - ema_slow

    # Calculate signal line
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()

    # Calculate histogram
    histogram = macd_line - signal_line

    # Get current values
    current_macd = macd_line.iloc[-1]
    current_signal = signal_line.iloc[-1]
    current_histogram = histogram.iloc[-1]

    # Detect crossovers (check last 5 periods for recent crossover)
    recent_periods = 5
    macd_recent = macd_line.iloc[-recent_periods:]
    signal_recent = signal_line.iloc[-recent_periods:]

    signals = []

    # Current position
    if current_macd > current_signal:
        signals.append("MACD above signal line (bullish)")
        sentiment = "bullish"
    else:
        signals.append("MACD below signal line (bearish)")
        sentiment = "bearish"

    # Histogram interpretation
    if current_histogram > 0:
        signals.append(f"Positive histogram ({round(current_histogram, 2)}) - upward momentum")
    else:
        signals.append(f"Negative histogram ({round(current_histogram, 2)}) - downward momentum")

    # Check for recent crossover
    for i in range(1, len(macd_recent)):
        if macd_recent.iloc[i] > signal_recent.iloc[i] and macd_recent.iloc[i-1] <= signal_recent.iloc[i-1]:
            signals.append("RECENT: Bullish crossover detected")
            break
        elif macd_recent.iloc[i] < signal_recent.iloc[i] and macd_recent.iloc[i-1] >= signal_recent.iloc[i-1]:
            signals.append("RECENT: Bearish crossover detected")
            break

    return {
        "macd": round(current_macd, 4),
        "signal_line": round(current_signal, 4),
        "histogram": round(current_histogram, 4),
        "signals": signals,
        "sentiment": sentiment
    }


def calculate_bollinger_bands(hist: pd.DataFrame,
                               period: int = 20,
                               std_dev: int = 2) -> Dict:
    """
    Calculate Bollinger Bands

    Args:
        hist: Historical price dataframe from yfinance
        period: Moving average period (default: 20)
        std_dev: Number of standard deviations (default: 2)

    Returns:
        Dict with Bollinger Bands values and signals
    """
    close = hist['Close']

    # Calculate middle band (SMA)
    middle_band = close.rolling(window=period).mean()

    # Calculate standard deviation
    std = close.rolling(window=period).std()

    # Calculate upper and lower bands
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)

    # Get current values
    current_price = close.iloc[-1]
    current_upper = upper_band.iloc[-1]
    current_middle = middle_band.iloc[-1]
    current_lower = lower_band.iloc[-1]

    # Calculate bandwidth and %B
    bandwidth = ((current_upper - current_lower) / current_middle) * 100
    percent_b = (current_price - current_lower) / (current_upper - current_lower)

    # Generate signals
    signals = []

    if current_price >= current_upper:
        signals.append("Price at or above upper band - overbought, possible reversal")
        sentiment = "bearish"
    elif current_price <= current_lower:
        signals.append("Price at or below lower band - oversold, possible reversal")
        sentiment = "bullish"
    elif current_price > current_middle:
        signals.append("Price above middle band - bullish trend")
        sentiment = "bullish"
    else:
        signals.append("Price below middle band - bearish trend")
        sentiment = "bearish"

    # Bandwidth interpretation
    if bandwidth < BOLLINGER_NARROW_BANDWIDTH:
        signals.append(f"Narrow bandwidth ({round(bandwidth, 2)}%) - low volatility, potential breakout")
    elif bandwidth > BOLLINGER_WIDE_BANDWIDTH:
        signals.append(f"Wide bandwidth ({round(bandwidth, 2)}%) - high volatility")

    return {
        "upper_band": round(current_upper, 2),
        "middle_band": round(current_middle, 2),
        "lower_band": round(current_lower, 2),
        "current_price": round(current_price, 2),
        "bandwidth_pct": round(bandwidth, 2),
        "percent_b": round(percent_b, 2),
        "signals": signals,
        "sentiment": sentiment
    }


def _generate_overall_signal(sma_data: Dict, rsi_data: Dict,
                             macd_data: Dict, bb_data: Dict) -> Dict:
    """
    Generate overall signal by combining all indicators

    Returns:
        Dict with overall recommendation and confidence
    """
    bullish_count = 0
    bearish_count = 0
    total_signals = 0

    # SMA signals
    for signal in sma_data.get('signals', []):
        total_signals += 1
        if 'bullish' in signal.lower():
            bullish_count += 1
        elif 'bearish' in signal.lower():
            bearish_count += 1

    # RSI signal
    total_signals += 1
    if rsi_data.get('sentiment') == 'bullish':
        bullish_count += 1
    else:
        bearish_count += 1

    # MACD signal
    total_signals += 1
    if macd_data.get('sentiment') == 'bullish':
        bullish_count += 1
    else:
        bearish_count += 1

    # Bollinger Bands signal
    total_signals += 1
    if bb_data.get('sentiment') == 'bullish':
        bullish_count += 1
    else:
        bearish_count += 1

    # Calculate percentages
    bullish_pct = (bullish_count / total_signals) * 100
    bearish_pct = (bearish_count / total_signals) * 100

    # Generate recommendation
    if bullish_pct >= 70:
        recommendation = "STRONG BUY"
        confidence = "high"
    elif bullish_pct >= 55:
        recommendation = "BUY"
        confidence = "moderate"
    elif bearish_pct >= 70:
        recommendation = "STRONG SELL"
        confidence = "high"
    elif bearish_pct >= 55:
        recommendation = "SELL"
        confidence = "moderate"
    else:
        recommendation = "HOLD"
        confidence = "low"

    return {
        "recommendation": recommendation,
        "confidence": confidence,
        "bullish_signals": bullish_count,
        "bearish_signals": bearish_count,
        "total_signals": total_signals,
        "bullish_pct": round(bullish_pct, 1),
        "bearish_pct": round(bearish_pct, 1)
    }


# Convenience function for easy tool integration
def analyze_technicals(ticker: str) -> Dict:
    """
    Simplified interface for technical analysis
    Returns formatted analysis suitable for AI agent interpretation
    """
    result = get_technical_indicators(ticker, period="6mo")

    if "error" in result:
        return result

    # Generate timestamp
    analysis_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')

    # Format for agent readability
    summary = f"""
Technical Analysis for {result['ticker']} (${result['current_price']})
Analysis Timestamp: {analysis_time}
Data Period: {result['period']} ({result['data_points']} trading days)
Latest Data: {result['latest_date']}

DATA SOURCES & VERIFICATION:
- Price Data: Yahoo Finance (via yfinance Python library)
- Verify at: https://finance.yahoo.com/quote/{result['ticker']}/history
- Chart verification: https://finance.yahoo.com/quote/{result['ticker']}/chart

CALCULATION METHODOLOGY:
- SMA: Simple Moving Average over specified periods (20/50/200 days)
- RSI: Relative Strength Index (14-period) - measures momentum
- MACD: Moving Average Convergence Divergence (12/26/9) - trend following
- Bollinger Bands: 20-day SMA ± 2 standard deviations - volatility measure

MOVING AVERAGES (SMA):
{_format_sma_summary(result['sma'])}

RELATIVE STRENGTH INDEX (RSI):
- RSI(14): {result['rsi']['rsi_14']}
- Signal: {result['rsi']['signal']}

MACD (12/26/9):
- MACD: {result['macd']['macd']}
- Signal Line: {result['macd']['signal_line']}
- Histogram: {result['macd']['histogram']}
- Signals: {', '.join(result['macd']['signals'])}

BOLLINGER BANDS (20-day, 2 std dev):
- Upper: ${result['bollinger_bands']['upper_band']}
- Middle: ${result['bollinger_bands']['middle_band']}
- Lower: ${result['bollinger_bands']['lower_band']}
- Current: ${result['bollinger_bands']['current_price']}
- Bandwidth: {result['bollinger_bands']['bandwidth_pct']}%
- Signals: {', '.join(result['bollinger_bands']['signals'])}

OVERALL SIGNAL:
- Recommendation: {result['overall_signal']['recommendation']}
- Confidence: {result['overall_signal']['confidence']}
- Bullish Signals: {result['overall_signal']['bullish_signals']}/{result['overall_signal']['total_signals']} ({result['overall_signal']['bullish_pct']}%)
- Bearish Signals: {result['overall_signal']['bearish_signals']}/{result['overall_signal']['total_signals']} ({result['overall_signal']['bearish_pct']}%)

IMPORTANT DISCLAIMER:
This technical analysis is for informational purposes only and should NOT be considered
financial advice. Always verify the source data independently using the links provided above.
Past performance does not guarantee future results. Consult a licensed financial advisor
before making investment decisions.

Data calculated using standard industry formulas. All indicators are lagging (based on
historical data) and may not predict future price movements. Use as one of multiple factors
in your investment research.
"""

    return {
        "summary": summary.strip(),
        "raw_data": result,
        "verification_links": {
            "price_history": f"https://finance.yahoo.com/quote/{result['ticker']}/history",
            "chart": f"https://finance.yahoo.com/quote/{result['ticker']}/chart",
            "quote": f"https://finance.yahoo.com/quote/{result['ticker']}"
        },
        "data_source": "Yahoo Finance",
        "analysis_timestamp": analysis_time
    }


def _format_sma_summary(sma_data: Dict) -> str:
    """Format SMA data for readable output"""
    lines = []

    for key, value in sma_data.items():
        if key.startswith('sma_') and not key.endswith('_distance'):
            period = key.split('_')[1]
            distance_key = f'sma_{period}_distance'
            distance = sma_data.get(distance_key, 0)
            lines.append(f"- SMA({period}): ${value} (Price {'+' if distance >= 0 else ''}{distance}% from SMA)")

    if 'signals' in sma_data:
        lines.append(f"- Signals: {', '.join(sma_data['signals'])}")

    return '\n'.join(lines)


if __name__ == "__main__":
    # Test the technical indicators
    print("Testing Technical Indicators Module\n")

    test_ticker = "AAPL"
    print(f"Analyzing {test_ticker}...\n")

    result = analyze_technicals(test_ticker)

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(result['summary'])
