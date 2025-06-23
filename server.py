from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
import feedparser
import requests
import json
import logging
from fastapi.middleware.cors import CORSMiddleware

# Enable logging
logging.basicConfig(filename="ollama_debug.log", level=logging.DEBUG)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:8b"
DEBUG = True

class LocationQuery(BaseModel):
    location: str
    days: int = 2

def query_ollama(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "max_tokens": 80,
        "temperature": 0.3,
        "top_p": 0.8,
        "stream": False,
        
    }

    if DEBUG:
        print("\n🧠 [PROMPT SENT TO OLLAMA]:")
        print(prompt)
        print("-" * 60)

    response = requests.post(OLLAMA_URL, headers=headers, data=json.dumps(payload))

    if response.status_code == 200:
        reply = response.json().get("response", "").strip()
        if DEBUG:
            print("🧠 [RESPONSE RECEIVED]:")
            print(reply)
            print("=" * 60)
        logging.debug(f"\nPROMPT:\n{prompt}\nRESPONSE:\n{reply}\n{'='*60}")
        return reply
    else:
        print("❌ Error from Ollama:", response.text)
        return "Unknown"

def filter_unique_titles(titles: list[str]) -> list[str]:
    id_map = {f"T{i+1}": title for i, title in enumerate(titles)}

    prompt = f"""
You are a news deduplication assistant.

Below is a list of news headlines. Some may be reworded versions of the same event. Your job is to identify which headlines refer to **unique events**.

Each title is labeled as T1, T2, ..., Tn.

Return ONLY the list of IDs that represent **distinct** events. If two or more titles are about the same incident (even if phrased differently), keep only one ID from that group.

Respond in this **strict format only**:

T1
T3
T4

### Headlines:
{chr(10).join([f"- {id}: {title}" for id, title in id_map.items()])}
"""

    response = query_ollama(prompt)
    unique_ids = [line.strip().lstrip("-").strip() for line in response.splitlines() if line.strip().startswith("T")]
    return [id_map[uid] for uid in unique_ids if uid in id_map]

def classify_with_ollama(title, location):
    prompt = f"""
You are a news classifier assistant.

Given a news headline from {location}, do the following:

1. Classify it into **one of**:
   - sports
   - weather
   - crime
   - natural disaster
   - politics
   - war
   - construction

2. Assign a threat level:
   - For crime, war, natural disaster, weather: LOW, MEDIUM, or HIGH
   - For sports and politics: NaN

Return this exact format:

Category: <category>  
Threat: <LOW / MEDIUM / HIGH / NaN>

Headline: "{title}"
"""
    response = query_ollama(prompt)
    category, threat = "unknown", "NaN"
    for line in response.splitlines():
        if line.lower().startswith("category:"):
            category = line.split(":", 1)[1].strip().lower()
        if line.lower().startswith("threat:"):
            threat = line.split(":", 1)[1].strip().upper()
    return category, threat

@app.post("/analyze")
def analyze_location(query: LocationQuery):
    results = []
    url = f'https://news.google.com/rss/search?q={query.location.replace(" ", "+")}&hl=en-IN&gl=IN&ceid=IN:en'
    feed = feedparser.parse(url)

    now = datetime.utcnow()
    cutoff = now - timedelta(days=query.days)

    raw_titles = []
    entry_map = {}

    for entry in feed.entries:
        logging.debug(entry)
        if hasattr(entry, 'published_parsed'):
            published = datetime(*entry.published_parsed[:6])
            if published < cutoff:
                continue
            title = entry.title.strip()
            raw_titles.append(title)
            entry_map[title] = {
                "link": entry.link,
                "published": published.isoformat()
            }

    unique_titles = filter_unique_titles(raw_titles[:15])  # limit to top 5
    logging.debug(unique_titles)
    for title in unique_titles:
        category, threat = classify_with_ollama(title, query.location)
        if category == "nan":
            continue

        results.append({
            "title": title,
            "link": entry_map.get(title, {}).get("link", ""),
            "published": entry_map.get(title, {}).get("published", ""),
            "category": category,
            "threat": threat
        })

    return results
