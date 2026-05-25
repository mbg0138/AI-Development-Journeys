import logging
import os
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

_PROJECT_DIR = Path(__file__).resolve().parent
_ENV_FILE = _PROJECT_DIR / ".env"
load_dotenv(_ENV_FILE)

LOG_FILE = _PROJECT_DIR / "app.log"
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


# Fallback defaults (mirror .env.example; overridden by environment / .env)
_FALLBACK_WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
_FALLBACK_GEOCODING_URL = "https://nominatim.openstreetmap.org/reverse"
_FALLBACK_USER_AGENT = "bobo-test-weather/1.0"
_FALLBACK_TIMEOUT = "10.0"
_FALLBACK_LATITUDE = "41.0082"
_FALLBACK_LONGITUDE = "28.9784"
_FALLBACK_PORT = "5000"


@dataclass(frozen=True)
class AppSettings:
    latitude: float
    longitude: float
    port: int


@dataclass(frozen=True)
class ApiConfig:
    weather_url: str = _FALLBACK_WEATHER_URL
    geocoding_url: str = _FALLBACK_GEOCODING_URL
    user_agent: str = _FALLBACK_USER_AGENT
    timeout: float = 10.0
    api_key: str | None = None


def _env_str(name: str, fallback: str) -> str:
    value = os.getenv(name)
    return fallback if value is None or value.strip() == "" else value.strip()


def _env_float(name: str, fallback: str) -> float:
    return float(_env_str(name, fallback))


def load_app_settings() -> AppSettings:
    return AppSettings(
        latitude=_env_float("WEATHER_LATITUDE", _FALLBACK_LATITUDE),
        longitude=_env_float("WEATHER_LONGITUDE", _FALLBACK_LONGITUDE),
        port=int(_env_str("PORT", _FALLBACK_PORT)),
    )


def load_config_from_env() -> ApiConfig:
    api_key = _env_str("API_KEY", "")
    user_agent = _env_str("NOMINATIM_USER_AGENT", _FALLBACK_USER_AGENT)
    if user_agent == _FALLBACK_USER_AGENT:
        logger.warning(
            "NOMINATIM_USER_AGENT is not set; using fallback. "
            "Set it in .env (see .env.example)."
        )
    return ApiConfig(
        weather_url=_env_str("WEATHER_API_URL", _FALLBACK_WEATHER_URL),
        geocoding_url=_env_str("GEOCODING_API_URL", _FALLBACK_GEOCODING_URL),
        user_agent=user_agent,
        timeout=_env_float("REQUEST_TIMEOUT", _FALLBACK_TIMEOUT),
        api_key=api_key or None,
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