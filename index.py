from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import json
import os
from datetime import datetime, timedelta

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

# Free news API
NEWS_API_URL = "https://newsdata.io/api/1/news?apikey=YOUR_FREE_API_KEY&q="

# Load cache if exists
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

@app.get("/news/{topic}")
def get_news(topic: str):
    cache = load_cache()
    if cache:
        return {"news": cache}
    
    response = requests.get(NEWS_API_URL + topic)
    data = response.json()
    articles = [{
        "title": article["title"],
        "summary": article.get("description", "No description available."),
        "image": article.get("image_url", ""),
        "source": article["source_url"]
    } for article in data.get("results", [])]
    
    save_cache(articles)
    return {"news": articles}

# Serve frontend
@app.get("/")
def serve_frontend():
    return {"message": "Backend is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
