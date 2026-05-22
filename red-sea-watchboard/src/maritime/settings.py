from __future__ import annotations

from datetime import date, timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Demo configuration. Reads from `.env` / env vars."""

    gdelt_api_key: str = ""
    gdelt_base_url: str = "https://gdeltcloud.com"
    # Optional fixed window — defaults to last 7 days (weekly report).
    # The live hosted demo uses the same 7-day window; lengthen via env vars
    # if you want a longer back-look (the /api/v2/events endpoint caps at 30 days
    # per call, so for 60+ day windows you'll need two calls merged in Python).
    red_sea_date_start: str | None = None
    red_sea_date_end: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False, extra="ignore")

    def resolved_window(self) -> tuple[str, str]:
        """Return (start_date, end_date) as ISO strings, defaulting to last 7 days."""
        if self.red_sea_date_start and self.red_sea_date_end:
            return self.red_sea_date_start, self.red_sea_date_end
        today = date.today()
        start = today - timedelta(days=6)  # inclusive 7-day window
        return start.isoformat(), today.isoformat()
