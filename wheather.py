import logging
import os
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import requests
LOG_FILE = Path(__file__).resolve().parent / "app.log"
LOG_MAX_BYTES = 1 * 1024 * 1024  # 1 MB
LOG_BACKUP_COUNT = 5
USER_FRIENDLY_ERROR_MSG = "Bir hata oluştu, detaylar app.log dosyasında."
logger = logging.getLogger(__name__)


def setup_logging() -> None:
    if logger.handlers:
        return
    logger.setLevel(logging.INFO)
    logger.propagate = False
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def report_user_error() -> None:
    print(USER_FRIENDLY_ERROR_MSG)


setup_logging()


DEFAULT_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
DEFAULT_GEOCODING_URL = "https://nominatim.openstreetmap.org/reverse"
DEFAULT_USER_AGENT = "bobo-test-weather/1.0"
DEFAULT_TIMEOUT = 10.0


@dataclass(frozen=True)
class ApiConfig:
    weather_url: str = DEFAULT_WEATHER_URL
    geocoding_url: str = DEFAULT_GEOCODING_URL
    user_agent: str = DEFAULT_USER_AGENT
    timeout: float = DEFAULT_TIMEOUT
    api_key: str | None = None


def load_config_from_env() -> ApiConfig:
    timeout_raw = os.getenv("REQUEST_TIMEOUT", str(DEFAULT_TIMEOUT))
    api_key = os.environ.get("API_KEY")
    return ApiConfig(
        weather_url=os.getenv("WEATHER_API_URL", DEFAULT_WEATHER_URL),
        geocoding_url=os.getenv("GEOCODING_API_URL", DEFAULT_GEOCODING_URL),
        user_agent=os.getenv("NOMINATIM_USER_AGENT", DEFAULT_USER_AGENT),
        timeout=float(timeout_raw),
        api_key=api_key if api_key else None,
    )


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
        self._config = config or load_config_from_env()
        self._session = session or requests.Session()

    def fetch_weather(self, latitude: float, longitude: float) -> dict[str, Any]:
        params: dict[str, Any] = {
            "latitude": latitude,
            "longitude": longitude,
            "current_weather": "true",
        }
        if self._config.api_key:
            params["apikey"] = self._config.api_key
        logger.info(
            "Weather API request: url=%s params=%s",
            self._config.weather_url,
            params,
        )
        try:
            response = self._session.get(
                self._config.weather_url,
                params=params,
                timeout=self._config.timeout,
            )
            response.raise_for_status()
            logger.info(
                "Weather API success: status=%s lat=%s lon=%s",
                response.status_code,
                latitude,
                longitude,
            )
            return response.json()
        except requests.RequestException as exc:
            logger.error(
                "Weather API failed: lat=%s lon=%s error=%s",
                latitude,
                longitude,
                exc,
            )
            raise
    def resolve_location_name(self, latitude: float, longitude: float) -> str:
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "accept-language": "tr",
        }
        logger.info(
            "Geocoding API request: url=%s params=%s",
            self._config.geocoding_url,
            params,
        )
        try:
            response = self._session.get(
                self._config.geocoding_url,
                params=params,
                headers={"User-Agent": self._config.user_agent},
                timeout=self._config.timeout,
            )
            response.raise_for_status()
            location = format_location_from_geocode(
                response.json(), latitude, longitude
            )
            logger.info(
                "Geocoding API success: status=%s lat=%s lon=%s location=%s",
                response.status_code,
                latitude,
                longitude,
                location,
            )
            return location
        except requests.RequestException as exc:
            logger.error(
                "Geocoding API failed: lat=%s lon=%s error=%s",
                latitude,
                longitude,
                exc,
            )
        return f"{latitude:.4f}°, {longitude:.4f}°"
    def get_current_temperature(
        self, latitude: float, longitude: float
    ) -> tuple[str, float | None]:
        logger.info(
            "Fetching current temperature: lat=%s lon=%s", latitude, longitude
        )
        data = self.fetch_weather(latitude, longitude)
        location = self.resolve_location_name(latitude, longitude)
        temperature = extract_temperature(data)
        logger.info(
            "Temperature resolved: lat=%s lon=%s location=%s temperature=%s",
            latitude,
            longitude,
            location,
            temperature,
        )
        return location, temperature

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
            logger.error(
                "Temperature unavailable in CLI: lat=%s lon=%s location=%s",
                lat,
                lon,
                location,
            )
            report_user_error()
    except ValueError:
        logger.error("Invalid coordinate input from user")
        print("Geçerli bir sayı giriniz.")
    except requests.RequestException as exc:
        logger.error("Unhandled API error in CLI: %s", exc)
        report_user_error()