from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .client import GdeltCloudClient

# Three primary bauxite sourcing regions for the global aluminum trade.
# Roughly 75% of bauxite feedstock for smelters comes from these three countries.
COUNTRIES: list[dict[str, str]] = [
    {"iso3": "GIN", "label": "Guinea", "subtitle": "CBG · SMB · top global bauxite producer"},
    {"iso3": "IDN", "label": "Indonesia", "subtitle": "PT Antam · refining build-out · export bans"},
    {"iso3": "AUS", "label": "Australia", "subtitle": "Rio Tinto Weipa · Alcoa · stable supply"},
]

# Commodity search term used for story clusters across all three countries.
COMMODITY_SEARCH = "aluminum bauxite mining"


@dataclass
class CountryBlock:
    iso3: str
    label: str
    subtitle: str
    events: list[dict[str, Any]] = field(default_factory=list)
    stories: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Dataset:
    per_country: list[CountryBlock] = field(default_factory=list)
    all_events: list[dict[str, Any]] = field(default_factory=list)
    all_stories: list[dict[str, Any]] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""


def fetch_all(client: GdeltCloudClient, start_date: str, end_date: str) -> Dataset:
    """Pull every panel of the demo from the GDELT Cloud REST API.

    Three independent country queries (Guinea, Indonesia, Australia), each
    pulling /api/v2/events + /api/v2/stories. Results merged in Python so
    the dashboard can show per-country panels AND a unified map / table.
    """

    per_country: list[CountryBlock] = []
    all_events: list[dict[str, Any]] = []
    all_stories: list[dict[str, Any]] = []

    for c in COUNTRIES:
        events = client.events(
            country=c["iso3"],
            start_date=start_date,
            end_date=end_date,
            limit=60,
            include_images="false",
        )
        # include_images="true" so the cross-country "Top story clusters"
        # panel at the bottom renders rich image cards (matches the live demo).
        stories = client.stories(
            country=c["iso3"],
            start_date=start_date,
            end_date=end_date,
            search=COMMODITY_SEARCH,
            limit=10,
            include_images="true",
        )

        per_country.append(
            CountryBlock(
                iso3=c["iso3"],
                label=c["label"],
                subtitle=c["subtitle"],
                events=events,
                stories=stories,
            )
        )
        all_events.extend(events)
        all_stories.extend(stories)

    return Dataset(
        per_country=per_country,
        all_events=all_events,
        all_stories=all_stories,
        start_date=start_date,
        end_date=end_date,
    )
