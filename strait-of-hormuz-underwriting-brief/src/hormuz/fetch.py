from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .client import GdeltCloudClient

# Strait of Hormuz littoral states
COUNTRIES = ["IRN", "OMN", "ARE", "QAT"]
# Persian Gulf + Strait of Hormuz bbox for energy assets layer
ASSETS_BBOX = "24,49,30,57"


@dataclass
class Dataset:
    events: list[dict[str, Any]] = field(default_factory=list)
    stories: list[dict[str, Any]] = field(default_factory=list)
    entities: list[dict[str, Any]] = field(default_factory=list)
    assets: list[dict[str, Any]] = field(default_factory=list)
    start_date: str = ""
    end_date: str = ""


def fetch_all(client: GdeltCloudClient, start_date: str, end_date: str) -> Dataset:
    """Pull every panel of the demo from the GDELT Cloud REST API."""

    events = client.events(
        country=",".join(COUNTRIES),
        start_date=start_date,
        end_date=end_date,
        limit=100,
        include_images="false",
    )
    # include_images="true" so story cards render with article sharing images
    # and the entity sidebar shows Wikipedia thumbnails — matches the live demo.
    stories = client.stories(
        country=",".join(COUNTRIES),
        start_date=start_date,
        end_date=end_date,
        article_count_min=5,
        limit=40,
        include_images="true",
    )
    entities = client.entities(
        start_date=start_date,
        end_date=end_date,
        search="Iran",
        limit=20,
        include_images="true",
    )
    assets = client.energy_assets(
        bbox=ASSETS_BBOX,
        tracker="oil_gas_plants,lng_terminals",
        limit=60,
    )

    return Dataset(
        events=events,
        stories=stories,
        entities=entities,
        assets=assets,
        start_date=start_date,
        end_date=end_date,
    )
