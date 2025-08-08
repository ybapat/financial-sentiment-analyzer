# backend/app.py

import praw
import joblib
import pandas as pd
import config # Your API keys
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import datetime
import os

# --- 1. LOAD THE TRAINED MODEL AND VECTORIZER ---
print("Loading model and vectorizer...")
model = joblib.load('backend/sentiment_model.pkl')
vectorizer = joblib.load('backend/tfidf_vectorizer.pkl')
print("Model and vectorizer loaded successfully.")

# Import the text cleaning function from your other script
# Corrected the filename from sentiment_analysis to sentiment_analyzer
from sentiment_analysis import clean_text

# --- DATABASE SETUP ---
DATABASE_FILE = 'backend/sentiment_history.db'

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
CORS(app) # This is important to allow your frontend to make requests to this backend

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
