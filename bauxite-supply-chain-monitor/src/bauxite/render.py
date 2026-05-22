from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .fetch import CountryBlock, Dataset


# ── CAMEO+ category visual identity ────────────────────────────────────────────
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
        return (datetime.strptime(b, "%Y-%m-%d") - datetime.strptime(a, "%Y-%m-%d")).days
    except Exception:
        return 0


def _prepare_event(event: dict[str, Any]) -> dict[str, Any]:
    geo = event.get("geo") or {}
    lat = geo.get("latitude")
    lon = geo.get("longitude")
    metrics = event.get("metrics") or {}
    category = event.get("category")
    family = event.get("family") or event.get("event_family")
    subcategory = event.get("subcategory")
    accent, icon_d = _category_visual(category, family)
    return {
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
        "actors": event.get("actors") or [],
        "marker_size": _size_for_magnitude(metrics.get("magnitude")),
        "marker_color": _color_for_goldstein(metrics.get("goldstein_scale")),
        "category_color": accent,
        "category_icon_d": icon_d,
        "has_coords": lat is not None and lon is not None,
    }


def _prepare_story(story: dict[str, Any]) -> dict[str, Any]:
    metrics = story.get("metrics") or {}
    geo = story.get("geo") or {}
    top_articles = story.get("top_articles") or []
    return {
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


def _avg(values: list[float]) -> float | None:
    return (sum(values) / len(values)) if values else None


def _prepare_country_panel(block: CountryBlock) -> dict[str, Any]:
    events = [_prepare_event(e) for e in block.events]
    stories = [_prepare_story(s) for s in block.stories]

    fatal_count = sum(1 for e in events if (e.get("fatalities") or 0) > 0)
    top_event = max(events, key=lambda e: e.get("significance") or 0, default=None)
    # Top story: prefer ≥3 article clusters so a 1-article cluster doesn't get
    # the "headline story this week" treatment.
    qualified_stories = [s for s in stories if (s.get("article_count") or 0) >= 3]
    top_story = max(qualified_stories, key=lambda s: s.get("article_count") or 0, default=None)

    # CAMEO+ averages — show the avg metric over the week so panel viewers
    # see "what kind of risk" this country is showing right now.
    goldstein_vals = [e["goldstein"] for e in events if e.get("goldstein") is not None]
    mag_vals = [e["magnitude"] for e in events if e.get("magnitude") is not None]
    prop_vals = [e["propagation"] for e in events if e.get("propagation") is not None]
    mkt_vals = [e["market_sensitivity"] for e in events if e.get("market_sensitivity") is not None]
    sys_vals = [e["systemic"] for e in events if e.get("systemic") is not None]
    article_counts = [
        e.get("metrics", {}).get("article_count")
        if isinstance(e.get("metrics"), dict)
        else None
        for e in block.events
    ]
    article_total = sum(a or 0 for a in article_counts)

    avg_g = _avg(goldstein_vals)
    avg_mag = _avg(mag_vals)
    avg_prop = _avg(prop_vals)
    avg_mkt = _avg(mkt_vals)
    avg_sys = _avg(sys_vals)

    # Top actor — skip names that ARE the country itself ("Guinea" as top actor
    # in the Guinea panel is tautological).
    skip = {block.label.lower(), block.iso3.lower()}
    actor_tally: Counter[str] = Counter()
    for e in events:
        for a in e.get("actors") or []:
            name = (a.get("name") or "").strip()
            if not name or name.lower() in skip:
                continue
            actor_tally[name] += 1
    top_actor = actor_tally.most_common(1)[0][0] if actor_tally else None

    # Goldstein severity spectrum bar — position the marker from 0% (avg=-10)
    # to 100% (avg=+10). 50% = neutral.
    if avg_g is not None:
        spectrum_pct = max(0.0, min(100.0, (avg_g + 10) / 20 * 100))
    else:
        spectrum_pct = 50.0
    spectrum_label = (
        "conflict-leaning" if (avg_g or 0) < -1.5
        else "cooperative-leaning" if (avg_g or 0) > 1.5
        else "neutral"
    )

    return {
        "iso3": block.iso3,
        "label": block.label,
        "subtitle": block.subtitle,
        "event_count": len(events),
        "story_count": len(stories),
        "fatal_count": fatal_count,
        "article_count": article_total,
        "avg_goldstein": avg_g,
        "avg_magnitude": avg_mag,
        "avg_propagation": avg_prop,
        "avg_market_sensitivity": avg_mkt,
        "avg_systemic": avg_sys,
        "spectrum_pct": round(spectrum_pct, 1),
        "spectrum_label": spectrum_label,
        "top_actor": top_actor,
        "top_event": top_event,
        "top_story": top_story,
    }


def _prepare_timeline(events: list[dict[str, Any]], start_date: str, end_date: str) -> list[dict[str, Any]]:
    total_days = max(1, _days_between(start_date, end_date))
    sorted_events = sorted(
        [e for e in events if e.get("event_date")], key=lambda e: e["event_date"]
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
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d")
    except Exception:
        return []
    out: list[dict[str, Any]] = []
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


# Static LME aluminum placeholder series — last 30 trading days, USD/tonne.
_LME_ALUMINUM_PLACEHOLDER: list[dict[str, Any]] = [
    {"date": "2026-04-08", "value": 2480},
    {"date": "2026-04-15", "value": 2528},
    {"date": "2026-04-22", "value": 2588},
    {"date": "2026-04-29", "value": 2625},
    {"date": "2026-05-06", "value": 2680},
    {"date": "2026-05-13", "value": 2735},
    {"date": "2026-05-20", "value": 2785},
]


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

    panels = [_prepare_country_panel(b) for b in dataset.per_country]

    all_event_rows = [_prepare_event(e) for e in dataset.all_events]
    all_story_rows = [_prepare_story(s) for s in dataset.all_stories]

    top_events = sorted(all_event_rows, key=lambda e: e.get("significance") or 0, reverse=True)[:18]
    # Cross-country dedup'd top stories — same logic as the live demo. No
    # article-count floor at the panel level so commodity-search 1-2 article
    # clusters still surface.
    seen: set[str] = set()
    cross_stories: list[dict[str, Any]] = []
    for s in sorted(all_story_rows, key=lambda x: x.get("article_count") or 0, reverse=True):
        sid = str(s.get("id") or "")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        cross_stories.append(s)
        if len(cross_stories) >= 9:
            break

    # Stat tile totals.
    total_events = sum(p["event_count"] for p in panels)
    total_stories = sum(p["story_count"] for p in panels)
    total_fatal = sum(p["fatal_count"] for p in panels)

    # Per-country event lists for the "What changed this week" 3-col panel.
    per_country_top_events: list[dict[str, Any]] = []
    for b in dataset.per_country:
        rows = sorted(
            [_prepare_event(e) for e in b.events],
            key=lambda e: e.get("significance") or 0,
            reverse=True,
        )[:5]
        per_country_top_events.append(
            {"iso3": b.iso3, "label": b.label, "event_count": len(b.events), "top_events": rows}
        )

    timeline_events = _prepare_timeline(top_events, dataset.start_date, dataset.end_date)
    day_markers = _day_markers(dataset.start_date, dataset.end_date)

    map_payload = {
        "events": [e for e in all_event_rows if e["has_coords"]],
    }

    lme_sparkline = _macro_sparkline(
        label="LME Aluminum · 3M spot",
        unit="USD/t",
        points=_LME_ALUMINUM_PLACEHOLDER,
    )

    html = template.render(
        start_date=dataset.start_date,
        end_date=dataset.end_date,
        panels=panels,
        total_events=total_events,
        total_stories=total_stories,
        total_fatal=total_fatal,
        country_count=len(panels),
        top_events=top_events,
        timeline_events=timeline_events,
        day_markers=day_markers,
        per_country_top_events=per_country_top_events,
        cross_stories=cross_stories,
        macro_series=[lme_sparkline] if lme_sparkline else [],
        map_payload_json=json.dumps(map_payload),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path
