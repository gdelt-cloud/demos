from __future__ import annotations

from datetime import date, timedelta

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Demo configuration. Reads from `.env` / env vars."""

    gdelt_api_key: str = ""
    gdelt_base_url: str = "https://gdeltcloud.com"
    # Optional fixed window — defaults to last 7 days (weekly brief). The live
    # hosted demo uses the same 7-day window; the /api/v2/events endpoint caps
    # at 30 days per call, so for 60+ day windows you'll need two API calls
    # merged in Python.
    hormuz_date_start: str | None = None
    hormuz_date_end: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False, extra="ignore")

    def resolved_window(self) -> tuple[str, str]:
        """Return (start_date, end_date) as ISO strings, defaulting to last 7 days."""
        if self.hormuz_date_start and self.hormuz_date_end:
            return self.hormuz_date_start, self.hormuz_date_end
        today = date.today()
        start = today - timedelta(days=6)  # inclusive 7-day window
        return start.isoformat(), today.isoformat()
