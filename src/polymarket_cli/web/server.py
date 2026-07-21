"""A small FastAPI app that serves a browser demo for the Polymarket CLI.

It reuses the same public-API clients the CLI uses, so the demo shows live
market data with no API key. Run it with `polymarket serve` (requires the
`web` extra: `pip install -e ".[web]"`).
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from polymarket_cli.models import Event
from polymarket_cli.api.gamma import (
    fetch_top_events,
    search_events,
    fetch_event_by_slug,
)

STATIC_DIR = Path(__file__).parent / "static"

app = FastAPI(title="Polymarket CLI — Web Demo", docs_url=None, redoc_url=None)


def _event_to_dict(event: Event, max_outcomes: int = 6) -> dict:
    """Flatten an event into the compact shape the front-end renders."""
    outcomes = [o for m in event.markets for o in m.outcomes]
    outcomes.sort(key=lambda o: o.price, reverse=True)
    return {
        "slug": event.slug,
        "title": event.title,
        "volume": event.volume,
        "volume_24hr": event.volume_24hr,
        "liquidity": event.liquidity,
        "end_date": event.end_date,
        "outcomes": [
            {"name": o.name, "price": o.price} for o in outcomes[:max_outcomes]
        ],
        "outcome_count": len(outcomes),
    }


@app.get("/api/dashboard")
async def api_dashboard(limit: int = 12, sort: str = "volume_24hr"):
    limit = max(1, min(limit, 50))
    events = await fetch_top_events(limit=limit, sort=sort)
    return [_event_to_dict(e) for e in events]


@app.get("/api/search")
async def api_search(q: str, limit: int = 12):
    q = q.strip()
    if not q:
        return []
    limit = max(1, min(limit, 50))
    events = await search_events(q, limit=limit)
    return [_event_to_dict(e) for e in events]


@app.get("/api/event/{slug}")
async def api_event(slug: str):
    event = await fetch_event_by_slug(slug)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return {
        "slug": event.slug,
        "title": event.title,
        "volume": event.volume,
        "volume_24hr": event.volume_24hr,
        "liquidity": event.liquidity,
        "end_date": event.end_date,
        "markets": [
            {
                "question": m.question,
                "outcomes": [
                    {"name": o.name, "price": o.price} for o in m.outcomes
                ],
            }
            for m in event.markets
        ],
    }


@app.get("/")
async def index():
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")
