# backend/app.py

from dotenv import load_dotenv
load_dotenv()

import praw
import joblib
import pandas as pd
#import config # Your API keys


from flask import Flask, jsonify, send_from_directory, request, session
from flask_cors import CORS
import sqlite3
import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

# --- 1. LOAD THE TRAINED MODEL AND VECTORIZER ---
print("Loading model and vectorizer...")
model = joblib.load('sentiment_model.pkl')
vectorizer = joblib.load('tfidf_vectorizer.pkl')
print("Model and vectorizer loaded successfully.")

# Import the text cleaning function from your other script
# Corrected the filename from sentiment_analysis to sentiment_analyzer
from sentiment_analysis import clean_text

# --- DATABASE SETUP ---
DATABASE_FILE = 'sentiment_history.db'

def init_db():
    """Initializes the database and creates the table if it doesn't exist."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sentiment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            sentiment_score REAL NOT NULL,
            mention_count INTEGER NOT NULL,
            timestamp DATETIME NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

# Create users table if not exists
with sqlite3.connect(DATABASE_FILE) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    """)

# Create user_favorites table if not exists
with sqlite3.connect(DATABASE_FILE) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            UNIQUE(user_id, ticker)
        )
    """)

# Create user_watchlist table if not exists
with sqlite3.connect(DATABASE_FILE) as conn:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS user_watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            ticker TEXT NOT NULL,
            UNIQUE(user_id, ticker)
        )
    """)

# --- UTILITY FUNCTION TO LOAD TICKERS ---
def load_tickers_from_csv(filename):
    """Loads stock tickers from a CSV file into a Python set."""
    try:
        df = pd.read_csv(filename)
        # Ensure the column name 'Symbol' matches your CSV file.
        tickers = set(df['Symbol'].unique())
        print(f"Successfully loaded {len(tickers)} tickers from {filename}.")
        return tickers
    except FileNotFoundError:
        print(f"Error: The file {filename} was not found. Defaulting to empty set.")
        return set()
    except KeyError:
        print(f"Error: The CSV file {filename} does not have a 'Symbol' column. Defaulting to empty set.")
        return set()

# --- 2. SETUP FLASK APP ---
# Set static_folder to the frontend directory (relative to backend/app.py)
app = Flask(__name__, static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), '../frontend')), static_url_path='')
app.secret_key = os.environ.get('SECRET_KEY')
CORS(app) # This is important to allow your frontend to make requests to this backend

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
    def __init__(self, id, username, email, password_hash):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash

