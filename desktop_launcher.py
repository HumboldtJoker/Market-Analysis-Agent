#!/usr/bin/env python3
"""
Desktop Wrapper for Market Analysis Agent
Provides a simple desktop interface for running market analysis
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys
import os
import threading
import json
from datetime import datetime

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from mcp_react_agent import create_mcp_agent
    from mcp_wrapper import (
        analyze_stock, technical_analysis_wrapper,
        portfolio_analysis_wrapper, macro_analysis_wrapper
    )
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

class MarketAnalysisDesktopApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Market Analysis Agent - Desktop Interface")
        self.root.geometry("800x600")

        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)

        # Title
        title_label = ttk.Label(main_frame, text="Market Analysis Agent",
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))

        # Analysis Type Selection
        ttk.Label(main_frame, text="Analysis Type:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.analysis_type = ttk.Combobox(main_frame, values=[
            "Stock Analysis", "Technical Analysis", "Portfolio Analysis", "Macro Analysis"
        ], state="readonly", width=20)
        self.analysis_type.set("Stock Analysis")
        self.analysis_type.grid(row=1, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)

        # Ticker/Input
        ttk.Label(main_frame, text="Ticker/Input:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.ticker_entry = ttk.Entry(main_frame, width=20)
        self.ticker_entry.insert(0, "AAPL")
        self.ticker_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)

        # Query/Question
        ttk.Label(main_frame, text="Question:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.query_entry = ttk.Entry(main_frame, width=40)
        self.query_entry.insert(0, "Should I invest in this stock?")
        self.query_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), padx=(10, 0), pady=5)

        # Analyze Button
        self.analyze_button = ttk.Button(main_frame, text="Analyze", command=self.run_analysis)
        self.analyze_button.grid(row=1, column=2, rowspan=3, padx=(10, 0), pady=5, sticky=(tk.N, tk.S))

        # Results Area
        ttk.Label(main_frame, text="Analysis Results:").grid(row=4, column=0, sticky=(tk.W, tk.N), pady=(20, 5))

        self.results_text = scrolledtext.ScrolledText(main_frame, width=80, height=25, wrap=tk.WORD)
        self.results_text.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))

        # Status Bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready for analysis")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_bar.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))

        # Bind Enter key to analysis
        self.root.bind('<Return>', lambda event: self.run_analysis())

        # Initial welcome message
        self.show_welcome_message()

    def show_welcome_message(self):
        welcome_msg = """
Welcome to Market Analysis Agent Desktop Interface!

This tool provides AI-powered investment analysis using real-time market data.

Quick Start:
1. Select analysis type (Stock Analysis, Technical Analysis, etc.)
2. Enter ticker symbol (e.g., AAPL, TSLA, MSFT)
3. Enter your question or use the default
4. Click "Analyze" or press Enter

Features:
- Real-time stock prices and financials
- Technical indicators (SMA, RSI, MACD, Bollinger Bands)
- Portfolio correlation analysis
- Macro economic regime detection
- Paper trading integration ready

Example Queries:
- "Should I buy this stock for long-term growth?"
- "Is this a good entry point for day trading?"
- "How risky is this investment?"
- "What's the current market sentiment?"

Ready to analyze! Enter a ticker and click Analyze.
        """
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, welcome_msg)

    def run_analysis(self):
        # Get inputs
        analysis_type = self.analysis_type.get()
        ticker = self.ticker_entry.get().strip().upper()
        query = self.query_entry.get().strip()

        if not ticker:
            messagebox.showerror("Error", "Please enter a ticker symbol")
            return

        # Disable button and show status
        self.analyze_button.config(state='disabled')
        self.status_var.set(f"Running {analysis_type.lower()}...")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"Analyzing {ticker}...\n\n")
        self.root.update()

        # Run analysis in thread to prevent GUI freezing
        threading.Thread(target=self.perform_analysis,
                        args=(analysis_type, ticker, query),
                        daemon=True).start()

    def perform_analysis(self, analysis_type, ticker, query):
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if analysis_type == "Stock Analysis":
                result = analyze_stock(ticker, query, False)
            elif analysis_type == "Technical Analysis":
                result = technical_analysis_wrapper(ticker)
            elif analysis_type == "Portfolio Analysis":
                # For portfolio analysis, treat ticker as comma-separated list
                tickers = [t.strip() for t in ticker.split(',')]
                result = portfolio_analysis_wrapper(json.dumps(tickers))
            elif analysis_type == "Macro Analysis":
                result = macro_analysis_wrapper()
            else:
                result = "Unknown analysis type"

            # Update GUI in main thread
            self.root.after(0, self.display_results, result, timestamp, analysis_type, ticker)

        except Exception as e:
            error_msg = f"Error during analysis: {str(e)}"
            self.root.after(0, self.display_results, error_msg, timestamp, analysis_type, ticker)

    def display_results(self, result, timestamp, analysis_type, ticker):
        # Clear and display results
        self.results_text.delete(1.0, tk.END)

        header = f"""
{'='*60}
{analysis_type.upper()}: {ticker}
Timestamp: {timestamp}
{'='*60}

"""
        self.results_text.insert(tk.END, header)
        self.results_text.insert(tk.END, result)

        # Re-enable button and update status
        self.analyze_button.config(state='normal')
        self.status_var.set(f"Analysis complete for {ticker}")

        # Auto-scroll to top
        self.results_text.see(1.0)

def main():
    """Main entry point for desktop app"""
    try:
        root = tk.Tk()
        app = MarketAnalysisDesktopApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Failed to start desktop app: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()