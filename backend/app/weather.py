"""Open-Meteo weather client with in-memory cache and fallback support."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
from pydantic import BaseModel

from .utils import iso_hour_key

SNOWMASS_LOCATION = {"name": "Snowmass", "lat": 39.2094, "lon": -106.9495}
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class HourlyWeather(BaseModel):
    time: datetime
    temperature: float
    precipitation: float
    wind_speed: float
    wind_direction: float
    cloud_cover: float


class WeatherResult(BaseModel):
    hours: list[HourlyWeather]
    source: str = "open-meteo"
    available: bool = True


class WeatherClient:
    """Fetches hourly forecast data and caches by target hour + horizon."""

    def __init__(self) -> None:
        self._cache: dict[str, WeatherResult] = {}
        self.last_ok: bool | None = None
        self.last_fetch_at: datetime | None = None
        self.last_error: str | None = None

    def get_forecast(self, target: datetime, horizon_hours: int) -> WeatherResult:
        cache_key = f"{iso_hour_key(target)}:{horizon_hours}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        params = {
            "latitude": SNOWMASS_LOCATION["lat"],
            "longitude": SNOWMASS_LOCATION["lon"],
            "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_direction_10m,cloud_cover",
            "forecast_days": 2,
            "timezone": "UTC",
        }

        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.get(OPEN_METEO_URL, params=params)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            result = WeatherResult(
                hours=self._neutral_hours(target, horizon_hours),
                source="open-meteo-unavailable",
                available=False,
            )
            self._cache[cache_key] = result
            self.last_ok = False
            self.last_fetch_at = datetime.now(UTC)
            self.last_error = str(exc)
            return result

        result = self._extract_hours(payload, target, horizon_hours)
        self._cache[cache_key] = result
        self.last_ok = result.available
        self.last_fetch_at = datetime.now(UTC)
        self.last_error = None if result.available else "No weather rows matched requested horizon"
        return result

    def _extract_hours(self, payload: dict, target: datetime, horizon_hours: int) -> WeatherResult:
        hourly = payload.get("hourly", {})
        times = hourly.get("time", [])
        lookup = {}
        for idx, t in enumerate(times):
            lookup[t] = HourlyWeather(
                time=datetime.fromisoformat(t).replace(tzinfo=UTC),
                temperature=hourly["temperature_2m"][idx],
                precipitation=hourly["precipitation"][idx],
                wind_speed=hourly["wind_speed_10m"][idx],
                wind_direction=hourly["wind_direction_10m"][idx],
                cloud_cover=hourly["cloud_cover"][idx],
            )

        target_utc = target.astimezone(UTC) if target.tzinfo else target.replace(tzinfo=UTC)
        target_hour = target_utc.replace(minute=0, second=0, microsecond=0)
        selected: list[HourlyWeather] = []
        for offset in range(horizon_hours):
            slot = target_hour + timedelta(hours=offset)
            slot_key = slot.strftime("%Y-%m-%dT%H:%M")
            if slot_key in lookup:
                selected.append(lookup[slot_key])

        if not selected:
            return WeatherResult(
                hours=self._neutral_hours(target, horizon_hours),
                source="open-meteo-unavailable",
                available=False,
            )
        return WeatherResult(hours=selected)

    def _neutral_hours(self, target: datetime, horizon_hours: int) -> list[HourlyWeather]:
        target_utc = target.astimezone(UTC) if target.tzinfo else target.replace(tzinfo=UTC)
        baseline = target_utc.replace(minute=0, second=0, microsecond=0)
        return [
            HourlyWeather(
                time=baseline + timedelta(hours=i),
                temperature=-5.0,
                precipitation=0.0,
                wind_speed=10.0,
                wind_direction=270.0,
                cloud_cover=45.0,
            )
            for i in range(horizon_hours)
        ]
