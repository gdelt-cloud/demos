---
name: gdelt-cloud-demo-war-risk-underwriting
description: Use this skill when the user wants to build a GDELT Cloud-powered war-risk underwriting brief — e.g. Strait of Hormuz tanker hull/war pricing, Suez Canal transit risk, Red Sea alternate-route exposure, Strait of Malacca chokepoint check. Produces a single printable HTML brief from the GDELT Cloud REST API + an optional MCP macro snapshot, sized for a marine war-risk underwriter or aviation war-risk desk.
triggers:
  - "build a war-risk underwriting brief for the Strait of Hormuz"
  - "build a war-risk underwriting brief for Suez"
  - "build a war-risk underwriting brief for the Red Sea"
  - "build a war-risk underwriting brief for the Strait of Malacca"
  - "scaffold a marine war-risk brief"
  - "create a tanker hull/war pricing brief"
  - "make a chokepoint underwriting brief"
---

# Building a GDELT Cloud War-Risk Underwriting Brief

This skill scaffolds a Python project that calls the GDELT Cloud REST API for a chosen war-risk corridor and renders a single **printable** HTML brief — map, events table, story clusters, entity panel, and a macro (Brent/WTI/freight) sidebar. The deliverable is a one-page brief suitable for circulating to a war-risk committee or attaching to a quote.

## Personas this skill is for

- **Marine war-risk underwriter** pricing a tanker hull/war policy through a chokepoint
- **Energy trader desk** evaluating freight exposure on a specific lane
- **Aviation war-risk underwriter** monitoring an over-flight corridor (adapt the bbox to airspace)
- **Reinsurance treaty analyst** running a corridor-stress snapshot for renewal review

## Prerequisites

- A GDELT Cloud API key (`gdelt_sk_*`) — get one at https://gdeltcloud.com/api-keys
- Python 3.11+ and `uv` installed
- A clear idea of the **corridor** (country net + bbox) and the **anchor entity** (state actor, militant group, named threat)

## Live reference

The hosted live demo this skill is patterned after is at
**https://gdeltcloud.com/demos/strait-of-hormuz-underwriting-brief** —
visually verify your build matches the same layout (executive brief →
KPI tiles with "Energy MW at risk" → horizontal event timeline → panoramic
map → Brent + WTI sparklines → events / image-rich story cards / entity
cards footer grid). The Next.js source lives at
`nextjs_/app/demos/strait-of-hormuz-underwriting-brief/page.tsx`.

## Looking things up while you build

For anything you need about the GDELT Cloud API, MCP, or product surfaces
that isn't in this SKILL, connect to the **GDELT Cloud Docs MCP** at
`https://docs.gdeltcloud.com/mcp` and call its `SearchGdeltCloud` tool. It
indexes the full Mintlify docs site (events, stories, entities, energy
endpoints, ranking, query patterns, plus the v2 OpenAPI spec) and returns
direct links + snippets. Use it instead of guessing or assuming based on
training data — and especially before making up a v2 parameter you "think"
exists.

## Step 1: Pick a corridor and an entity anchor

Use one of the menus below as your starting point — they pre-fill the country net, bbox, and a sensible entity search.

### Corridor menu (region → countries + bbox)

| Corridor | Country net (ISO-3) | Bbox (lat_min,lon_min,lat_max,lon_max) | Map center | Zoom |
|----------|---------------------|----------------------------------------|------------|------|
| **Strait of Hormuz** | IRN, OMN, ARE, QAT | 24,49,30,57 | [26, 55] | 5 |
| **Suez Canal** | EGY | 29,32,32,33 | [30, 32.5] | 7 |
| **Red Sea / Bab-el-Mandeb** (alternate to Hormuz) | YEM, DJI, ERI, SAU, EGY, ISR | 11.5,42.5,13.5,44.5 | [17, 44.5] | 4 |
| **Strait of Malacca** | MYS, IDN, SGP | 1,99,6,104 | [3.5, 101.5] | 5 |

### Entity-anchor menu (entity search term → coverage)

