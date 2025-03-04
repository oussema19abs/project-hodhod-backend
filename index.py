from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()  # Load API keys from .env file

app = FastAPI()

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store fetched news (expires after 24h)
CACHE_FILE = "news_cache.json"
EXPIRY_TIME = timedelta(hours=24)

# APIs
GNEWS_API = f"https://gnews.io/api/v4/search?token={os.getenv('GNEWS_API_KEY')}&q="
NEWSDATA_API = f"https://newsdata.io/api/1/news?apikey={os.getenv('NEWSDATA_API_KEY')}&q="
HACKER_NEWS_API = "https://hacker-news.firebaseio.com/v0/topstories.json"
LEXICA_API_URL = "https://lexica.art/api/v1/search"

# Load cached news if it exists and is valid
def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as file:
            data = json.load(file)
            if datetime.fromisoformat(data["timestamp"]) > datetime.utcnow() - EXPIRY_TIME:
                return data["news"]
    return None

# Save cache
def save_cache(news):
    with open(CACHE_FILE, "w") as file:
        json.dump({"timestamp": datetime.utcnow().isoformat(), "news": news}, file)

# Fetch news from multiple sources
def fetch_news(topic: str):
    news = []
    
    # Fetch from GNews
    try:
        res = requests.get(GNEWS_API + topic).json()
        news.extend([
            {"title": a["title"], "summary": a["description"], "source": a["url"]}
            for a in res.get("articles", [])
        ])
    except Exception as e:
        print(f"GNews Error: {e}")

    # Fetch from NewsData.io
    try:
        res = requests.get(NEWSDATA_API + topic).json()
        news.extend([
            {"title": a["title"], "summary": a["description"], "source": a["source_url"]}
            for a in res.get("results", [])
        ])
    except Exception as e:
        print(f"NewsData.io Error: {e}")

    # Fetch from Hacker News
    try:
        top_stories = requests.get(HACKER_NEWS_API).json()[:5]  # Get top 5
        for story_id in top_stories:
            story = requests.get(f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json").json()
            news.append({"title": story["title"], "summary": "Hacker News Article", "source": story.get("url", "")})
    except Exception as e:
        print(f"Hacker News Error: {e}")

    return news[:10]  # Limit to 10 articles

# Generate AI images for articles
def get_lexica_images(query, num_images=3):
    params = {"q": query}
    response = requests.get(LEXICA_API_URL, params=params)

    if response.status_code == 200:
        data = response.json()
        return [photo["src"] for photo in data.get("images", [])[:num_images]]
    
    return []

@app.get("/news/{topic}")
def get_news(topic: str):
    cache = load_cache()
    if cache:
        return {"news": cache}
    
    articles = fetch_news(topic)
    
    for article in articles:
        lexica_images = get_lexica_images(article["title"])
        article["lexica_images"] = lexica_images

    save_cache(articles)
    return {"news": articles}

@app.get("/")
def home():
    return {"message": "Backend is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
