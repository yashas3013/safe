from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime, timedelta
import feedparser
import requests
import json
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ✅ Allow CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "deepseek-r1:8b"
# OLLAMA_MODEL = "deepseek-coder:latest"
class LocationQuery(BaseModel):
    location: str
    days: int = 2

def query_ollama(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(OLLAMA_URL, headers=headers, data=json.dumps(payload))
    if response.status_code == 200:
        return response.json().get("response", "").strip()
    else:
        return "Unknown"
def classify_with_ollama(title, location):
    prompt = f"""
You are a news classifier assistant.

Given a news headline from {location}, do two things:

1. **Classify** it into one of the following categories if it is repeated then return Nan:
   - sports
   - weather
   - crime
   - natural disaster
   - politics
   - war
   - construction 

2. **Assign a threat level** based on the category if repeated return Nan:
   - For crime, war, natural disaster, weather: use LOW, MEDIUM, or HIGH
   - For sports and politics: return NaN (no threat)

Return the result in the following format exactly:

Category: <category>
Threat: <LOW / MEDIUM / HIGH / NaN>

Headline: "{title}"
"""

    response =  query_ollama(prompt)
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
    count = 0
    for entry in feed.entries:
        if hasattr(entry, 'published_parsed'):
            published = datetime(*entry.published_parsed[:6])
            if published < cutoff:
                continue

            category, threat = classify_with_ollama(entry.title, query.location)
            if (category.lower()=="nan"):
                continue
            results.append({
                "title": entry.title,
                "link": entry.link,
                "published": published.isoformat(),
                "category": category,
                "threat": threat
            })
            count +=1
            if(count>5):
                break

    return results
