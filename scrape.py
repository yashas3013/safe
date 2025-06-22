import feedparser
from datetime import datetime, timedelta
import requests
import json

# Ollama endpoint
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:latest"  # Replace with your model name

def query_ollama(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(OLLAMA_URL, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        result = response.json()
        return result.get("response", "").strip()
    else:
        print("❌ Ollama error:", response.text)
        return "Unknown"

def classify_with_ollama(title, location):
    prompt = f"""
You are a news danger classification assistant.
Given the following news headline from {location}, classify the danger level as one of:
- SAFE
- WARNING
- DANGER

Title: "{title}"

Just return only one word: SAFE, WARNING or DANGER.
"""
    return query_ollama(prompt)

def fetch_recent_news_by_location(location, days=2):
    query = location.replace(' ', '+')
    url = f'https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en'

    feed = feedparser.parse(url)

    print(f"\n📰 Top headlines for location: {location} (last {days} days)\n{'-'*50}")
    
    now = datetime.utcnow()
    cutoff = now - timedelta(days=days)
    
    for entry in feed.entries:
        if hasattr(entry, 'published_parsed'):
            published = datetime(*entry.published_parsed[:6])
            if published < cutoff:
                continue  # Skip older articles

            danger_level = classify_with_ollama(entry.title, location)
            print(f"[{danger_level}] {entry.title}")
            print(f"   🔗 {entry.link}")
            print(f"   🗓️ Published: {published}\n")
        else:
            print(f"⚠️ Skipping article (missing published date): {entry.title}")

# Example usage
fetch_recent_news_by_location("Vellore", days=20)

