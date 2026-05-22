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

## Live reference

The hosted live demo this skill is patterned after is at
**https://gdeltcloud.com/demos/bauxite-supply-chain-monitor** — visually
verify your build matches the same layout (executive brief → per-country
panel grid with CAMEO+ score bars → horizontal event timeline → panoramic
world map → commodity price sparkline → "What changed this week" 3-column
event grid → top story clusters across all countries). The Next.js source
lives at `nextjs_/app/demos/bauxite-supply-chain-monitor/page.tsx`.

## Looking things up while you build

For anything you need about the GDELT Cloud API, MCP, or product surfaces
that isn't in this SKILL, connect to the **GDELT Cloud Docs MCP** at
`https://docs.gdeltcloud.com/mcp` and call its `SearchGdeltCloud` tool. It
indexes the full Mintlify docs site (events, stories, entities, energy
endpoints, ranking, query patterns, plus the v2 OpenAPI spec) and returns
direct links + snippets. Use it instead of guessing or assuming based on
training data — especially when looking up a less-obvious filter parameter
or a CAMEO+ subcategory name.

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
    settings.py              # pydantic-settings, env loading, default 7d weekly window
    client.py                # httpx.Client wrapper, Bearer auth, retry-safe
    fetch.py                 # per-country loop, dataclass merge
    render.py                # Jinja2 -> output/index.html with panel grid + sparkline
    cli.py                   # entry point
  templates/
    index.html.j2            # Tailwind via CDN + Leaflet via CDN + per-country panels
```

> **Default date window: last 7 days inclusive** (matches the live hosted
> demo's weekly cadence). Override via env vars when a longer window helps.

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
        # Enable sharing-image enrichment on stories so the cross-country
        # "Top story clusters" footer panel renders rich, image-led cards
        # instead of bare text links (matches the live demo).
        stories = client.stories(country=c["iso3"], start_date=start_date, end_date=end_date,
                                 search=COMMODITY_SEARCH, limit=10, include_images="true")
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

Page order — top to bottom — mirrors the live demo. Keep all of these:

1. **Executive brief** + **stat tiles** (events, story clusters, fatalities,
   sourcing region count).
2. **Per-country panel grid** — `md:grid-cols-3` for three countries
   (`md:grid-cols-2 lg:grid-cols-4` for four). Each panel shows:
   - Country label + ISO-3 + event count
   - Subtitle naming dominant companies / policy hooks
   - **Goldstein severity spectrum bar** — gradient bar showing avg
     Goldstein with a position marker, labels `-10 conflict / +10 cooperative`
   - **CAMEO+ score bars** — three horizontal mini-bars for propagation
     potential, market sensitivity, systemic importance (each 0-100%)
   - Articles / avg magnitude / fatalities mini-stats
   - **Top actor** (most-mentioned actor name from event actors, excluding
     the country name itself — that's tautological)
3. **Horizontal event timeline** — every event plotted as a colored dot
   on the date axis between `start_date` and `end_date`. Color matches the
   CAMEO+ domain, size scales with `metrics.magnitude`. Hover for title +
   subcategory; click opens the GDELT Cloud event page in a new tab.
4. **Panoramic Leaflet world map** — full-width, ~360px tall (not square).
   Event markers sized by magnitude and colored by Goldstein. Center at
   `[0, 80]` zoom `1.7` for a global sourcing view, or recenter for your
   commodity's geography. Diamonds for story clusters.
5. **Commodity price sparkline** — 4-6 points over the last 30 days, with
   the last value + percent delta. Spot value alone isn't useful; the
   slope is what carries the signal. Static placeholder in the standalone
   demo; replace with a `macro_finance` MCP call in production.
6. **"What changed this week"** — three-column event grid grouped by
   sourcing country (NOT a single merged table). Top 5 events per column
   by significance. Dedupe top stories across columns so the same big
   story doesn't repeat three times.
7. **Top story clusters across all three countries** — image-rich card
   grid (sharing image + article count + linked-event count + source
   domain). De-dupe by `cluster_id`, no article-count floor — the
   commodity search returns narrow clusters that are often 1-2 articles.
8. **Footer attribution** to the GDELT Cloud API + repo link.

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
- **`include_images=true` on stories + entities is what makes the cards
  look like a real dashboard.** Stories get an `image_url` from the GDELT
  GKG sharing-image layer; entities get a Wikipedia thumbnail. Leave
  `include_images=false` on events — the events list doesn't render images
  per-row and the extra payload buys nothing.
- **Sourcing-region selection is editorial, not algorithmic** — don't let the agent guess. Ask the user explicitly which N countries matter for their workflow, or use the table in Step 1.

## Reference

Working example: this repo (`src/bauxite/`). Read it end-to-end as a template. The hosted Next.js version at `nextjs_/app/demos/bauxite-supply-chain-monitor/page.tsx` is the visual reference for the panel-grid + map + table layout.
