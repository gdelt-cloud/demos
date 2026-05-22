from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .fetch import Dataset


# ── CAMEO+ category visual identity (color + lucide-equivalent icon SVG path) ───
#
# Mirrors `nextjs_/components/demos/event-card.tsx` so the standalone Python
# build looks identical to the hosted Next.js demo.
CATEGORY_VISUAL: dict[str, tuple[str, str]] = {
    "POLITICAL": ("#2e8de0", "M3 21h18M5 21V8l7-5 7 5v13M9 9h.01M9 12h.01M9 15h.01M9 18h.01M15 9h.01M15 12h.01M15 15h.01M15 18h.01"),
    "ECONOMIC": ("#1f9466", "M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"),
    "CORPORATE": ("#7c44d9", "M6 22V4a2 2 0 0 1 2-2h8a2 2 0 0 1 2 2v18ZM6 12H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h2M18 9h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M10 6h4M10 10h4M10 14h4M10 18h4"),
    "TECHNOLOGY": ("#159dbf", "M4 17h2v-7H4M9 17h2V7H9M14 17h2v-4h-2M19 17h2V10h-2"),
    "INFRASTRUCTURE": ("#f08016", "M2 20h20M14 12v-2M14 6v-2M10 4h4l1 8H9zM4 12h6v8M14 12h6v8M8 16h2M16 16h2"),
    "HEALTH": ("#df3f3f", "M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.29 1.51 4.04 3 5.5l7 7Z"),
    "INFORMATION": ("#5b6df0", "m3 11 18-8-8 18-2-8z"),
    "ENVIRONMENT": ("#1fa744", "M11 20A7 7 0 0 1 4 13C4 8 11 2 11 2s7 6 7 11a7 7 0 0 1-7 7M11 20v-9"),
    "CRIME": ("#d61f4d", "M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10M8.5 13.5 11 16l4-4.5"),
    "DEMOGRAPHIC": ("#bc40c2", "M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"),
    "CONFLICT": ("#d61f4d", "M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5"),
}

FALLBACK_VISUAL: tuple[str, str] = ("#808080", "M22 12h-4l-3 9L9 3l-3 9H2")


def _category_visual(category: str | None, family: str | None) -> tuple[str, str]:
    key = (category or "").upper()
    if key in CATEGORY_VISUAL:
        return CATEGORY_VISUAL[key]
    if (family or "").lower() == "conflict":
        return CATEGORY_VISUAL["CONFLICT"]
    return FALLBACK_VISUAL


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


def _days_between(a: str, b: str) -> int:
    try:
        ad = datetime.strptime(a, "%Y-%m-%d")
        bd = datetime.strptime(b, "%Y-%m-%d")
        return (bd - ad).days
    except Exception:
        return 0


def _prepare_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for event in events:
        geo = event.get("geo") or {}
        lat = geo.get("latitude")
        lon = geo.get("longitude")
        metrics = event.get("metrics") or {}
        category = event.get("category")
        family = event.get("family") or event.get("event_family")
        subcategory = event.get("subcategory")
        accent, icon_d = _category_visual(category, family)
        rows.append(
            {
                "id": event.get("id") or event.get("event_uid"),
                "title": event.get("title"),
                "url": event.get("url"),
                "country": geo.get("country"),
                "latitude": lat,
                "longitude": lon,
                "event_date": event.get("event_date"),
                "family": family,
                "category": category,
                "subcategory": subcategory,
                "magnitude": metrics.get("magnitude"),
                "goldstein": metrics.get("goldstein_scale"),
                "propagation": metrics.get("propagation_potential"),
                "market_sensitivity": metrics.get("market_sensitivity"),
                "systemic": metrics.get("systemic_importance"),
                "fatalities": metrics.get("fatalities"),
                "significance": metrics.get("significance") or 0,
                "marker_size": _size_for_magnitude(metrics.get("magnitude")),
                "marker_color": _color_for_goldstein(metrics.get("goldstein_scale")),
                "category_color": accent,
                "category_icon_d": icon_d,
                "has_coords": lat is not None and lon is not None,
            }
        )
    return rows


def _prepare_timeline(
    events: list[dict[str, Any]], start_date: str, end_date: str
) -> list[dict[str, Any]]:
    total_days = max(1, _days_between(start_date, end_date))
    sorted_events = sorted(
        [e for e in events if e.get("event_date")],
        key=lambda e: e["event_date"],
    )
    out: list[dict[str, Any]] = []
    for i, e in enumerate(sorted_events):
        days = _days_between(start_date, e["event_date"])
        pct = max(0.0, min(100.0, (days / total_days) * 100.0))
        magnitude = float(e.get("magnitude") or 0)
        r = 8 + min(6.0, magnitude * 0.6)
        icon_px = round(r * 1.5 - 1)
        lane = (i % 4) - 1.5
        out.append(
            {
                "id": e.get("id"),
                "title": e.get("title"),
                "url": e.get("url"),
                "country": e.get("country"),
                "category": e.get("category"),
                "subcategory": e.get("subcategory"),
                "event_date": e.get("event_date"),
                "pct": round(pct, 2),
                "lane": lane,
                "r": round(r, 1),
                "icon_px": icon_px,
                "color": e.get("category_color"),
                "icon_d": e.get("category_icon_d"),
            }
        )
    return out


def _day_markers(start_date: str, end_date: str) -> list[dict[str, Any]]:
    total_days = max(1, _days_between(start_date, end_date))
    out: list[dict[str, Any]] = []
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    except Exception:
        return out
    for i in range(total_days + 1):
        d = start.fromordinal(start.toordinal() + i)
        out.append(
            {
                "date": d.strftime("%Y-%m-%d"),
                "pct": round((i / total_days) * 100, 2),
                "label": d.strftime("%b %-d"),
            }
        )
    return out


