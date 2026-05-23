from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class ApiConfig:
    weather_url: str = "https://api.open-meteo.com/v1/forecast"
    geocoding_url: str = "https://nominatim.openstreetmap.org/reverse"
    user_agent: str = "bobo-test-weather/1.0"
    timeout: float = 10.0


def extract_temperature(data: dict[str, Any]) -> float | None:
    return data.get("current_weather", {}).get("temperature")


def format_location_from_geocode(
    data: dict[str, Any],
    latitude: float,
    longitude: float,
) -> str:
    address = data.get("address", {})
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
    )
    country = address.get("country")
    if city and country:
        return f"{city}, {country}"
    if data.get("display_name"):
        return data["display_name"]
    return f"{latitude:.4f}°, {longitude:.4f}°"


class WeatherService:
    def __init__(
        self,
        config: ApiConfig | None = None,
        session: requests.Session | None = None,
    ) -> None:
        self._config = config or ApiConfig()
        self._session = session or requests.Session()

    def fetch_weather(self, latitude: float, longitude: float) -> dict[str, Any]:
        try:
            response = self._session.get(
                self._config.weather_url,
                params={
                    "latitude": latitude,
                    "longitude": longitude,
                    "current_weather": "true",
                },
                timeout=self._config.timeout,
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            raise

    def resolve_location_name(self, latitude: float, longitude: float) -> str:
        try:
            response = self._session.get(
                self._config.geocoding_url,
                params={
                    "lat": latitude,
                    "lon": longitude,
                    "format": "json",
                    "accept-language": "tr",
                },
                headers={"User-Agent": self._config.user_agent},
                timeout=self._config.timeout,
            )
            response.raise_for_status()
            return format_location_from_geocode(
                response.json(), latitude, longitude
            )
        except requests.RequestException:
            pass
        return f"{latitude:.4f}°, {longitude:.4f}°"

    def get_current_temperature(
        self, latitude: float, longitude: float
    ) -> tuple[str, float | None]:
        data = self.fetch_weather(latitude, longitude)
        location = self.resolve_location_name(latitude, longitude)
        return location, extract_temperature(data)


if __name__ == "__main__":
    try:
        lat = float(input("Enlem (latitude) giriniz: "))
        lon = float(input("Boylam (longitude) giriniz: "))
        service = WeatherService()
        location, temp = service.get_current_temperature(lat, lon)
        if temp is not None:
            print(f"Konum: {location}")
            print(f"Anlık sıcaklık: {temp}°C")
        else:
            print("Sıcaklık bilgisi alınamadı.")
    except ValueError:
        print("Geçerli bir sayı giriniz.")
    except requests.RequestException as e:
        print(f"API isteği sırasında hata oluştu: {e}")
