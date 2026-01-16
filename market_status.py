"""Quick market status check - run at session start"""
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetCalendarRequest
from dotenv import load_dotenv
from datetime import date, datetime, timedelta
import pytz
import os

load_dotenv()

def get_market_status():
    """Returns current market status with dates"""
    client = TradingClient(os.getenv('ALPACA_API_KEY'), os.getenv('ALPACA_SECRET_KEY'), paper=True)
    eastern = pytz.timezone('US/Eastern')
    now = datetime.now(eastern)
    today = date.today()
    
    # Get calendar for this week
    request = GetCalendarRequest(start=today, end=today + timedelta(days=7))
    calendar = client.get_calendar(request)
    
    # Check if today is a trading day
    trading_days = {c.date: c for c in calendar}
    is_trading_day = today in trading_days
    
    # Find next trading day
    next_trading = None
    for c in calendar:
        if c.date > today or (c.date == today and now.time() < c.close.time()):
            next_trading = c
            break
    
    # Check if market is currently open
    market_open = False
    if is_trading_day:
        cal = trading_days[today]
        market_open = cal.open.time() <= now.time() <= cal.close.time()
    
    return {
        'now': now.strftime('%A, %B %d, %Y %I:%M %p ET'),
        'today': today.strftime('%A, %B %d, %Y'),
        'day_of_week': today.strftime('%A'),
        'is_trading_day': is_trading_day,
        'market_open': market_open,
        'next_trading_day': next_trading.date.strftime('%A, %B %d') if next_trading else 'Unknown',
        'upcoming_days': [(c.date.strftime('%a %b %d'), 'OPEN') for c in calendar[:5]]
    }

if __name__ == '__main__':
    status = get_market_status()
    print('=' * 50)
    print('MARKET STATUS')
    print('=' * 50)
    print(f"Current Time: {status['now']}")
    print(f"Today: {status['today']}")
    print(f"Trading Day: {'YES' if status['is_trading_day'] else 'NO (Holiday/Weekend)'}")
    print(f"Market Open: {'YES' if status['market_open'] else 'NO'}")
    print(f"Next Trading: {status['next_trading_day']}")
    print()
    print('Upcoming Trading Days:')
    for day, st in status['upcoming_days']:
        print(f'  {day}: {st}')
    print('=' * 50)
