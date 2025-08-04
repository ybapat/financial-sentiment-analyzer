import pandas as pd
import re
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score
import joblib # Used to save model


#Step 1: Data Cleaning
# This function will clean text data by:
# Removing special characters, converting to lowercase, tokenizing, removing stopwords, and stemming.

def clean_text(text):
    # Remove special characters and numbers
    text = re.sub(r'[^a-zA-Z\s]', '', text, re.I|re.A)

    #convert to lowercase
    text = text.lower()

    #tokenize text
    words = text.split()

    # Remove stopwords (common words like 'the', 'is', etc.)
    stop_words = set(stopwords.words('english'))
    words = [w for w in words if not w in stop_words]
    # Stemming (reducing words to their root form, e.g., 'running' -> 'run')
    stemmer = PorterStemmer()
    words = [stemmer.stem(w) for w in words]
    # Join words back into a single string
    return " ".join(words)


# Training a Sentiment Analysis Model

def train_model():
    #load dataset
    df = pd.read_csv('data.csv', encoding='latin-1', names=['text', 'sentiment'])

    # We only care about 'positive' and 'negative' for now
    df = df[df.sentiment.isin(['positive', 'negative'])]

    #apply cleaning function to the df
    df['cleaned_text'] = df['text'].apply(clean_text)

    #Convert positive and negative sentiments to binary values
    df['sentiment'] = df['sentiment'].map({'positive': 1, 'negative': 0})

    # --- Feature Extraction (TF-IDF) ---
    print("Vectorizing text data...")
    vectorizer = TfidfVectorizer(max_features=5000) # Use top 5000 features
    X = vectorizer.fit_transform(df['cleaned_text'])
    y = df['sentiment']

    # --- Splitting Data ---
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # --- Training the Logistic Regression Model ---
    print("Training the model...")
    model = LogisticRegression()
    model.fit(X_train, y_train)

    # --- Evaluating the Model ---
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Model Accuracy: {accuracy:.4f}")

    # --- 5. Saving the Model and Vectorizer ---
    # We save both the model and the vectorizer so we can use them later
    # on new, unseen data from our scraper.
    print("Saving model and vectorizer...")
    joblib.dump(model, 'sentiment_model.pkl')
    joblib.dump(vectorizer, 'tfidf_vectorizer.pkl')
    print("Training complete and model saved!")

# This part allows you to run the training directly from the terminal
if __name__ == '__main__':
    # You might need to download nltk data
    import nltk
    nltk.download('stopwords')
    train_model()







