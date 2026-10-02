from typing import Any

import httpx


async def fetch_daily_forecast(latitude: float | None, longitude: float | None) -> dict[str, Any] | None:
    if latitude is None or longitude is None:
        return None
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "precipitation_sum,temperature_2m_mean",
        "forecast_days": 3,
        "timezone": "UTC",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("https://api.open-meteo.com/v1/forecast", params=params)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError):
        return None