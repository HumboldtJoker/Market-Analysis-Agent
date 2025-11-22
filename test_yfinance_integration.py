#!/usr/bin/env python3
"""
Quick test of Yahoo Finance integration
"""

import sys
sys.path.insert(0, '.')

from autoinvestor_react import (
    get_stock_price,
    get_company_financials,
    get_analyst_ratings,
    calculate_valuation,
    risk_assessment
)

def test_tool(tool_name, function, ticker="AAPL"):
    """Test a single tool"""
    print(f"\n{'='*80}")
    print(f"Testing: {tool_name}")
    print(f"{'='*80}")
    try:
        result = function(ticker)
        print(f"[OK] Success!")
        print(f"\nData received:")
        for key, value in result.items():
            print(f"  {key}: {value}")
        return True
    except Exception as e:
        print(f"[ERROR] {e}")
        return False

if __name__ == "__main__":
    print("\nYahoo Finance Integration Test")
    print(f"{'='*80}\n")

    # Test each tool
    results = {}

    results["get_stock_price"] = test_tool(
        "get_stock_price",
        get_stock_price,
        "AAPL"
    )

    results["get_company_financials"] = test_tool(
        "get_company_financials",
        get_company_financials,
        "AAPL"
    )

    results["get_analyst_ratings"] = test_tool(
        "get_analyst_ratings",
        get_analyst_ratings,
        "AAPL"
    )

    results["calculate_valuation"] = test_tool(
        "calculate_valuation",
        calculate_valuation,
        "AAPL"
    )

    results["risk_assessment"] = test_tool(
        "risk_assessment",
        risk_assessment,
        "AAPL"
    )

    # Summary
    print(f"\n{'='*80}")
    print("TEST SUMMARY")
    print(f"{'='*80}")

    for tool, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status}: {tool}")

    total_tests = len(results)
    passed = sum(results.values())

    print(f"\nTotal: {passed}/{total_tests} tests passed")

    if passed == total_tests:
        print("\n[SUCCESS] All Yahoo Finance tools working correctly!")
    else:
        print(f"\n[FAILURE] {total_tests - passed} tool(s) failed")
