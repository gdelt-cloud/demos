from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .client import GdeltCloudClient

# Red Sea coastline + Houthi-target country net
COUNTRIES = ["YEM", "DJI", "ERI", "SAU", "EGY", "ISR"]
# Bab-el-Mandeb bbox for energy assets layer
ASSETS_BBOX = "11.5,42.5,13.5,44.5"


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
    stories = client.stories(
        country=",".join(COUNTRIES),
        start_date=start_date,
        end_date=end_date,
        article_count_min=8,
        limit=50,
        include_images="false",
    )
    entities = client.entities(
        start_date=start_date,
        end_date=end_date,
        search="Houthi",
        limit=20,
        include_images="false",
    )
    assets = client.energy_assets(
        bbox=ASSETS_BBOX,
        tracker="oil_gas_plants,lng_terminals",
        limit=40,
    )

    return Dataset(
        events=events,
        stories=stories,
        entities=entities,
        assets=assets,
        start_date=start_date,
        end_date=end_date,
    )
