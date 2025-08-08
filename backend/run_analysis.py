import praw
import config
import pandas as pd
import os
import time
import sqlite3
import json
import joblib
from sentiment_analysis import clean_text

DB_PATH = 'backend/sentiment_history.db'
MODEL_PATH = 'backend/sentiment_model.pkl'
VECTORIZER_PATH = 'backend/tfidf_vectorizer.pkl'

# Load tickers
def load_tickers_from_csv(filename):
    try:
        if os.path.exists(filename):
            df = pd.read_csv(filename)
        elif os.path.exists(os.path.join('backend', filename)):
            df = pd.read_csv(os.path.join('backend', filename))
        else:
            print(f"Error: The file {filename} was not found.")
            return set()
        tickers = set(df['Symbol'].unique())
        return tickers
    except Exception as e:
        print(f"Error loading tickers: {e}")
        return set()

# Add extra tickers
tickers = load_tickers_from_csv('sp500_companies.csv')
extra_tickers = {"GME", "AMC", "BTC", "ETH", "SOL", "DOGE", "CRCL", "XRP", "SUI"}
tickers.update(extra_tickers)

# Load model and vectorizer
model = joblib.load(MODEL_PATH)
vectorizer = joblib.load(VECTORIZER_PATH)

# Reddit API setup
reddit = praw.Reddit(
    client_id=config.CLIENT_ID,
    client_secret=config.CLIENT_SECRET,
    user_agent=config.USER_AGENT,
)

subreddit_names = ["stocks", "stockmarket", "investing", "wallstreetbets",
                  "cryptocurrency", "ethereum"]

one_hour_ago = time.time() - 3600
stock_data = {}

stopwords = {
    "A", "I", "IT", "AND", "THE", "TO", "OF", "IN", "ON", "FOR", "IS", "AT", "BY", "AN", "OR", "AS", "BE", "ARE", "WITH", "FROM", "THIS", "THAT", "BUT", "NOT", "SO", "DO", "IF", "NO", "YES", "ALL", "ANY", "CAN", "WAS", "HAS", "HAVE", "WILL", "JUST", "ABOUT", "OUT", "UP", "DOWN", "OVER", "UNDER", "MORE", "LESS", "THAN", "THEN", "NOW", "ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "TEN", "WELL", "DAY"
}

for subreddit_name in subreddit_names:
    print(f"Processing subreddit: {subreddit_name}")
    subreddit = reddit.subreddit(subreddit_name)
    for post in subreddit.new(limit=50):
        post.comments.replace_more(limit=0)
        for comment in post.comments.list():
            comment_text = comment.body
            words = comment_text.upper().split()
            for word in words:
                cleaned_word = word.strip('.,?!-$')
                if cleaned_word in tickers and cleaned_word not in stopwords:
                    if cleaned_word not in stock_data:
                        stock_data[cleaned_word] = {
                            "mention_count": 0,
                            "comments": []
                        }
                    stock_data[cleaned_word]["mention_count"] += 1
                    stock_data[cleaned_word]["comments"].append(comment_text)

# Sentiment analysis and DB save
def save_to_db(data, db_path):
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS ticker_mentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT,
            mention_count INTEGER,
            comments TEXT,
            sentiment_score REAL,
            sentiment_label TEXT,
            timestamp INTEGER
        )
    """)
    now = int(time.time())
    for ticker, info in data.items():
        comments = info["comments"]
        if not comments:
            continue
        cleaned_comments = [clean_text(c) for c in comments]
        X_new = vectorizer.transform(cleaned_comments)
        probabilities = model.predict_proba(X_new)
        positive_probabilities = probabilities[:, 1]
        sentiment_score_raw = float(positive_probabilities.mean())
        # Normalize sentiment score: 0.55 -> 0, 0.8 -> 1
        if sentiment_score_raw >= 0.8:
            sentiment_score = 1.0
        elif sentiment_score_raw <= 0.55:
            sentiment_score = 0.0
        else:
            sentiment_score = (sentiment_score_raw - 0.55) / (0.8 - 0.55)
        sentiment_score = max(0.0, min(1.0, sentiment_score))  # Clamp to [0,1]
        # Map min/max to .03/.97
        if sentiment_score == 0.0:
            sentiment_score = 0.03
        elif sentiment_score == 1.0:
            sentiment_score = 0.97
        if sentiment_score > 0.6:
            sentiment_label = "BUY"
            box_color = "linear-gradient(90deg, #a21caf 0%, #43ff7b 100%)"  # half purple, half bright green
        elif sentiment_score < 0.3:
            sentiment_label = "SELL"
            box_color = "linear-gradient(90deg, #a21caf 0%, #ff2e2e 100%)"  # half purple, half bright red
        else:
            sentiment_label = "HOLD"
            box_color = "linear-gradient(90deg, #a21caf 0%, #ffe600 100%)"  # half purple, half bright yellow
        c.execute("""
            INSERT INTO ticker_mentions (ticker, mention_count, comments, sentiment_score, sentiment_label, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ticker, info["mention_count"], json.dumps(comments), sentiment_score, sentiment_label, now))
    conn.commit()
    conn.close()
    print(f"Saved tickers to DB.")

save_to_db(stock_data, DB_PATH)
print("Analysis complete and saved.")
