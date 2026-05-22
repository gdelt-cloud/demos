---
name: gdelt-cloud-demo-maritime
description: Use this skill when the user wants to build a GDELT Cloud-powered workflow dashboard for maritime intelligence — e.g. Red Sea threat brief, Suez Canal disruption watchboard, South China Sea routing assessment, Strait of Malacca chokepoint monitor. Produces a single static HTML dashboard from the GDELT Cloud REST API + an optional MCP snapshot.
triggers:
  - "build a GDELT Cloud demo for maritime risk"
  - "scaffold a maritime watchboard"
  - "create a chokepoint monitor"
  - "make a strait/route/coastline threat dashboard"
---

# Building a GDELT Cloud Maritime Watchboard

This skill scaffolds a Python project that calls the GDELT Cloud REST API for a chosen maritime region and renders a single static HTML dashboard — map, events table, story clusters, entity panel.

## Prerequisites

- A GDELT Cloud API key (`gdelt_sk_*`) — get one at https://gdeltcloud.com/api-keys
- Python 3.11+ and `uv` installed
- A clear idea of the **region** (country list + bbox) and the **persona** (analyst preparing a brief? underwriter pricing a route?)

## Step 1: Scaffold the project

Create a directory layout matching this skeleton:

```
demo-<topic>/
  pyproject.toml             # uv project, deps: httpx, jinja2, pydantic-settings
  README.md                  # 1-page description + run instructions
  .env.example               # GDELT_API_KEY, GDELT_BASE_URL, optional date window vars
  .gitignore                 # .env, output/, __pycache__/, .venv/
  src/<package>/
    __init__.py
    settings.py              # pydantic-settings, env loading, default date window
    client.py                # httpx.Client wrapper, Bearer auth, retry-safe
    fetch.py                 # the API calls for this demo + dataclass
    render.py                # Jinja2 -> output/index.html
    cli.py                   # `python -m <package>` entry
  templates/
    index.html.j2            # Tailwind via CDN + Leaflet via CDN
```

Run `uv init demo-<topic>` then edit `pyproject.toml` to add deps and a script entry.

## Step 2: Configure the data shape

Pick exactly one **country net** and one **bbox** that matches the maritime region.

| Region | Country net (ISO-3) | Bbox (lat_min,lon_min,lat_max,lon_max) |
|--------|---------------------|----------------------------------------|
| Red Sea / Bab-el-Mandeb | YEM, DJI, ERI, SAU, EGY, ISR | 11.5,42.5,13.5,44.5 |
| Strait of Hormuz | IRN, OMN, ARE, QAT | 24,49,30,57 |
| Suez Canal | EGY | 29,32,32,33 |
| Strait of Malacca | MYS, IDN, SGP | 1,99,6,104 |
| South China Sea | PHL, VNM, MYS, BRN | 8,108,22,121 |
| Eastern Med | TUR, GRC, CYP, EGY, LBN, ISR | 32,28,38,38 |

In `fetch.py`:

```python
COUNTRIES = ["YEM", "DJI", "ERI", "SAU", "EGY", "ISR"]  # change for your region
ASSETS_BBOX = "11.5,42.5,13.5,44.5"                      # change for your bbox

def fetch_all(client, start_date, end_date):
    events = client.events(country=",".join(COUNTRIES),
                           start_date=start_date, end_date=end_date,
                           limit=100, include_images="false")
    stories = client.stories(country=",".join(COUNTRIES),
                             start_date=start_date, end_date=end_date,
                             article_count_min=8, limit=50,
                             include_images="false")
    entities = client.entities(search="<your-anchor-entity>",  # e.g. "Houthi", "IRGC"
                               start_date=start_date, end_date=end_date,
                               limit=20, include_images="false")
    assets = client.energy_assets(bbox=ASSETS_BBOX,
                                  tracker="oil_gas_plants,lng_terminals",
                                  limit=40)
    return Dataset(events=events, stories=stories, entities=entities, assets=assets, ...)
```

## Step 3: Wire the HTTP client

`src/<package>/client.py` — a small `httpx.Client` wrapper that attaches `Authorization: Bearer <GDELT_API_KEY>` and exposes one method per endpoint. Reference implementation in this repo at `src/maritime/client.py` — copy verbatim, just rename the class.

## Step 4: Render the dashboard

`templates/index.html.j2` uses Tailwind via CDN (`cdn.tailwindcss.com`) and Leaflet via CDN (`unpkg.com/leaflet@1.9.4`). The map payload is injected as a `<script type="application/json">` block and parsed client-side.

Key things to keep:

- **Stat tiles** at top: events, stories, fatal incidents, assets
- **Leaflet map** with event markers (size = magnitude, color = Goldstein) + asset markers (squares)
- **Events table** (top 15 by significance)
- **Story clusters list** (top 8 by article count)
- **Entities sidebar** (top 10 from search)
- **Footer attribution** to the GDELT Cloud API

## Step 5: Verify and iterate

```bash
uv run python -m <package>
```

Expected output:

- `output/index.html` exists and is >50 KB
- Opening in browser shows a populated map with ≥20 event markers
- Tables aren't empty

If the data looks anemic, **widen the country net** or **lengthen the date window**. The 30-day API cap means longer windows need either bbox-only filtering or multiple windowed calls merged in Python.

## Customization checklist

Hand this to your coding agent when adapting:

- [ ] Update `COUNTRIES` for your maritime region
- [ ] Update `ASSETS_BBOX` to encompass your chokepoint
- [ ] Change the entity `search` term to match the threat actor / shipping company / state actor relevant to your route
- [ ] Update `templates/index.html.j2` map `setView()` for your region's center + zoom
- [ ] Update README.md and SKILL.md with the new region + customer name
- [ ] Adjust `article_count_min` for stories — busier regions can filter higher (e.g. 15-20), quiet regions need lower (3-5)
- [ ] Consider adding a `domain` filter on events (e.g. `domain=INFRASTRUCTURE` for chokepoint-focused workflows)

## Data quality gotchas

- **Entity link tables only have rich coverage from April 2026 onwards.** Older windows may show empty entity panels — pivot to recent windows for entity-rich dashboards.
- **Energy assets bbox is strict** — if your chokepoint has no GEM-tracked oil/gas/LNG infrastructure, the asset layer will be empty (and that's OK — the demo still works, just remove the asset bullet from the stat tiles).
- **The 30-day window cap on `/api/v2/events`** means a 60d demo needs two API calls merged in Python.

## Reference

Working example: this repo (`src/maritime/`). Read it end-to-end as a template.
