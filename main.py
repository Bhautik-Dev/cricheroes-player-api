
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import requests
import re

app = FastAPI(title="CricHeroes Player API")

ALLOWED_HOSTS = {
    "chshare.link",
    "www.chshare.link",
    "cricheroes.com",
    "www.cricheroes.com",
}

class PlayerRequest(BaseModel):
    url: HttpUrl


@app.get("/")
def home():
    return {
        "status": "online",
        "service": "CricHeroes Player API"
    }


@app.post("/player")
def get_player(request: PlayerRequest):
    url = str(request.url)
    parsed = urlparse(url)

    if parsed.hostname not in ALLOWED_HOSTS:
        raise HTTPException(400, "Unsupported player URL")

    # Support both direct profile URLs and share URLs
    match = re.search(
        r"/player-profile/(\d+)|/player/([A-Za-z0-9]+)",
        parsed.path
    )

    if not match:
        raise HTTPException(400, "Invalid player URL")

    player_id = match.group(1) or match.group(2)

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=25,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            502, f"Could not access player profile: {exc}"
        )

    if urlparse(response.url).hostname not in ALLOWED_HOSTS:
        raise HTTPException(502, "Unexpected redirect host")

    soup = BeautifulSoup(response.text, "html.parser")
    page_text = " ".join(soup.stripped_strings)

    # Try to read statistics from the page text
    patterns = {
        "total_runs": r"(\d[\d,]*)\s*Runs\b",
        "total_wickets": r"(\d[\d,]*)\s*Wickets?\b",
        "matches": r"(\d[\d,]*)\s*Matches\b",
        "strike_rate": r"([\d.]+)\s*SR\b",
        "bowling_economy": r"([\d.]+)\s*Economy\b",
        "highest_score": r"(\d+)\s*(?:HS|Highest Score)\b",
        "fifties": r"(\d+)\s*50s\b",
        "hundreds": r"(\d+)\s*100s\b",
    }

    stats = {}
    for field, pattern in patterns.items():
        found = re.search(pattern, page_text, re.IGNORECASE)
        stats[field] = (
            found.group(1).replace(",", "")
            if found else None
        )

    title = soup.title.get_text(" ", strip=True) if soup.title else None
    player_name = title.split("|")[0].strip() if title else None

    stats["player_name"] = player_name

    return {
        "status": "success" if any(
            value is not None for value in stats.values()
        ) else "page_unreadable",
        "player_id": player_id,
        "player_url": url,
        "resolved_url": response.url,
        **stats,
    }