| Anchor | When to use |
|--------|-------------|
| `Iran` | Hormuz, Persian Gulf state-actor narrative |
| `IRGC` | Hormuz / Levant proxy networks |
| `Houthi` | Red Sea / Bab-el-Mandeb attacks on shipping |
| `Hezbollah` | Eastern Med + Levant overspill |
| `Saudi Arabia` | Gulf state-actor counter-narrative |
| `Israel` | Eastern Med + Red Sea cross-strikes |
| `China` | South China Sea / Strait of Malacca posture |

Combine **one corridor** + **one entity anchor** — the corridor sets the country/bbox filter, the entity anchor sets the named-entities sidebar.

## Step 2: Scaffold the project

```
demo-<corridor>-brief/
  pyproject.toml             # uv project, deps: httpx, jinja2, pydantic-settings
  README.md                  # 1-page description + run instructions
  .env.example               # GDELT_API_KEY, GDELT_BASE_URL, optional date window vars
  .gitignore                 # .env, output/, __pycache__/, .venv/
  src/<package>/
    __init__.py
    __main__.py              # so `python -m <package>` works
    settings.py              # pydantic-settings, env loading, default 7d weekly window
    client.py                # httpx.Client wrapper, Bearer auth, retry-safe
    fetch.py                 # the 4 API calls + Dataset dataclass
    render.py                # Jinja2 -> output/index.html, rolls up capacity_mw
    cli.py                   # `python -m <package>` entry, prints output path
  templates/
    index.html.j2            # Tailwind + Leaflet via CDN, includes PRINT CSS
```

Run `uv init demo-<corridor>-brief` then edit `pyproject.toml` to add deps.

## Step 3: Configure the data shape

In `fetch.py`:

```python
COUNTRIES = ["IRN", "OMN", "ARE", "QAT"]   # corridor menu
ASSETS_BBOX = "24,49,30,57"                 # corridor menu

def fetch_all(client, start_date, end_date):
    events = client.events(country=",".join(COUNTRIES),
                           start_date=start_date, end_date=end_date,
                           limit=100, include_images="false")
    stories = client.stories(country=",".join(COUNTRIES),
                             start_date=start_date, end_date=end_date,
                             article_count_min=5, limit=40,         # underwriter signal threshold
                             # Enable sharing-image enrichment so story cards
                             # carry the article hero image. Matches the live
                             # underwriting brief which leads with visual story
                             # identity, not text-only links.
                             include_images="true")
    entities = client.entities(search="Iran",                       # entity-anchor menu
                               start_date=start_date, end_date=end_date,
                               limit=20,
                               # Enable Wikipedia thumbnail enrichment so the
                               # entity sidebar shows recognizable people /
                               # organizations rather than bare names.
                               include_images="true")
    assets = client.energy_assets(bbox=ASSETS_BBOX,
                                  tracker="oil_gas_plants,lng_terminals",
                                  limit=60)
    return Dataset(events=events, stories=stories, entities=entities, assets=assets, ...)
```

`article_count_min=5` is the live demo's threshold for the underwriting
persona — busy corridors can push to 12-20, quiet ones to 3-4.

## Step 4: Roll up the headline figures (underwriter-flavored)

In `render.py`, in addition to the standard event/story/entity tiles, compute:

```python
total_capacity_mw = sum((a.get("capacity_mw") or 0) for a in assets_rows)
# Format as "12.4k" if > 1000 MW
```

The **"Energy MW at risk"** tile (capacity_mw summed across all assets in the bbox) is the headline an underwriter cares about more than raw asset count.

Fatal-incident count + total fatalities is the other underwriter-relevant headline — pull that out of the events.

## Step 5: Wire the printable brief template

`templates/index.html.j2` uses Tailwind via CDN and Leaflet via CDN. The
brief is organized as **four numbered sections** that mirror the hosted
live version — keep this order:

