
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl
from urllib.parse import urlparse
import re

app = FastAPI(
    title="CricHeroes Player API",
    version="1.0.0"
)


class PlayerRequest(BaseModel):
    url: HttpUrl


@app.get("/")
def home():
    return {
        "status": "online",
        "service": "CricHeroes Player API",
        "fields": [
            "player_name",
            "total_runs",
            "total_wickets",
            "strike_rate",
            "bowling_economy",
            "highest_score"
        ]
    }


@app.post("/player")
def get_player(request: PlayerRequest):
    url = str(request.url)
    parsed = urlparse(url)

    allowed_hosts = {
        "chshare.link",
        "www.chshare.link",
        "cricheroes.com",
        "www.cricheroes.com"
    }

    if parsed.hostname not in allowed_hosts:
        raise HTTPException(
            status_code=400,
            detail="Unsupported player URL"
        )

    match = re.search(
        r"/player/([A-Za-z0-9]+)",
        parsed.path
    )

    if not match:
        raise HTTPException(
            status_code=400,
            detail="Player ID not found in URL"
        )

    return {
        "status": "pending_integration",
        "player_id": match.group(1),
        "player_url": url,
        "player_name": None,
        "total_runs": None,
        "total_wickets": None,
        "strike_rate": None,
        "bowling_economy": None,
        "highest_score": None,
        "message": "Live CricHeroes data integration is not configured yet."
    }
