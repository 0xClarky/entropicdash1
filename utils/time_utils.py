from datetime import datetime
import pytz
import pandas as pd

def get_time_ago(timestamp):
    """Convert timestamp to human readable time ago string"""
    now = pd.Timestamp.now(tz='UTC')
    
    # Convert timestamp to UTC if it has a timezone, or localize if it doesn't
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize('UTC')
    else:
        timestamp = timestamp.tz_convert('UTC')
    
    diff = now - timestamp
    
    seconds = diff.total_seconds()
    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes}m ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours}h ago"
    else:
        days = int(seconds / 86400)
        return f"{days}d ago"