import praw
import config
import pandas as pd
import os


# A dictionary to store aggregated data
# The key will be the stock ticker (e.g., "TSLA")
# The value will be another dictionary holding the mention count and a list of all comments
stock_data = {}

ticker_blacklist = {
    'A', 'I', 'IT', 'ON', 'SO', 'ARE', 'NOW', 'HAS', 'ALL', 'WELL', 'DAY',
    'FOR', 'IS', 'OF', 'TO', 'BE', 'GO', 'OR', 'IN', 'AT', 'BY', 'DD', 'CEO', 'BRO', 'LOW',
    'HES', 'AND', 'THE', 'AN', 'AS', 'BUT', 'NOT', 'NO', 'OUT', 'UP', 'DOWN', 'OFF', 'ONE', 'TWO', 'THREE', 'FOUR', 'FIVE', 'SIX', 'SEVEN', 'EIGHT', 'NINE', 'TEN', 'FROM', 'WITH', 'THAT', 'THIS', 'THEN', 'THAN', 'CAN', 'DO', 'IF', 'INTO', 'JUST', 'LIKE', 'MAKE', 'MORE', 'MOST', 'OVER', 'SEE', 'SOME', 'TAKE', 'TIME', 'VERY', 'WAY', 'WHO', 'WHY', 'YES', 'YOU', 'YOUR', 'YET', 'ALL', 'ANY', 'EACH', 'EVERY', 'FEW', 'MANY', 'MUCH', 'OTHER', 'OUR', 'SAME', 'SO', 'SUCH', 'THOSE', 'THESE', 'TOO', 'UNDER', 'UNTIL', 'WHILE', 'WHERE', 'WHICH', 'WHAT', 'WHEN', 'WHOM', 'WHOSE', 'WOULD', 'SHOULD', 'COULD', 'MIGHT', 'MUST', 'WILL', 'SHALL', 'MAY', 'DOES', 'DID', 'DONE', 'GET', 'GOT', 'GIVE', 'GIVEN', 'GOES', 'GOING', 'HAD', 'HAS', 'HAVE', 'HAVING', 'HE', 'HER', 'HIM', 'HIS', 'HOW', 'IT', 'ITS', 'LET', 'ME', 'MY', 'NO', 'NOT', 'OF', 'ON', 'ONCE', 'ONLY', 'OR', 'OUR', 'OUT', 'OVER', 'OWN', 'SHE', 'SO', 'SOME', 'SUCH', 'THAN', 'THAT', 'THE', 'THEIR', 'THEM', 'THEN', 'THERE', 'THESE', 'THEY', 'THIS', 'THOSE', 'THOUGH', 'THREE', 'THROUGH', 'THUS', 'TO', 'TOO', 'UNDER', 'UNTIL', 'UP', 'UPON', 'US', 'VERY', 'WAS', 'WE', 'WERE', 'WHAT', 'WHEN', 'WHERE', 'WHICH', 'WHILE', 'WHO', 'WHOM', 'WHY', 'WITH', 'WOULD', 'YES', 'YET', 'YOU', 'YOUR'
}

def load_tickers_from_csv(filename):
    """Loads stock tickers from a CSV file into a Python set. Tries both local and backend/ paths."""
    try:
        # Try the given filename first
        if os.path.exists(filename):
            df = pd.read_csv(filename)
        # Try backend/filename if not found
        elif os.path.exists(os.path.join('backend', filename)):
            df = pd.read_csv(os.path.join('backend', filename))
        else:
            print(f"Error: The file {filename} was not found in current or backend/ directory.")
            return set()
        tickers = set(df['Symbol'].unique())
        return tickers
    except FileNotFoundError:
        print(f"Error: The file {filename} was not found. Please make sure it's in the backend folder.")
        return set() # Return an empty set on error
    except KeyError:
        print(f"Error: The CSV file {filename} does not have a 'Symbol' column. Please check the file.")
        return set()
    

# Load the base tickers from the S&P 500 file and add extra tickers from crypto
tickers = load_tickers_from_csv('sp500_companies.csv')
extra_tickers = {"GME", "AMC", "BTC", "ETH", "SOL", "DOGE", "CRCL", "XRP", "SUI"}
tickers.update(extra_tickers)

reddit = praw.Reddit(
    client_id=config.CLIENT_ID,
    client_secret=config.CLIENT_SECRET,
    user_agent=config.USER_AGENT,
)

print("Successful connection.")

subreddit_names = ["stocks", "stockmarket", "investing", "wallstreetbets",
                  "cryptocurrency", "ethereum"]

for subreddit_name in subreddit_names:
    print(f"Processing subreddit: {subreddit_name}")
    subreddit = reddit.subreddit(subreddit_name)

    for post in subreddit.hot(limit=25):
        print("--- POST ---")
        print("Title:", post.title)

        # fetches all comments, avoiding "MoreComments" objects.
        post.comments.replace_more(limit=0)

        # loops through the top-level comments of the post
        print("  --- COMMENTS ---")
        for comment in post.comments.list():
            comment_text = comment.body
            words = comment_text.upper().split()

            for word in words:
                # Remove punctuation from the word
                cleaned_word = word.strip('.,?!-$')
                if cleaned_word in tickers and cleaned_word not in ticker_blacklist:
                    # This is a ticker we are tracking!

                    # If we've never seen this ticker before, add it to our dictionary
                    if cleaned_word not in stock_data:
                        stock_data[cleaned_word] = {
                            "mention_count": 0,
                            "comments": []
                        }

                    # Now, update the data for this ticker
                    stock_data[cleaned_word]["mention_count"] += 1
                    stock_data[cleaned_word]["comments"].append(comment_text)


