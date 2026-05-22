from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .fetch import Dataset


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


def _prepare_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        geo = event.get("geo") or {}
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        metrics = event.get("metrics") or {}
        rows.append(
            {
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
        )
    return rows


def _prepare_stories(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for story in stories:
        metrics = story.get("metrics") or {}
        rows.append(
            {
                "id": story.get("id") or story.get("cluster_id"),
                "label": story.get("label") or story.get("title") or "(unlabeled story)",
                "cluster_date": story.get("cluster_date"),
                "article_count": metrics.get("article_count") or story.get("article_count") or 0,
                "significance": metrics.get("significance") or 0,
            }
        )
    return rows


def _prepare_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ent in entities:
        metrics = ent.get("metrics") or {}
        rows.append(
            {
                "id": ent.get("id"),
                "name": ent.get("name"),
                "type": (ent.get("type") or "").lower(),
                "event_count": metrics.get("event_count") or 0,
                "story_count": metrics.get("story_count") or 0,
            }
        )
    return rows


def _prepare_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten V2 energy asset cards for the template.

    V2 /api/v2/energy/assets returns nested shapes — geo.lat / geo.lon for
    coordinates and capacity.mw for capacity, not flat top-level fields.
    """
    rows: list[dict[str, Any]] = []
    for asset in assets:
        geo = asset.get("geo") or {}
        capacity = asset.get("capacity") or {}
        lat = geo.get("lat")
        lon = geo.get("lon")
        if lat is None or lon is None:
            continue
        rows.append(
            {
                "id": asset.get("id") or asset.get("gem_id") or asset.get("name"),
                "name": asset.get("name"),
                "latitude": lat,
                "longitude": lon,
                "capacity_mw": capacity.get("mw"),
                "tracker": asset.get("tracker"),
            }
        )
    return rows


def _format_capacity(total_mw: float) -> str:
    if total_mw > 1000:
        return f"{total_mw / 1000:.1f}k"
    return str(int(round(total_mw)))


def render_dashboard(dataset: Dataset, output_dir: Path) -> Path:
    """Render a single static index.html from a Dataset. Returns the output path."""
    env = Environment(
        loader=FileSystemLoader(str(Path(__file__).parent.parent.parent / "templates")),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("index.html.j2")

    events_rows = _prepare_events(dataset.events)
    stories_rows = _prepare_stories(dataset.stories)
    entities_rows = _prepare_entities(dataset.entities)
    assets_rows = _prepare_assets(dataset.assets)

    top_events = sorted(events_rows, key=lambda e: e.get("significance") or 0, reverse=True)[:15]
    top_stories = sorted(stories_rows, key=lambda s: s.get("article_count") or 0, reverse=True)[:8]

    fatal_events = [e for e in events_rows if (e.get("fatalities") or 0) > 0]
    total_fatalities = sum((e.get("fatalities") or 0) for e in fatal_events)

    # Hormuz-specific: sum capacity_mw across assets in the Persian Gulf bbox
    total_capacity_mw = sum((a.get("capacity_mw") or 0) for a in assets_rows)
    total_capacity_label = _format_capacity(total_capacity_mw)

    map_payload = {
        "events": [e for e in events_rows if e["has_coords"]],
        "assets": assets_rows,
    }

    html = template.render(
        start_date=dataset.start_date,
        end_date=dataset.end_date,
        events_count=len(events_rows),
        stories_count=len(stories_rows),
        entities_count=len(entities_rows),
        assets_count=len(assets_rows),
        fatal_count=len(fatal_events),
        total_fatalities=total_fatalities,
        total_capacity_mw=total_capacity_mw,
        total_capacity_label=total_capacity_label,
        top_events=top_events,
        top_stories=top_stories,
        entities=entities_rows[:12],
        map_payload_json=json.dumps(map_payload),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path