1. **Event timeline** — horizontal strip plotting every event on the date
   axis between `start_date` and `end_date`. Dot color matches the CAMEO+
   domain, dot size scales with `metrics.magnitude`. Hover reveals title +
   subcategory; click opens the GDELT Cloud event page in a new tab. Use
   ~150px tall total and 3-4 alternating lanes around the axis so adjacent
   dates don't pile up. The live demo's React component is the reference:
   `nextjs_/components/demos/event-timeline.tsx`.
2. **Strait of Hormuz disruption picture** — panoramic Leaflet map
   (full-width, ~380px tall, not square). Squares for energy terminals,
   circles for events sized by magnitude / colored by Goldstein, diamonds
   for story clusters. Layer toggles for Events / Stories / Energy assets.
3. **Marine war-risk macro** — Brent + WTI sparklines (4-6 points,
   ~30-day window). Show last value + percent delta next to each. Source
   is the MCP `macro_finance` proxy in production; in the standalone demo
   ship hard-coded placeholder points so the brief is self-contained.
4. **Events + story clusters + named entities** — three-column footer:
   structured events list (top 15 by significance), image-rich story cards
   (with article sharing image + linked-event count + source domain), and
   entity cards with Wikipedia thumbnails + horizontal metric bars
   (Articles / Stories / Events) scaled relative to the heaviest entity.

Plus:

- **Energy MW at risk** is the headline KPI tile underwriters care about
  most — sum `capacity.mw` across `assets` (note the nested shape: `geo.lat`,
  `capacity.mw`, NOT flat `latitude`/`capacity_mw`). Format as "12.4k" if >1000 MW.
- **Print CSS** is required — wrap inside `@media print { ... }` with:
  page-break-inside on sections, larger header font, smaller map height
  (~360px), hide refresh/no-print elements, drop link underlines.
- Map `setView()` per the corridor menu.

## Step 6: Verify

```bash
uv run python -m <package>
```

Expected:

- `output/index.html` exists and is >50 KB
- Opening in a browser shows a populated map with ≥20 event markers + several asset squares
- Cmd/Ctrl+P preview is a clean 1-2 page brief (no UI chrome)

If data looks anemic, widen the country net or stretch the date window. For 60+ day windows you'll need two API calls merged in Python (the events endpoint caps at 30d per call).

## Customization checklist (hand to coding agent)

- [ ] Pick a corridor from the menu and update `COUNTRIES` + `ASSETS_BBOX`
- [ ] Pick an entity anchor and update `client.entities(search=...)`
- [ ] Update `templates/index.html.j2` map `setView()` to the corridor map center + zoom
- [ ] Update the H1 + subtitle in the template for the chosen corridor and persona
- [ ] Update README.md + SKILL.md region/persona references
- [ ] Confirm print CSS is intact — test Cmd/Ctrl+P in the browser
- [ ] Adjust `article_count_min` for stories — busy corridors push to 15-20, quiet to 6-8
- [ ] Decide whether to keep the energy-assets tile (drop it if the chokepoint has no GEM-tracked oil/gas/LNG infrastructure)

## Data quality gotchas

- **Entity link tables only have rich coverage from April 2026 onwards.** Older windows may show empty entity panels — pivot to recent windows for entity-rich briefs.
- **Energy assets bbox is strict** — if your corridor has no GEM-tracked infrastructure, the asset layer will be empty (and that's OK — the brief still works, just remove the asset bullet from the stat tiles).
- **The 30-day window cap on `/api/v2/events`** means a 60d brief needs two API calls merged in Python.
- **Macro sparklines** — the standalone demo ships with hard-coded 4-6 point
  series so the brief is self-contained. The hosted Next.js demo pulls live
  values from the GDELT Cloud MCP `macro_finance` proxy (Alpha Vantage
  upstream); both render the same little SVG line + last value + percent
  delta. Spot value alone (e.g. "Brent $89.4") doesn't carry the signal —
  the slope does, so always render the line.

## Reference

Working example: this repo (`src/hormuz/`). Read it end-to-end as a template — the package layout, the print CSS, and the capacity_mw rollup are all reusable across corridors.
