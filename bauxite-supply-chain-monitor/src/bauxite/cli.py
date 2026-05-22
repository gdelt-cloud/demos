from __future__ import annotations

import sys
from pathlib import Path

from .client import GdeltCloudClient
from .fetch import fetch_all
from .render import render_dashboard
from .settings import Settings


def main() -> int:
    settings = Settings()
    if not settings.gdelt_api_key:
        print("ERROR: set GDELT_API_KEY in .env or environment.", file=sys.stderr)
        return 1

    start_date, end_date = settings.resolved_window()
    print(f"GDELT Cloud Bauxite Supply-Chain Monitor · {start_date} → {end_date}")
    print(f"Base URL: {settings.gdelt_base_url}")

    with GdeltCloudClient(api_key=settings.gdelt_api_key, base_url=settings.gdelt_base_url) as client:
        dataset = fetch_all(client, start_date, end_date)

    per_country_summary = " · ".join(
        f"{b.label}: {len(b.events)}e/{len(b.stories)}s" for b in dataset.per_country
    )
    print(
        f"Fetched: {len(dataset.all_events)} events · {len(dataset.all_stories)} stories "
        f"across {len(dataset.per_country)} countries"
    )
    print(f"  per-country → {per_country_summary}")

    output_dir = Path("output")
    output_path = render_dashboard(dataset, output_dir)
    print(f"\n✓ Rendered: {output_path.resolve()}")
    print(f"  Open in browser:  file://{output_path.resolve()}")
    print(f"  Or serve locally: python -m http.server --directory output  # then visit http://localhost:8000/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
