#!/usr/bin/env python3
"""
Investor Profile Interview Tool
Gathers user investment goals, risk tolerance, and constraints
"""

from typing import Dict, Optional
import json
from datetime import datetime


class InvestorProfile:
    """Captures investor goals and preferences"""

    def __init__(self):
        self.profile = {}

    def interview(self) -> Dict:
        """Interactive interview to build investor profile"""

        print("\n" + "="*80)
        print("INVESTOR PROFILE INTERVIEW")
        print("="*80)
        print("Let's understand your investment goals and preferences.\n")

        # 1. Investment Goals
        print("1. What is your primary investment goal?")
        print("   a) Capital preservation (safety first)")
        print("   b) Income generation (dividends, interest)")
        print("   c) Balanced growth (moderate risk/reward)")
        print("   d) Aggressive growth (maximize returns)")
        print("   e) Speculation (high risk/high reward)")

        goal = input("\nYour choice (a-e): ").strip().lower()
        goal_map = {
            'a': 'capital_preservation',
            'b': 'income_generation',
            'c': 'balanced_growth',
            'd': 'aggressive_growth',
            'e': 'speculation'
        }
        self.profile['investment_goal'] = goal_map.get(goal, 'balanced_growth')

        # 2. Risk Tolerance
        print("\n2. How would you react if your portfolio dropped 20% in a month?")
        print("   a) Panic sell everything")
        print("   b) Sell some positions to reduce exposure")
        print("   c) Hold steady and wait for recovery")
        print("   d) Buy more at lower prices")

        risk = input("\nYour choice (a-d): ").strip().lower()
        risk_map = {
            'a': 'very_low',
            'b': 'low',
            'c': 'moderate',
            'd': 'high'
        }
        self.profile['risk_tolerance'] = risk_map.get(risk, 'moderate')

        # 3. Time Horizon
        print("\n3. What is your investment time horizon?")
        print("   a) Less than 1 year (short-term)")
        print("   b) 1-3 years (medium-term)")
        print("   c) 3-5 years (long-term)")
        print("   d) 5+ years (very long-term)")

        horizon = input("\nYour choice (a-d): ").strip().lower()
        horizon_map = {
            'a': 'short_term',
            'b': 'medium_term',
            'c': 'long_term',
            'd': 'very_long_term'
        }
        self.profile['time_horizon'] = horizon_map.get(horizon, 'long_term')

        # 4. Investment Amount
        print("\n4. How much are you planning to invest?")
        try:
            amount = float(input("Amount in USD: $").strip().replace(',', ''))
            self.profile['investment_amount'] = amount
        except ValueError:
            print("Invalid amount, setting to $10,000 default")
            self.profile['investment_amount'] = 10000

        # 5. Existing Portfolio
        print("\n5. Do you have an existing investment portfolio?")
        has_portfolio = input("(yes/no): ").strip().lower()
        self.profile['has_existing_portfolio'] = has_portfolio == 'yes'

        if self.profile['has_existing_portfolio']:
            print("\n6. Briefly describe your current holdings:")
            holdings = input("(e.g., '60% stocks, 30% bonds, 10% cash'): ").strip()
            self.profile['current_holdings'] = holdings

        # 7. Sector Preferences
        print("\n7. Any sector preferences or restrictions?")
        print("   Examples: 'avoid oil/gas', 'prefer tech', 'ESG only', etc.")
        preferences = input("Preferences (or press Enter to skip): ").strip()
        self.profile['sector_preferences'] = preferences if preferences else "none"

        # 8. Income Needs
        print("\n8. Do you need income from investments (dividends)?")
        income_need = input("(yes/no): ").strip().lower()
        self.profile['needs_income'] = income_need == 'yes'

        # 9. Tax Considerations
        print("\n9. Are you investing in a tax-advantaged account?")
        print("   (e.g., 401k, IRA, Roth IRA)")
        tax_advantaged = input("(yes/no): ").strip().lower()
        self.profile['tax_advantaged'] = tax_advantaged == 'yes'

        # 10. Experience Level
        print("\n10. What is your investment experience level?")
        print("    a) Beginner (new to investing)")
        print("    b) Intermediate (some experience)")
        print("    c) Advanced (extensive experience)")

        exp = input("\nYour choice (a-c): ").strip().lower()
        exp_map = {
            'a': 'beginner',
            'b': 'intermediate',
            'c': 'advanced'
        }
        self.profile['experience_level'] = exp_map.get(exp, 'intermediate')

        # Add timestamp
        self.profile['created_at'] = datetime.now().isoformat()

        return self.profile

    def get_analysis_context(self) -> str:
        """Generate context string for ReAct agent"""

        goal_descriptions = {
            'capital_preservation': 'prioritize safety and capital preservation over growth',
            'income_generation': 'focus on dividend-paying stocks and income generation',
            'balanced_growth': 'seek moderate growth with balanced risk',
            'aggressive_growth': 'maximize capital appreciation with higher risk tolerance',
            'speculation': 'pursue high-risk, high-reward opportunities'
        }

        risk_descriptions = {
            'very_low': 'very conservative (minimize volatility)',
            'low': 'conservative (limited risk tolerance)',
            'moderate': 'moderate risk tolerance',
            'high': 'high risk tolerance (comfortable with volatility)'
        }

        context = f"""
INVESTOR PROFILE CONTEXT:

Investment Goal: {goal_descriptions.get(self.profile.get('investment_goal', 'balanced_growth'))}
Risk Tolerance: {risk_descriptions.get(self.profile.get('risk_tolerance', 'moderate'))}
Time Horizon: {self.profile.get('time_horizon', 'long_term').replace('_', ' ')}
Investment Amount: ${self.profile.get('investment_amount', 0):,.2f}
Experience Level: {self.profile.get('experience_level', 'intermediate')}
Needs Income: {'Yes' if self.profile.get('needs_income', False) else 'No'}
Tax-Advantaged Account: {'Yes' if self.profile.get('tax_advantaged', False) else 'No'}
Sector Preferences: {self.profile.get('sector_preferences', 'none')}

IMPORTANT: Tailor your analysis and recommendations to match this investor's profile.
- Adjust risk assessment based on their risk tolerance
- Consider their time horizon when evaluating volatility
- Respect sector preferences and restrictions
- Account for tax implications if not in tax-advantaged account
- Recommend position sizing appropriate for their investment amount
"""
        return context.strip()

    def save_to_file(self, filename: str = "investor_profile.json"):
        """Save profile to JSON file"""
        with open(filename, 'w') as f:
            json.dump(self.profile, f, indent=2)
        print(f"\n✓ Profile saved to {filename}")

    def load_from_file(self, filename: str = "investor_profile.json") -> Dict:
        """Load profile from JSON file"""
        try:
            with open(filename, 'r') as f:
                self.profile = json.load(f)
            print(f"\n✓ Profile loaded from {filename}")
            return self.profile
        except FileNotFoundError:
            print(f"\n✗ Profile file {filename} not found")
            return {}


if __name__ == "__main__":
    # Test the interview
    profiler = InvestorProfile()
    profile = profiler.interview()

    print("\n" + "="*80)
    print("PROFILE SUMMARY")
    print("="*80)
    print(json.dumps(profile, indent=2))

    print("\n" + "="*80)
    print("ANALYSIS CONTEXT FOR REACT AGENT")
    print("="*80)
    print(profiler.get_analysis_context())

    # Save to file
    profiler.save_to_file()
