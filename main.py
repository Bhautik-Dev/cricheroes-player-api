
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

FIELDS = [
    "player_name",
    "total_runs",
    "total_wickets",
    "strike_rate",
    "bowling_economy",
    "highest_score",
]


class PlayerRequest(BaseModel):
    url: HttpUrl


def valid_host(url):
    host = urlparse(url).hostname
    return host in ALLOWED_HOSTS


@app.get("/")
def home():
    return {
        "status": "online",
        "service": "CricHeroes Player API"
    }


@app.post("/player")
def get_player(request: PlayerRequest):
    url = str(request.url)

    if not valid_host(url):
        raise HTTPException(400, "Unsupported player URL")

    if not re.search(r"/player/([A-Za-z0-9]+)", urlparse(url).path):
        raise HTTPException(400, "Invalid player URL")

    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=20,
            allow_redirects=True,
        )
    except requests.RequestException:
        raise HTTPException(
            502, "Could not access the public profile"
        )

    if not valid_host(response.url):
        raise HTTPException(502, "Unexpected redirect host")

    soup = BeautifulSoup(response.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.get_text(" ", strip=True) if soup.title else None
    text = " ".join(soup.stripped_strings)

    patterns = {
        "total_runs": r"\b(\d[\d,]*)\s+Runs\b",
        "total_wickets": r"\b(\d[\d,]*)\s+Wickets\b",
        "strike_rate": r"\b([\d.]+)\s+SR\b",
        "bowling_economy": r"\b([\d.]+)\s+Economy\b",
        "highest_score": r"\b(\d+)\s+(?:HS|Highest Score)\b",
    }

    stats = {}
    for field, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        stats[field] = (
            match.group(1).replace(",", "")
            if match else None
        )

    name = None
    if soup.title:
        name = title.split("|")[0].strip()

    stats["player_name"] = name

    found = sum(value is not None for value in stats.values())

    return {
        "status": "success" if found else "page_unreadable",
        "player_id": re.search(
            r"/player/([A-Za-z0-9]+)",
            urlparse(url).path
        ).group(1),
        "player_url": url,
        "resolved_url": response.url,
        "http_status": response.status_code,
        **stats,
        "message": (
            "Some public HTML fields were detected."
            if found else
            "No supported statistics found in HTML. "
            "The page may require JavaScript or another "
            "authorized data source."
        )
    }
