import requests
from flask import Flask, jsonify, render_template
import time
import re
import json
import os
import threading
from datetime import datetime, timedelta

app = Flask(__name__)

# Data Persistence File
HISTORY_FILE = "gold_history.json"

# Load history on startup
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r') as f:
                data = json.load(f)
                return data
        except:
            pass
    return []

# Save history with Today's Cleanup Logic
def save_history(data_point):
    history = load_history()
    
    # Add new point
    # Avoid duplicates if timestamp is identical
    if not history or history[-1]['timestamp'] != data_point['timestamp']:
        history.append(data_point)
    
    # Cleanup: Keep only data from Today 00:00:00 onwards
    # Get today's midnight timestamp
    now = datetime.now()
    midnight = datetime(now.year, now.month, now.day).timestamp()
    
    # Filter old data (keep only points >= midnight)
    new_history = [p for p in history if p.get('timestamp', 0) >= midnight]
    
    # Write back only if changed or cleaned
    if len(new_history) != len(history) or len(new_history) > 0:
        with open(HISTORY_FILE, 'w') as f:
            json.dump(new_history, f)
    
    return new_history

# Zheshang Bank Real-time Gold Price API (via JD Gold)
# Source: https://api.jdjygold.com/gw2/generic/jrm/h5/m/stdLatestPrice?productSku=1961543816
DATA_URL = "https://api.jdjygold.com/gw2/generic/jrm/h5/m/stdLatestPrice?productSku=1961543816"

def fetch_gold_price():
    headers = {
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
        "Referer": "https://m.jdjygold.com/"
    }
    try:
        response = requests.get(DATA_URL, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "resultData" in data:
                info = data["resultData"]["datas"]
                
                price = float(info["price"])
                yesterday_price = float(info["yesterdayPrice"])
                
                # JD API returns timestamp in ms, convert to seconds
                timestamp = int(info["time"]) / 1000
                time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp))
                
                high = max(price, yesterday_price)
                low = min(price, yesterday_price)
                
                data_point = {
                    "name": "浙商积存金",
                    "price": price,
                    "open": yesterday_price, 
                    "high": high, 
                    "low": low,
                    "last_close": yesterday_price,
                    "time": time_str,
                    "timestamp": timestamp
                }
                
                # Persist this point
                save_history(data_point)
                
                return data_point
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

# Background Thread for Continuous Fetching
def background_fetcher():
    print("Starting background data fetcher...")
    while True:
        try:
            fetch_gold_price()
        except Exception as e:
            print(f"Background fetch error: {e}")
        time.sleep(10) # Fetch every 10 seconds

# Start background thread
# Daemon=True ensures it dies when main app dies
fetch_thread = threading.Thread(target=background_fetcher, daemon=True)
fetch_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/price')
def get_price():
    data = fetch_gold_price()
    if data:
        return jsonify({"success": True, "data": data})
    else:
        return jsonify({
            "success": False, 
            "message": "Failed to fetch data",
            "data": {
                "name": "浙商积存金(Mock)",
                "price": 0.0,
                "time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        })

@app.route('/api/history')
def get_history():
    history = load_history()
    return jsonify({"success": True, "data": history})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
