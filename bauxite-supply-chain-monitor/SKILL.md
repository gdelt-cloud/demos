---
name: gdelt-cloud-demo-commodity-supply-chain
description: Use this skill when the user wants to build a GDELT Cloud-powered workflow dashboard for commodity supply-chain monitoring — e.g. bauxite / aluminum brief for Hindalco, copper exposure for Glencore, lithium sourcing for an OEM battery team, cocoa for a confectioner, palm oil for a CPG buyer. Produces a single static HTML dashboard with a multi-country panel grid, a unified world map, a "what changed this week" table, and a commodity price sparkline — from the GDELT Cloud REST API.
triggers:
  - "build a commodity supply-chain monitor for bauxite"
  - "build a commodity supply-chain monitor for copper"
  - "build a commodity supply-chain monitor for lithium"
  - "build a commodity supply-chain monitor for cocoa"
  - "build a commodity supply-chain monitor for palm oil"
  - "scaffold a multi-country sourcing-risk dashboard"
  - "create a conglomerate Group Risk dashboard for [commodity]"
  - "make a per-country supply-chain watchboard"
---

# Building a GDELT Cloud Commodity Supply-Chain Monitor

This skill scaffolds a Python project that calls the GDELT Cloud REST API for **N independent sourcing-region queries**, then merges them into a single static HTML dashboard with a **per-country panel grid**, a unified world map, a "what changed this week" table, and a commodity price sparkline.

It is the **multi-country panel-grid** pattern — distinct from single-region maritime watchboards, which use one country-net + one bbox. Use this skill whenever the workflow is "I source commodity X from N regions and want to track all of them on one page."

## Prerequisites

- A GDELT Cloud API key (`gdelt_sk_*`) — get one at https://gdeltcloud.com/api-keys
- Python 3.11+ and `uv` installed
- A clear idea of the **commodity** + **sourcing regions** (3-5 countries) + the **persona** (Group Risk team at a conglomerate? Procurement at a CPG? OEM battery buyer?)

## Step 1: Pick the commodity and sourcing regions

Use this menu as a starting point. Edit freely — the skill scales to any (commodity, regions) pair.

| Commodity | Sourcing regions (ISO-3) | Commodity search term | Price benchmark |
|-----------|-------------------------|------------------------|-----------------|
| Bauxite / aluminum | GIN, IDN, AUS | `aluminum bauxite mining` | LME aluminum 3M spot (USD/t) |
| Copper | CHL, PER, COD, ZMB | `copper mining smelter` | LME copper 3M spot (USD/t) |
| Lithium | AUS, CHL, ARG, CHN | `lithium mining refining battery` | Battery-grade Li carbonate (USD/t) |
| Cocoa | CIV, GHA, ECU, NGA | `cocoa farmer harvest export` | ICE cocoa futures (USD/t) |
| Palm oil | IDN, MYS, COL, THA | `palm oil plantation export` | MDEX CPO futures (MYR/t) |
| Coffee | BRA, VNM, COL, ETH | `coffee arabica robusta export` | ICE arabica futures (USD/lb) |
| Cobalt | COD, IDN, AUS | `cobalt mining battery DRC` | LME cobalt (USD/t) |
| Rare earths | CHN, AUS, USA, MMR | `rare earth neodymium dysprosium` | NdPr index (USD/kg) |

## Step 2: Scaffold the project

Create a directory layout matching this skeleton:

```
demo-<commodity>-monitor/
  pyproject.toml             # uv project, deps: httpx, jinja2, pydantic-settings
  README.md                  # 1-page description + run instructions
  .env.example               # GDELT_API_KEY, GDELT_BASE_URL, optional date window vars
  .gitignore                 # .env, output/, __pycache__/, .venv/
  src/<package>/
    __init__.py
    __main__.py              # so `python -m <package>` works
    settings.py              # pydantic-settings, env loading, default date window
    client.py                # httpx.Client wrapper, Bearer auth, retry-safe
    fetch.py                 # per-country loop, dataclass merge
    render.py                # Jinja2 -> output/index.html with panel grid + sparkline
    cli.py                   # entry point
  templates/
    index.html.j2            # Tailwind via CDN + Leaflet via CDN + per-country panels
```

Run `uv init demo-<commodity>-monitor` then edit `pyproject.toml` to add deps and a script entry.

## Step 3: Wire the per-country fetch

The key shape difference vs the single-region maritime template: a **list of country dicts** + a **loop** that issues independent queries per country.