def _prepare_stories(stories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for story in stories:
        metrics = story.get("metrics") or {}
        geo = story.get("geo") or {}
        top_articles = story.get("top_articles") or []
        rows.append(
            {
                "id": story.get("id") or story.get("cluster_id"),
                "label": story.get("label") or story.get("title") or "(unlabeled story)",
                "url": story.get("url"),
                "cluster_date": story.get("cluster_date") or story.get("story_date"),
                "category": story.get("category"),
                "subcategory": story.get("subcategory"),
                "country": geo.get("country"),
                "image_url": story.get("image_url"),
                "source_domain": (top_articles[0].get("domain") if top_articles else None),
                "article_count": metrics.get("article_count") or story.get("article_count") or 0,
                "linked_event_count": metrics.get("linked_event_count") or 0,
                "significance": metrics.get("significance") or 0,
            }
        )
    return rows


def _prepare_entities(entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ent in entities:
        metrics = ent.get("metrics") or {}
        wiki = ent.get("wikipedia") or {}
        rows.append(
            {
                "id": ent.get("id"),
                "name": ent.get("name"),
                "type": (ent.get("type") or "").lower(),
                "wikipedia_url": ent.get("wikipedia_url") or wiki.get("page_url"),
                "image_url": ent.get("image_url") or ent.get("avatar_url") or wiki.get("thumbnail_url"),
                "article_count": metrics.get("article_count") or 0,
                "story_count": metrics.get("story_count") or 0,
                "event_count": metrics.get("event_count") or 0,
            }
        )
    return rows


def _scale_entities(entities: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "article_max": max((e.get("article_count") or 0) for e in entities) if entities else 1,
        "story_max": max((e.get("story_count") or 0) for e in entities) if entities else 1,
        "event_max": max((e.get("event_count") or 0) for e in entities) if entities else 1,
    }


def _prepare_assets(assets: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


def _sparkline_path(points: list[dict[str, Any]], width: int, height: int) -> str:
    if len(points) < 2:
        return ""
    values = [float(p["value"]) for p in points]
    lo, hi = min(values), max(values)
    rng = hi - lo or 1.0
    pad = 3
    usable_h = height - pad * 2
    step_x = (width - 4) / (len(values) - 1)
    coords = [
        (2 + i * step_x, pad + (1 - (v - lo) / rng) * usable_h) for i, v in enumerate(values)
    ]
    parts = [f"M {coords[0][0]:.1f} {coords[0][1]:.1f}"]
    for i in range(1, len(coords)):
        prev = coords[i - 1]
        cur = coords[i]
        mx = (prev[0] + cur[0]) / 2
        parts.append(f"Q {mx:.1f} {prev[1]:.1f} {cur[0]:.1f} {cur[1]:.1f}")
    return " ".join(parts)


def _macro_sparkline(label: str, unit: str, points: list[dict[str, Any]]) -> dict[str, Any] | None:
    if len(points) < 2:
        return None
    first = float(points[0]["value"])
    last = float(points[-1]["value"])
    delta = ((last - first) / first) * 100 if first != 0 else 0
    width, height = 200, 36
    return {
        "label": label,
        "unit": unit,
        "first": first,
        "last": last,
        "delta_pct": delta,
        "direction": "up" if delta > 0.1 else "down" if delta < -0.1 else "flat",
        "color": "#10b981" if delta > 0.1 else "#ef4444" if delta < -0.1 else "#3b82f6",
        "width": width,
        "height": height,
        "path_d": _sparkline_path(points, width, height),
        "first_date": points[0].get("date"),
        "last_date": points[-1].get("date"),
    }


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
    top_entities = entities_rows[:10]

    fatal_events = [e for e in events_rows if (e.get("fatalities") or 0) > 0]
    total_fatalities = sum((e.get("fatalities") or 0) for e in fatal_events)

    # Hormuz-specific: sum capacity_mw across assets in the Persian Gulf bbox
    total_capacity_mw = sum((a.get("capacity_mw") or 0) for a in assets_rows)
    total_capacity_label = _format_capacity(total_capacity_mw)

    timeline_events = _prepare_timeline(top_events, dataset.start_date, dataset.end_date)
    day_markers = _day_markers(dataset.start_date, dataset.end_date)

    # Brent + WTI sparklines — static snapshot so the standalone demo is
    # self-contained. The hosted Next.js demo pulls live values from the
    # GDELT Cloud MCP macro_finance proxy.
    brent_sparkline = _macro_sparkline(
        label="Brent Crude Oil",
        unit="USD/bbl",
        points=[
            {"date": "2026-03-22", "value": 80.1},
            {"date": "2026-04-01", "value": 82.3},
            {"date": "2026-04-15", "value": 84.7},
            {"date": "2026-04-30", "value": 86.5},
            {"date": "2026-05-10", "value": 88.0},
            {"date": "2026-05-20", "value": 89.4},
        ],
    )
    wti_sparkline = _macro_sparkline(
        label="WTI Crude Oil",
        unit="USD/bbl",
        points=[
            {"date": "2026-03-22", "value": 75.8},
            {"date": "2026-04-01", "value": 78.2},
            {"date": "2026-04-15", "value": 80.5},
            {"date": "2026-04-30", "value": 82.1},
            {"date": "2026-05-10", "value": 84.3},
            {"date": "2026-05-20", "value": 85.6},
        ],
    )

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
        timeline_events=timeline_events,
        day_markers=day_markers,
        top_events=top_events,
        top_stories=top_stories,
        entities=top_entities,
        entity_scale=_scale_entities(top_entities),
        macro_series=[s for s in [brent_sparkline, wti_sparkline] if s],
        map_payload_json=json.dumps(map_payload),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path