@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect(DATABASE_FILE)
    c = conn.cursor()
    c.execute("SELECT id, username, email, password_hash FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return User(*row)
    return None

# NEW: Add a root route to check if the server is running
@app.route('/')
def index():
    return jsonify({"status": "API is running successfully"})

# --- 3. CREATE THE API ENDPOINT ---
@app.route('/api/analyze', methods=['GET'])
def analyze_sentiment():
    print("Received API request to /api/analyze (DB mode)")
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    # Get the latest timestamp in the table
    cursor.execute('SELECT MAX(timestamp) FROM ticker_mentions')
    latest_ts = cursor.fetchone()[0]
    if not latest_ts:
        conn.close()
        return jsonify({})
    # Get all tickers for the latest timestamp
    cursor.execute('SELECT ticker, mention_count, sentiment_score, sentiment_label FROM ticker_mentions WHERE timestamp = ?', (latest_ts,))
    rows = cursor.fetchall()
    conn.close()
    results = {}
    for ticker, mention_count, sentiment_score, sentiment_label in rows:
        results[ticker] = {
            "mentions": mention_count,
            "sentiment": sentiment_label,
            "score": round(sentiment_score, 2)
        }
    return jsonify(results)

@app.route('/api/history/<ticker>', methods=['GET'])
def get_history(ticker):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, sentiment_score FROM ticker_mentions WHERE ticker = ? ORDER BY timestamp ASC', (ticker.upper(),))
    history = cursor.fetchall()
    conn.close()
    labels = []
    scores = []
    for ts, score in history:
        try:
            dt = datetime.datetime.fromtimestamp(ts)
            labels.append(dt.strftime('%b %d, %H:%M'))
        except Exception:
            labels.append(str(ts))
        scores.append(round(score, 2))
    return jsonify({"labels": labels, "scores": scores})

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    if not username or not email or not password:
        return jsonify({'error': 'Missing fields'}), 400
    password_hash = generate_password_hash(password)
    try:
        with sqlite3.connect(DATABASE_FILE) as conn:
            conn.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)", (username, email, password_hash))
        return jsonify({'message': 'User registered successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username or email already exists'}), 409

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'error': 'Missing fields'}), 400
    with sqlite3.connect(DATABASE_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT id, username, email, password_hash FROM users WHERE username=?", (username,))
        row = c.fetchone()
    if row and check_password_hash(row[3], password):
        user = User(*row)
        login_user(user)
        return jsonify({'message': 'Login successful', 'username': user.username})
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out'})

@app.route('/api/user', methods=['GET'])
@login_required
def get_user():
    return jsonify({'username': current_user.username, 'email': current_user.email})

@app.route('/api/favorite', methods=['POST'])
@login_required
def add_favorite():
    data = request.json
    ticker = data.get('ticker')
    if not ticker:
        return jsonify({'error': 'Missing ticker'}), 400
    with sqlite3.connect(DATABASE_FILE) as conn:
        try:
            conn.execute("INSERT OR IGNORE INTO user_favorites (user_id, ticker) VALUES (?, ?)", (current_user.id, ticker.upper()))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    return jsonify({'message': 'Ticker favorited'})

@app.route('/api/favorite', methods=['DELETE'])
@login_required
def remove_favorite():
    data = request.json
    ticker = data.get('ticker')
    if not ticker:
        return jsonify({'error': 'Missing ticker'}), 400
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("DELETE FROM user_favorites WHERE user_id=? AND ticker=?", (current_user.id, ticker.upper()))
    return jsonify({'message': 'Ticker unfavorited'})

@app.route('/api/favorites', methods=['GET'])
@login_required
def get_favorites():
    with sqlite3.connect(DATABASE_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT ticker FROM user_favorites WHERE user_id=?", (current_user.id,))
        tickers = [row[0] for row in c.fetchall()]
    return jsonify({'favorites': tickers})

@app.route('/api/watchlist', methods=['GET'])
@login_required
def get_watchlist():
    with sqlite3.connect(DATABASE_FILE) as conn:
        c = conn.cursor()
        c.execute("SELECT ticker FROM user_watchlist WHERE user_id=?", (current_user.id,))
        tickers = [row[0] for row in c.fetchall()]
    return jsonify({'watchlist': tickers})

@app.route('/api/watchlist/add', methods=['POST'])
@login_required
def add_watchlist():
    data = request.json
    ticker = data.get('ticker')
    if not ticker:
        return jsonify({'error': 'Missing ticker'}), 400
    with sqlite3.connect(DATABASE_FILE) as conn:
        try:
            conn.execute("INSERT OR IGNORE INTO user_watchlist (user_id, ticker) VALUES (?, ?)", (current_user.id, ticker.upper()))
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        # Return updated watchlist
        c = conn.cursor()
        c.execute("SELECT ticker FROM user_watchlist WHERE user_id=?", (current_user.id,))
        tickers = [row[0] for row in c.fetchall()]
    return jsonify({'success': True, 'watchlist': tickers})

@app.route('/api/watchlist/remove', methods=['POST'])
@login_required
def remove_watchlist():
    data = request.json
    ticker = data.get('ticker')
    if not ticker:
        return jsonify({'error': 'Missing ticker'}), 400
    with sqlite3.connect(DATABASE_FILE) as conn:
        conn.execute("DELETE FROM user_watchlist WHERE user_id=? AND ticker=?", (current_user.id, ticker.upper()))
        # Return updated watchlist
        c = conn.cursor()
        c.execute("SELECT ticker FROM user_watchlist WHERE user_id=?", (current_user.id,))
        tickers = [row[0] for row in c.fetchall()]
    return jsonify({'success': True, 'watchlist': tickers})

# Serve index.html at root
@app.route('/')
def serve_index():
    return send_from_directory(app.static_folder, 'index.html')

# Serve other static files (JS, CSS, etc.)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)


# This part allows you to run the Flask app directly
if __name__ == '__main__':
    init_db() # Initialize the database when the app starts
    app.run(host='0.0.0.0', debug=True, port=5001)
