import requests
import os

from flask import Flask, jsonify, render_template, request
import time
import re
import json
import os
import threading
from datetime import datetime, timedelta

app = Flask(__name__)

# Data Persistence Files
HISTORY_FILE = "gold_history.json"
SETTINGS_FILE = "settings.json"

# Global State for Notifications
last_high_alert_time = 0
last_low_alert_time = 0
current_high_target = None
current_low_target = None
NOTIFICATION_COOLDOWN = 60  # 1 minute cooldown

# Load settings on startup
def load_settings():
    default_settings = {
        "telegram_token": "",
        "telegram_chat_id": "",
        "price_low": 0,
        "price_high": 0,
        "notify_enabled": False
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return {**default_settings, **json.load(f)}
        except:
            pass
    return default_settings

def save_settings_to_file(settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

# Telegram Helpers
def send_telegram_message(token, chat_id, message):
    if not token or not chat_id:
        return False, "Missing token or chat_id"
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    
    # Load settings to check for custom proxy
    settings = load_settings()
    custom_proxy = settings.get("proxy_url", "").strip()
    
    try:
        proxies = None
        if custom_proxy:
            print(f"Using Custom Proxy: {custom_proxy}")
            proxies = {"http": custom_proxy, "https": custom_proxy}
        
        # 1. Try with custom proxy (if set) or system proxy (default)
        print(f"Sending Telegram message to {chat_id}...")
        response = requests.post(url, json=payload, timeout=10, proxies=proxies)
        
        if response.status_code == 200:
            return True, "Message sent"
        else:
            return False, f"Telegram API Error: {response.text}"
    except Exception as e:
        print(f"Telegram Send Error: {e}")
        # Only try fallback if no custom proxy was enforced
        if not custom_proxy:
             # 2. Try with common local proxies if system proxy failed
            for port in [7890, 10809]:
                try:
                    print(f"Retrying with local proxy 127.0.0.1:{port}...")
                    proxies = {
                        "http": f"http://127.0.0.1:{port}",
                        "https": f"http://127.0.0.1:{port}"
                    }
                    response = requests.post(url, json=payload, timeout=10, proxies=proxies)
                    if response.status_code == 200:
                        return True, "Message sent (via local proxy)"
                except:
                    continue

        return False, f"Connection Failed. Error: {str(e)}"

def get_telegram_updates(token):
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    # Load settings to check for custom proxy
    settings = load_settings()
    custom_proxy = settings.get("proxy_url", "").strip()

    try:
        proxies = None
        if custom_proxy:
            print(f"Using Custom Proxy: {custom_proxy}")
            proxies = {"http": custom_proxy, "https": custom_proxy}

        # 1. Try with custom proxy (if set) or system proxy (default)
        print("Fetching Telegram updates...")
        response = requests.get(url, timeout=10, proxies=proxies)
        
        if response.status_code == 200:
            return response.json()
        print(f"Telegram Updates Error: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Telegram Fetch Error: {e}")
        # Only try fallback if no custom proxy was enforced
        if not custom_proxy:
            # 2. Try with common local proxies if system proxy failed
            for port in [7890, 10809]:
                try:
                    print(f"Retrying with local proxy 127.0.0.1:{port}...")
                    proxies = {
                        "http": f"http://127.0.0.1:{port}",
                        "https": f"http://127.0.0.1:{port}"
                    }
                    response = requests.get(url, timeout=10, proxies=proxies)
                    if response.status_code == 200:
                        return response.json()
                except:
                    continue

    return None

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
        # Force no proxy for JD Gold API to avoid SSL/Proxy errors
        proxies = {"http": None, "https": None}
        response = requests.get(DATA_URL, headers=headers, timeout=5, proxies=proxies)
        
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
                
                # Check Notifications
                check_and_notify(price, time_str)

                return data_point
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

def check_and_notify(price, time_str):
    global last_high_alert_time, last_low_alert_time, current_high_target, current_low_target
    
    settings = load_settings()
    if not settings.get("notify_enabled"):
        return

    token = settings.get("telegram_token")
    chat_id = settings.get("telegram_chat_id")
    
    # Base user settings
    user_low = float(settings.get("price_low") or 0)
    user_high = float(settings.get("price_high") or 0)

    # Initialize dynamic targets if not set
    if current_high_target is None:
        current_high_target = user_high
    if current_low_target is None:
        current_low_target = user_low

    now = time.time()
    msg = ""

    # --- High Alert Logic ---
    if user_high > 0:
        # Reset Logic: If price drops below original user setting, reset the dynamic target
        if price < user_high:
            if current_high_target != user_high:
                print(f"Price {price} < Base High {user_high}. Resetting High Target to {user_high}")
            current_high_target = user_high
        
        # Trigger Logic
        elif price >= current_high_target:
            # Check Cooldown (1 minute)
            if now - last_high_alert_time >= NOTIFICATION_COOLDOWN:
                msg = f"� *High Price Alert*\nCurrent: ¥{price}\nTarget Reached: ¥{current_high_target}\nTime: {time_str}"
                
                # Update State
                last_high_alert_time = now
                current_high_target += 5  # Step up by 5
                print(f"High Alert Sent. Next High Target: {current_high_target}")

    # --- Low Alert Logic ---
    if user_low > 0:
        # Reset Logic: If price rises above original user setting, reset the dynamic target
        if price > user_low:
            if current_low_target != user_low:
                print(f"Price {price} > Base Low {user_low}. Resetting Low Target to {user_low}")
            current_low_target = user_low
            
        # Trigger Logic
        elif price <= current_low_target:
            # Check Cooldown (1 minute)
            if now - last_low_alert_time >= NOTIFICATION_COOLDOWN:
                msg = f"� *Low Price Alert*\nCurrent: ¥{price}\nTarget Reached: ¥{current_low_target}\nTime: {time_str}"
                
                # Update State
                last_low_alert_time = now
                current_low_target -= 5 # Step down by 5
                print(f"Low Alert Sent. Next Low Target: {current_low_target}")
    
    if msg:
        success, _ = send_telegram_message(token, chat_id, msg)
        if success:
            print(f"Notification sent: {msg}")

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

# --- Notification API Routes ---

@app.route('/api/settings', methods=['GET', 'POST'])
def handle_settings():
    if request.method == 'POST':
        data = request.json
        settings = load_settings()
        # Update only valid keys
        for key in ["telegram_token", "telegram_chat_id", "price_low", "price_high", "notify_enabled", "proxy_url"]:
            if key in data:
                settings[key] = data[key]
        
        save_settings_to_file(settings)
        return jsonify({"success": True, "settings": settings})
    else:
        return jsonify({"success": True, "settings": load_settings()})

@app.route('/api/telegram/test', methods=['POST'])
def test_telegram():
    data = request.json
    token = data.get('token')
    chat_id = data.get('chat_id')
    
    if not token or not chat_id:
        return jsonify({"success": False, "message": "Missing token or chat_id"})
    
    success, msg = send_telegram_message(token, chat_id, "🔔 *Test Notification*\nSystem is connected successfully!")
    return jsonify({"success": success, "message": msg})

@app.route('/api/telegram/get_id', methods=['POST'])
def get_chat_id():
    data = request.json
    token = data.get('token')
    
    if not token:
        return jsonify({"success": False, "message": "Missing token"})
    
    updates = get_telegram_updates(token)
    if updates and updates.get("ok"):
        result = updates.get("result", [])
        if result:
            # Get the last message's chat id
            last_msg = result[-1]
            if "message" in last_msg:
                chat = last_msg["message"]["chat"]
                return jsonify({
                    "success": True, 
                    "chat_id": str(chat["id"]),
                    "username": chat.get("username", "Unknown"),
                    "first_name": chat.get("first_name", "")
                })
    
    return jsonify({"success": False, "message": "No recent messages found. Please send /start to your bot."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
