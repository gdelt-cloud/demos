from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .fetch import CountryBlock, Dataset


def _color_for_goldstein(g: float | None) -> str:
    if g is None:
        return "#94a3b8"
    if g <= -7:
        return "#dc2626"
    if g <= -3:
        return "#ea580c"
    if g <= 0:
        return "#f59e0b"
    if g <= 3:
        return "#84cc16"
    return "#16a34a"


def _size_for_magnitude(m: float | None) -> int:
    base = m if m is not None else 0
    return max(8, min(22, int(8 + base * 1.3)))


def _prepare_event(event: dict[str, Any]) -> dict[str, Any]:
    geo = event.get("geo") or {}
    lat = geo.get("latitude")
    lon = geo.get("longitude")
    metrics = event.get("metrics") or {}
    return {
        "event_uid": event.get("event_uid"),
        "title": event.get("title"),
        "country": geo.get("country"),
        "latitude": lat,
        "longitude": lon,
        "event_date": event.get("event_date"),
        "event_family": event.get("event_family"),
        "category": event.get("category"),
        "magnitude": metrics.get("magnitude"),
        "goldstein": metrics.get("goldstein_scale"),
        "fatalities": metrics.get("fatalities"),
        "significance": metrics.get("significance") or 0,
        "marker_size": _size_for_magnitude(metrics.get("magnitude")),
        "marker_color": _color_for_goldstein(metrics.get("goldstein_scale")),
        "has_coords": lat is not None and lon is not None,
    }


def _prepare_story(story: dict[str, Any]) -> dict[str, Any]:
    metrics = story.get("metrics") or {}
    return {
        "id": story.get("id") or story.get("cluster_id"),
        "label": story.get("label") or story.get("title") or "(unlabeled story)",
        "cluster_date": story.get("cluster_date"),
        "article_count": metrics.get("article_count") or story.get("article_count") or 0,
        "significance": metrics.get("significance") or 0,
    }


def _prepare_country_panel(block: CountryBlock) -> dict[str, Any]:
    events = [_prepare_event(e) for e in block.events]
    stories = [_prepare_story(s) for s in block.stories]

    fatal_count = sum(1 for e in events if (e.get("fatalities") or 0) > 0)
    top_event = max(events, key=lambda e: e.get("significance") or 0, default=None)
    top_story = stories[0] if stories else None
    top_sig = (top_event.get("significance") if top_event else None) or 0

    return {
        "iso3": block.iso3,
        "label": block.label,
        "subtitle": block.subtitle,
        "event_count": len(events),
        "story_count": len(stories),
        "fatal_count": fatal_count,
        "top_sig": top_sig,
        "top_event": top_event,
        "top_story": top_story,
    }


# Static LME aluminum placeholder series — last 30 trading days, USD/tonne.
# Replace with a live macro_finance MCP call when wiring real data.
_LME_ALUMINUM_PLACEHOLDER: list[dict[str, Any]] = [
    {"date": "2026-04-08", "value": 2480},
    {"date": "2026-04-09", "value": 2492},
    {"date": "2026-04-10", "value": 2475},
    {"date": "2026-04-13", "value": 2510},
    {"date": "2026-04-14", "value": 2528},
    {"date": "2026-04-15", "value": 2541},
    {"date": "2026-04-16", "value": 2533},
    {"date": "2026-04-17", "value": 2549},
    {"date": "2026-04-20", "value": 2565},
    {"date": "2026-04-21", "value": 2572},
    {"date": "2026-04-22", "value": 2588},
    {"date": "2026-04-23", "value": 2595},
    {"date": "2026-04-24", "value": 2582},
    {"date": "2026-04-27", "value": 2603},
    {"date": "2026-04-28", "value": 2617},
    {"date": "2026-04-29", "value": 2625},
    {"date": "2026-04-30", "value": 2618},
    {"date": "2026-05-01", "value": 2640},
    {"date": "2026-05-04", "value": 2659},
    {"date": "2026-05-05", "value": 2671},
    {"date": "2026-05-06", "value": 2680},
    {"date": "2026-05-07", "value": 2672},
    {"date": "2026-05-08", "value": 2695},
    {"date": "2026-05-11", "value": 2712},
    {"date": "2026-05-12", "value": 2728},
    {"date": "2026-05-13", "value": 2735},
    {"date": "2026-05-14", "value": 2741},
    {"date": "2026-05-15", "value": 2755},
    {"date": "2026-05-18", "value": 2768},
    {"date": "2026-05-19", "value": 2779},
    {"date": "2026-05-20", "value": 2785},
    {"date": "2026-05-21", "value": 2794},
]


def _sparkline_path(points: list[dict[str, Any]], width: int = 280, height: int = 60) -> dict[str, Any]:
    if len(points) < 2:
        return {"path": "", "first": 0, "last": 0, "delta_pct": 0.0, "count": len(points)}
    values = [p["value"] for p in points]
    vmin, vmax = min(values), max(values)
    rng = (vmax - vmin) or 1
    segs: list[str] = []
    for i, p in enumerate(points):
        x = (i / (len(points) - 1)) * width
        y = height - ((p["value"] - vmin) / rng) * height
        segs.append(f"{'M' if i == 0 else 'L'}{x:.1f},{y:.1f}")
    first = values[0]
    last = values[-1]
    delta_pct = ((last - first) / first) * 100 if first else 0.0
    return {
        "path": " ".join(segs),
        "first": first,
        "last": last,
        "delta_pct": delta_pct,
        "count": len(points),
        "width": width,
        "height": height,
    }


def render_dashboard(dataset: Dataset, output_dir: Path) -> Path:
    """Render a single static index.html from a Dataset. Returns the output path."""
    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent.parent.parent / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("index.html.j2")

    panels = [_prepare_country_panel(b) for b in dataset.per_country]

    # Aggregated event + story rows across all three countries.
    all_event_rows = [_prepare_event(e) for e in dataset.all_events]
    all_story_rows = [_prepare_story(s) for s in dataset.all_stories]

    # "What changed this week" — top events across all three by significance.
    top_events = sorted(all_event_rows, key=lambda e: e.get("significance") or 0, reverse=True)[:12]

    # Stat tile totals.
    total_events = sum(p["event_count"] for p in panels)
    total_stories = sum(p["story_count"] for p in panels)
    total_fatal = sum(p["fatal_count"] for p in panels)

    map_payload = {
        "events": [e for e in all_event_rows if e["has_coords"]],
    }

    sparkline = _sparkline_path(_LME_ALUMINUM_PLACEHOLDER)

    html = template.render(
        start_date=dataset.start_date,
        end_date=dataset.end_date,
        panels=panels,
        total_events=total_events,
        total_stories=total_stories,
        total_fatal=total_fatal,
        country_count=len(panels),
        top_events=top_events,
        map_payload_json=json.dumps(map_payload),
        sparkline=sparkline,
        lme_label="LME Aluminum · 3M spot",
        lme_unit="USD/t",
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path