```python
COUNTRIES = [
    {"iso3": "GIN", "label": "Guinea",    "subtitle": "CBG · SMB · top global bauxite producer"},
    {"iso3": "IDN", "label": "Indonesia", "subtitle": "PT Antam · refining build-out · export bans"},
    {"iso3": "AUS", "label": "Australia", "subtitle": "Rio Tinto Weipa · Alcoa · stable supply"},
]
COMMODITY_SEARCH = "aluminum bauxite mining"

def fetch_all(client, start_date, end_date):
    per_country, all_events, all_stories = [], [], []
    for c in COUNTRIES:
        events  = client.events( country=c["iso3"], start_date=start_date, end_date=end_date,
                                 limit=60, include_images="false")
        stories = client.stories(country=c["iso3"], start_date=start_date, end_date=end_date,
                                 search=COMMODITY_SEARCH, limit=10, include_images="false")
        per_country.append(CountryBlock(iso3=c["iso3"], label=c["label"],
                                        subtitle=c["subtitle"], events=events, stories=stories))
        all_events.extend(events); all_stories.extend(stories)
    return Dataset(per_country=per_country, all_events=all_events, all_stories=all_stories,
                   start_date=start_date, end_date=end_date)
```

The `subtitle` field is editorial — name the **mining companies, refiners, or policy hooks** that matter for that country. This is what makes the panel feel like a real analyst deliverable instead of a generic data dump.

## Step 4: Wire the HTTP client

`src/<package>/client.py` — a small `httpx.Client` wrapper that attaches `Authorization: Bearer <GDELT_API_KEY>` and exposes one method per endpoint. Reference implementation in this repo at `src/bauxite/client.py` — copy verbatim, just rename the class if you like (keeping `GdeltCloudClient` is fine).

## Step 5: Render the dashboard

`templates/index.html.j2` uses Tailwind via CDN (`cdn.tailwindcss.com`) and Leaflet via CDN (`unpkg.com/leaflet@1.9.4`). The map payload is injected as a `<script type="application/json">` block and parsed client-side.

Key components — keep all of these:

- **Commodity price sparkline** at top (static placeholder; replace with `macro_finance` MCP call)
- **Stat tiles**: events, stories, fatal incidents, sourcing region count
- **Per-country panel grid** (use CSS grid `md:grid-cols-3` for three countries; `md:grid-cols-2 lg:grid-cols-4` for four)
  - Per panel: country label + ISO-3, subtitle (companies / policy hooks), event count, story count, fatal count, top significance, top event title + meta, top commodity story title + meta
- **Leaflet world map** with event markers (size = magnitude, color = Goldstein) — center at `[0, 80]` zoom `1.7` for a global sourcing view, or recenter for your commodity's geography
- **"What changed this week" table** — top 12 events across all countries by significance
- **Footer attribution** to the GDELT Cloud API + repo link

No energy-assets layer by default — GEM trackers cover oil/gas/LNG/coal/power, not mines or refineries. If your commodity has a relevant GEM tracker (e.g. `coal_terminals`), add the asset layer back; otherwise drop it.

## Step 6: Verify and iterate

```bash
uv run python -m <package>
```

Expected output:

- `output/index.html` exists and is >40 KB
- Opening in browser shows three (or N) populated country panels with non-zero event counts
- World map has visible markers across all sourcing regions
- "What changed" table has ≥5 rows

If a country panel is sparse, **drop the search filter** on its stories call (so you catch all stories in that country, not just commodity-tagged ones), or **widen the date window**. The 30-day API cap means longer windows need multiple windowed calls merged in Python.

## Customization checklist

Hand this to your coding agent when adapting:

- [ ] Update `COUNTRIES` list — pick 3-5 sourcing regions; edit each `subtitle` to name the dominant companies / policy hooks
- [ ] Update `COMMODITY_SEARCH` to a 2-4 word term that GDELT's story clustering will resolve well
- [ ] Update the commodity price sparkline label, unit, and (when wiring live data) the `macro_finance` symbol
- [ ] Update `templates/index.html.j2` map `setView()` for your sourcing geography
- [ ] Update README.md + SKILL.md with the new commodity + customer name
- [ ] Pick a panel grid: 3 countries → `md:grid-cols-3`, 4 → `md:grid-cols-2 lg:grid-cols-4`, 5+ → `md:grid-cols-2 lg:grid-cols-3`
- [ ] Update the hero copy ("75% of bauxite from X, Y, Z") to the actual market structure for your commodity

## Data quality gotchas

- **Per-country fetches mean 2×N API calls** — at N=5 sourcing regions that's 10 calls per refresh. Cache aggressively (the hosted Next.js version uses `revalidate = 86400`).
- **Story coverage varies by region** — a niche sourcing country (e.g. CIV cocoa) will produce far fewer commodity-tagged stories than a major one. The panel will still render, just with `0 stories` on the sparse country.
- **The 30-day window cap on `/api/v2/events`** means a 60d demo needs two API calls per country merged in Python.
- **`include_images=false` is mandatory** — these queries can return hundreds of articles per cluster; image URLs balloon the payload by 5-10×.
- **Sourcing-region selection is editorial, not algorithmic** — don't let the agent guess. Ask the user explicitly which N countries matter for their workflow, or use the table in Step 1.

## Reference

Working example: this repo (`src/bauxite/`). Read it end-to-end as a template. The hosted Next.js version at `nextjs_/app/demos/bauxite-supply-chain-monitor/page.tsx` is the visual reference for the panel-grid + map + table layout.
