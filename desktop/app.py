"""
AutoInvestor Desktop - Flask Backend
Exposes CLI functionality as web API for PyWebView interface
"""

import os
import sys
import json
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import threading
import io
from contextlib import redirect_stdout

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)


def capture_output(func, *args, **kwargs):
    """Capture stdout from a function that prints"""
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            return {"error": str(e), "output": buffer.getvalue()}
    return {"output": buffer.getvalue(), "result": result}


@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')


@app.route('/api/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "anthropic_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "rapidapi_key": bool(os.environ.get("RAPIDAPI_KEY")),
        "fred_key": bool(os.environ.get("FRED_API_KEY"))
    })


@app.route('/api/technicals/<ticker>')
def technicals(ticker):
    """Get technical analysis for a ticker"""
    try:
        from technical_indicators import analyze_technicals
        result = analyze_technicals(ticker.upper())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/news/<ticker>')
def news_sentiment(ticker):
    """Get news sentiment for a ticker"""
    try:
        from news_sentiment import analyze_news_sentiment
        result = analyze_news_sentiment(ticker.upper())
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/congress/aggregate')
def congress_aggregate():
    """Get aggregate congressional trading patterns"""
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        return jsonify({"error": "RAPIDAPI_KEY not configured"}), 400

    try:
        from congressional_trades_aggregate import get_aggregate_analysis
        result = get_aggregate_analysis(api_key=api_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/congress/<ticker>')
def congress_ticker(ticker):
    """Get congressional trades for a specific ticker"""
    api_key = os.environ.get("RAPIDAPI_KEY")
    if not api_key:
        return jsonify({"error": "RAPIDAPI_KEY not configured"}), 400

    try:
        from congressional_trades import analyze_congressional_trades
        result = analyze_congressional_trades(ticker.upper(), api_key=api_key)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/portfolio', methods=['POST'])
def portfolio_correlation():
    """Analyze portfolio correlation"""
    data = request.get_json()
    tickers = data.get('tickers', [])

    if len(tickers) < 2:
        return jsonify({"error": "Need at least 2 tickers"}), 400

    try:
        from portfolio_correlation import analyze_portfolio_correlation
        result = analyze_portfolio_correlation([t.upper() for t in tickers])
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sectors', methods=['POST'])
def sector_allocation():
    """Analyze sector allocation"""
    data = request.get_json()
    holdings = data.get('holdings', {})

    if not holdings:
        return jsonify({"error": "No holdings provided"}), 400

    try:
        from sector_allocation import analyze_sector_allocation
        result = analyze_sector_allocation(holdings)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/macro')
def macro_regime():
    """Get current market macro regime"""
    try:
        from macro_agent import MacroAgent
        agent = MacroAgent()
        regime = agent.get_market_regime()
        regime['formatted_report'] = agent.format_report()
        return jsonify(regime)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/sec/<ticker>')
def sec_filings(ticker):
    """Analyze SEC filings"""
    query = request.args.get('query', None)

    try:
        from sec_filings_rag import analyze_sec_filings
        result = analyze_sec_filings(ticker.upper(), query=query)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analyze/<ticker>', methods=['POST'])
def full_analysis(ticker):
    """Run full ReAct analysis (this can take a while)"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return jsonify({"error": "ANTHROPIC_API_KEY not configured"}), 400

    data = request.get_json() or {}
    collaborative = data.get('collaborative', False)

    try:
        from autoinvestor_react import ReActAgent, Tool
        from autoinvestor_react import get_stock_price, get_company_financials
        from autoinvestor_react import get_analyst_ratings, calculate_valuation, risk_assessment
        from technical_indicators import analyze_technicals
        from news_sentiment import analyze_news_sentiment

        if collaborative:
            from collaborative_agent import CollaborativeAgent
            agent = CollaborativeAgent(api_key=api_key, max_iterations=10)
        else:
            agent = ReActAgent(api_key=api_key, max_iterations=10)

        # Register tools
        agent.tools.register(Tool(
            name="get_stock_price",
            description="Get current stock price, volume, and 52-week range",
            func=get_stock_price,
            parameters={"ticker": "Stock ticker symbol"}
        ))
        agent.tools.register(Tool(
            name="get_company_financials",
            description="Get company financial metrics",
            func=get_company_financials,
            parameters={"ticker": "Stock ticker symbol"}
        ))
        agent.tools.register(Tool(
            name="get_analyst_ratings",
            description="Get analyst consensus ratings",
            func=get_analyst_ratings,
            parameters={"ticker": "Stock ticker symbol"}
        ))
        agent.tools.register(Tool(
            name="calculate_valuation",
            description="Calculate valuation metrics",
            func=calculate_valuation,
            parameters={"ticker": "Stock ticker symbol"}
        ))
        agent.tools.register(Tool(
            name="risk_assessment",
            description="Assess investment risk",
            func=risk_assessment,
            parameters={"ticker": "Stock ticker symbol"}
        ))
        agent.tools.register(Tool(
            name="analyze_technicals",
            description="Technical analysis",
            func=analyze_technicals,
            parameters={"ticker": "Stock ticker symbol"}
        ))
        agent.tools.register(Tool(
            name="analyze_news_sentiment",
            description="News sentiment analysis",
            func=analyze_news_sentiment,
            parameters={"ticker": "Stock ticker symbol"}
        ))

        query = f"Provide a comprehensive investment analysis of {ticker.upper()}."

        if collaborative:
            result = agent.run_collaborative(query, max_questions=3, verbose=False)
        else:
            result = agent.run(query, verbose=False)

        return jsonify({
            "ticker": ticker.upper(),
            "mode": "collaborative" if collaborative else "standard",
            "answer": result.get('answer', ''),
            "iterations": result.get('iterations', 0)
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500



# Settings file path
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')


def load_settings_file():
    """Load settings from file and apply to environment"""
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                import json
                settings = json.load(f)
                if settings.get('anthropic_key'):
                    os.environ['ANTHROPIC_API_KEY'] = settings['anthropic_key']
                if settings.get('rapidapi_key'):
                    os.environ['RAPIDAPI_KEY'] = settings['rapidapi_key']
                if settings.get('fred_key'):
                    os.environ['FRED_API_KEY'] = settings['fred_key']
                return settings
        except Exception:
            pass
    return {}


# Load settings on import
load_settings_file()


@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get current settings (masked)"""
    settings = load_settings_file()
    # Return masked versions for display
    return jsonify({
        "anthropic_key": settings.get('anthropic_key', ''),
        "rapidapi_key": settings.get('rapidapi_key', ''),
        "fred_key": settings.get('fred_key', '')
    })


@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Save settings to file and apply to environment"""
    import json
    data = request.get_json()
    
    settings = {
        'anthropic_key': data.get('anthropic_key', ''),
        'rapidapi_key': data.get('rapidapi_key', ''),
        'fred_key': data.get('fred_key', '')
    }
    
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f)
        
        # Apply to environment immediately
        if settings['anthropic_key']:
            os.environ['ANTHROPIC_API_KEY'] = settings['anthropic_key']
        if settings['rapidapi_key']:
            os.environ['RAPIDAPI_KEY'] = settings['rapidapi_key']
        if settings['fred_key']:
            os.environ['FRED_API_KEY'] = settings['fred_key']
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def run_server(port=5000, debug=False):

    """Run the Flask server"""
    app.run(host='127.0.0.1', port=port, debug=debug, use_reloader=False)


if __name__ == '__main__':
    run_server(debug=True)
