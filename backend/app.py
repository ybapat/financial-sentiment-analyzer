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
    print("Received API request to /api/analyze")

    # --- This is your scraper code, now inside a function ---
    stock_data = {}
    
    # Load tickers from CSV and add custom ones
    tickers = load_tickers_from_csv('backend/sp500_companies.csv')
    extra_tickers = {"GME", "AMC", "BTC", "ETH", "SOL", "DOGE", "XRP", "LTC", "SUI", "CRCL"}
    tickers.update(extra_tickers)

    # *** ADDED: Ticker Blacklist ***
    # This set contains common English words that are also valid tickers.
    # We will ignore these to reduce noise in our results.
    ticker_blacklist = {
        'A', 'I', 'IT', 'ON', 'SO', 'ARE', 'NOW', 'HAS', 'ALL', 'WELL', 'DAY', 
        'FOR', 'IS', 'OF', 'TO', 'BE', 'GO', 'OR', 'IN', 'AT', 'BY', 'DD', 'CEO', 'BRO', 'LOW', 'FAST',
        'HES'
    }

    print("Connecting to Reddit...")
    reddit = praw.Reddit(
        client_id=config.CLIENT_ID,
        client_secret=config.CLIENT_SECRET,
        user_agent=config.USER_AGENT,
    )

    # Scrape a wider range of subreddits
    subreddit_names = ["wallstreetbets", "stocks", "investing", "cryptocurrency", "StockMarket", "options"]
    for subreddit_name in subreddit_names:
        print(f"Scraping subreddit: {subreddit_name}")
        subreddit = reddit.subreddit(subreddit_name)
        # Reduce the number of posts for faster response and to avoid timeouts
        for post in subreddit.hot(limit=25):
            try:
                post.comments.replace_more(limit=0)
                for comment in post.comments.list():
                    comment_text = comment.body
                    # Simple check to avoid huge blocks of text
                    if len(comment_text) > 500:
                        continue
                    
                    words = comment_text.upper().split()
                    for word in words:
                        cleaned_word = word.strip('.,?!-$')
                        
                        # *** UPDATED LOGIC: Check against the blacklist ***
                        if cleaned_word in tickers and cleaned_word not in ticker_blacklist:
                            if cleaned_word not in stock_data:
                                stock_data[cleaned_word] = {"mention_count": 0, "comments": []}
                            stock_data[cleaned_word]["mention_count"] += 1
                            stock_data[cleaned_word]["comments"].append(comment_text)
            except Exception as e:
                print(f"Could not process post: {post.id}. Error: {e}")


    # --- 4. ANALYZE SENTIMENT FOR EACH STOCK (IMPROVED LOGIC) ---
    print("Analyzing sentiment of scraped comments...")
    analyzed_results = {}
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now()
    for ticker, data in stock_data.items():
        if not data["comments"]:
            continue
        cleaned_comments = [clean_text(comment) for comment in data["comments"]]
        X_new = vectorizer.transform(cleaned_comments)
        probabilities = model.predict_proba(X_new)
        positive_probabilities = probabilities[:, 1]
        sentiment_score = positive_probabilities.mean()

        # Save to database for historical tracking
        cursor.execute('''
            INSERT INTO sentiment_history (ticker, sentiment_score, mention_count, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (ticker, float(sentiment_score), int(data["mention_count"]), timestamp))

        # Determine final sentiment label based on the probability score
        if sentiment_score > 0.6:
            sentiment_label = "BUY"
        elif sentiment_score < 0.45: # Adjusted threshold for more realistic "SELL"
            sentiment_label = "SELL"
        else:
            sentiment_label = "HOLD"

        # Return ALL tickers for debugging/demo
        analyzed_results[ticker] = {
            "mentions": int(data["mention_count"]),
            "sentiment": sentiment_label,
            "score": float(round(sentiment_score, 2))
        }
    print("Returning results:", analyzed_results)
    conn.commit()
    conn.close()
    print("Analysis complete. Sending response.")
    # --- 5. RETURN THE FINAL JSON RESPONSE ---
    return jsonify(analyzed_results)

@app.route('/api/history/<ticker>', methods=['GET'])
def get_history(ticker):
    """Fetches the last 7 days of sentiment history for a given ticker."""
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    seven_days_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    cursor.execute('''
        SELECT timestamp, sentiment_score FROM sentiment_history
        WHERE ticker = ? AND timestamp >= ?
        ORDER BY timestamp ASC
    ''', (ticker.upper(), seven_days_ago))
    history = cursor.fetchall()
    conn.close()
    labels = []
    scores = []
    for row in history:
        ts = row[0]
        try:
            # Try parsing with microseconds
            dt = datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S.%f')
        except Exception:
            try:
                # Try parsing without microseconds
                dt = datetime.datetime.strptime(ts, '%Y-%m-%d %H:%M:%S')
            except Exception:
                # Fallback: just use the raw string
                dt = ts
        labels.append(dt.strftime('%b %d, %H:%M') if hasattr(dt, 'strftime') else str(dt))
        scores.append(row[1])
    formatted_history = {
        "labels": labels,
        "scores": scores
    }
    return jsonify(formatted_history)

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
