"""
AI Ecosystem Opportunity Discovery Scanner
Scans for STRONG BUY signals across AI infrastructure and software stocks
"""

from autoinvestor_api import get_technicals, get_stock_price
import json

# Define scan universe
SCAN_UNIVERSE = {
    'semiconductor': ['AVGO', 'MRVL', 'QCOM', 'INTC', 'SMCI', 'ARM', 'SNPS', 'CDNS', 'ASML', 'LRCX', 'AMAT', 'KLAC'],
    'hardware': ['DELL', 'HPE'],
    'ai_software': ['PLTR', 'SNOW', 'AI', 'PATH', 'UPST', 'S'],
    'cybersecurity': ['CRWD', 'PANW', 'ZS'],
    'cloud': ['AMZN', 'ORCL', 'CRM', 'NOW']  # Excluding MSFT (already owned)
}

# Current holdings (skip these in detailed analysis)
CURRENT_HOLDINGS = ['CDNS', 'META', 'MSFT', 'MU', 'NVDA', 'TSM']

def scan_category(category_name, tickers):
    """Scan a category of stocks for opportunities"""
    print(f"\n{'='*80}")
    print(f"{category_name.upper()}")
    print('='*80)

    opportunities = []

    for ticker in tickers:
        if ticker in CURRENT_HOLDINGS:
            print(f"{ticker:6} | SKIPPED (already owned)")
            continue

        try:
            tech = get_technicals(ticker)

            if 'error' in tech:
                print(f"{ticker:6} | ERROR: {tech['error']}")
                continue

            signal = tech.get('signal', 'N/A')
            rsi = tech.get('rsi', 0)
            bullish_pct = tech.get('bullish_pct', 0)
            price = tech.get('price', 0)
            macd_signal = tech.get('macd_signal', 'neutral')
            confidence = tech.get('confidence', 'N/A')

            # Print summary
            print(f"{ticker:6} | {signal:12} | RSI: {rsi:5.1f} | Bullish: {bullish_pct:3.0f}% | "
                  f"Price: ${price:7.2f} | MACD: {macd_signal:8} | Conf: {confidence}")

            # Identify STRONG BUY candidates
            is_strong_buy = (
                signal in ['BUY', 'STRONG BUY'] and
                bullish_pct >= 60 and
                rsi < 70  # Not overbought
            )

            if is_strong_buy:
                opportunities.append({
                    'ticker': ticker,
                    'category': category_name,
                    'signal': signal,
                    'bullish_pct': bullish_pct,
                    'rsi': rsi,
                    'price': price,
                    'macd_signal': macd_signal,
                    'confidence': confidence,
                    'details': tech.get('details', '')
                })

        except Exception as e:
            print(f"{ticker:6} | ERROR: {str(e)}")

    return opportunities

def main():
    print("\n" + "="*80)
    print("AI ECOSYSTEM OPPORTUNITY DISCOVERY SCAN")
    print("="*80)
    print(f"Current holdings: {', '.join(CURRENT_HOLDINGS)}")
    print(f"Cash available: $9,041.17")
    print("="*80)

    all_opportunities = []

    # Scan each category
    for category, tickers in SCAN_UNIVERSE.items():
        opps = scan_category(category, tickers)
        all_opportunities.extend(opps)

    # Sort by conviction (bullish_pct)
    all_opportunities.sort(key=lambda x: x['bullish_pct'], reverse=True)

    # Print STRONG BUY opportunities
    print("\n" + "="*80)
    print("STRONG BUY OPPORTUNITIES (Ranked by Conviction)")
    print("="*80)

    if not all_opportunities:
        print("\nNo STRONG BUY opportunities found in current scan.")
    else:
        for i, opp in enumerate(all_opportunities, 1):
            print(f"\n{i}. {opp['ticker']} ({opp['category'].upper()})")
            print(f"   Signal: {opp['signal']} | Confidence: {opp['confidence']}")
            print(f"   Bullish Score: {opp['bullish_pct']:.0f}% | RSI: {opp['rsi']:.1f} | MACD: {opp['macd_signal']}")
            print(f"   Current Price: ${opp['price']:.2f}")
            print(f"   Entry Criteria: Price pullback to support or continuation on volume")
            if opp['details']:
                print(f"   Details: {opp['details'][:150]}...")

    # Save results
    with open('opportunity_scan_results.json', 'w') as f:
        json.dump({
            'scan_date': '2026-01-28',
            'cash_available': 9041.17,
            'current_holdings': CURRENT_HOLDINGS,
            'opportunities': all_opportunities
        }, f, indent=2)

    print(f"\n\nResults saved to opportunity_scan_results.json")
    print(f"Total opportunities found: {len(all_opportunities)}")

if __name__ == '__main__':
    main()
