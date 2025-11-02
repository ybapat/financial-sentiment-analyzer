# Bull AI - Reddit Sentiment Analyzer

**A full-stack, AI-powered web application that scrapes and analyzes real-time financial sentiment from Reddit to provide actionable insights on stocks and cryptocurrencies.**

### 🚀 Live Demo

**You can access the live, deployed application here:**

[**bull-ai.netlify.app**](https://bull-ai.netlify.app)

This project leverages a custom-trained NLP model to process thousands of comments from high-traffic subreddits, identifying trending tickers and classifying market sentiment as BUY, SELL, or HOLD. The application features a dynamic frontend with user authentication, personalized watchlists, and historical sentiment charting.

### Key Features

* **Real-Time Sentiment Analysis:** Scrapes Reddit in real-time to analyze the latest market chatter.
* **Custom Machine Learning Model:** Utilizes a custom-trained Logistic Regression model for domain-specific sentiment classification.
* **User Authentication:** Full registration and login system for a personalized user experience.
* **Personalized Watchlist:** Logged-in users can create and manage a personal watchlist of tickers they want to track.
* **Historical Data & Charting:** Stores analysis results in a database and visualizes 7-day sentiment trends with interactive charts.
* **Dynamic Data Pages:** Dedicated pages for "Trending," "Biggest Movers," and "Most Improved" tickers, powered by complex backend queries.
* **RESTful API Backend:** A robust Flask backend serves all data through a well-defined API.

### Tech Stack

| Category | Technology |
| :--- | :--- |
| **Frontend** | `HTML5`, `CSS3`, `JavaScript`, `Tailwind CSS`, `Chart.js` |
| **Backend** | `Python`, `Flask`, `PRAW (Python Reddit API Wrapper)` |
| **ML/NLP** | `Scikit-learn`, `Pandas`, `NLTK` |
| **Database** | `SQLite` (for local development), `PostgreSQL` (for production) |
| **Deployment** | `Docker`, `Render` (for backend & database), `Netlify` (for frontend) |

### Local Setup and Installation

To run this project on your local machine, follow these steps:

**Prerequisites:**

* Python 3.9+
* Conda or another virtual environment manager
* Node.js (for frontend development, optional)

**1. Clone the repository:**

```bash
git clone [https://github.com/YOUR_USERNAME/bull-ai-sentiment.git](https://github.com/YOUR_USERNAME/bull-ai-sentiment.git)
cd bull-ai-sentiment

# Navigate to the backend folder
cd backend

# Create and activate a Conda environment
conda create --name bullai-env python=3.9
conda activate bullai-env

# Install required libraries
pip install -r requirements.txt

# Create a .env file in the root directory and add your keys
# SECRET_KEY='your_super_secret_key'
# CLIENT_ID='your_reddit_client_id'
# CLIENT_SECRET='your_reddit_client_secret'
# USER_AGENT='BullAI Scraper v1.0 by u/your_username'

# Run the Flask server
python app.py

# Open a new terminal and navigate to the frontend folder
cd frontend

# (Recommended) Use a simple server to run the frontend
# If you have VS Code, the "Live Server" extension is a great choice.
# Alternatively, use Python's built-in server:
python -m http.server

The frontend will be accessible at http://localhost:8000

| **Method** | **Endpoint** | **Description** |
| :--- | :--- | :--- |
| `POST` | `/api/register`         | Registers a new user.                                   |
| `POST` | `/api/login`            | Logs in a user.                                         |
| `POST` | `/api/logout`           | Logs out the current user.                              |
| `GET`  | `/api/user`             | Checks the current user's login status.                 |
| `GET`  | `/api/trending`         | Gets the top 20 most mentioned tickers in the last 24h. |
| `GET`  | `/api/movers`           | Gets tickers with the biggest sentiment change (24h).   |
| `GET`  | `/api/improved`         | Gets tickers that have improved to a "BUY" status.      |
| `GET`  | `/api/history/<ticker>` | Gets the 7-day sentiment history for a specific ticker. |
| `POST` | `/api/watchlist/add`    | Adds a ticker to the user's watchlist.                  |
| `POST` | `/api/watchlist/remove` | Removes a ticker from the user's watchlist.             |
