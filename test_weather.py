from unittest.mock import MagicMock, Mock

import pytest
import requests

from wheather import (
    ApiConfig,
    WeatherService,
    extract_temperature,
    format_location_from_geocode,
)

LAT = 41.0082
LON = 28.9784

WEATHER_FIXTURE: dict = {
    "current_weather": {"temperature": 18.5, "windspeed": 10.0},
}

GEOCODE_FIXTURE: dict = {
    "address": {"city": "Istanbul", "country": "Turkey"},
}


@pytest.fixture
def api_config() -> ApiConfig:
    return ApiConfig(
        weather_url="https://test.example/forecast",
        geocoding_url="https://test.example/reverse",
        user_agent="test-weather/1.0",
        timeout=10.0,
    )


@pytest.fixture
def mock_session() -> MagicMock:
    return MagicMock(spec=requests.Session)


@pytest.fixture
def service(mock_session: MagicMock, api_config: ApiConfig) -> WeatherService:
    return WeatherService(config=api_config, session=mock_session)


def _ok_response(json_data: dict) -> Mock:
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = json_data
    return response


def _error_response(status_code: int = 404) -> Mock:
    response = Mock()
    response.status_code = status_code
    response.raise_for_status.side_effect = requests.HTTPError(
        f"{status_code} Client Error",
        response=response,
    )
    return response


class TestExtractTemperature:
    def test_returns_temperature_when_present(self) -> None:
        assert extract_temperature(WEATHER_FIXTURE) == 18.5

    def test_returns_none_when_missing(self) -> None:
        assert extract_temperature({}) is None
        assert extract_temperature({"current_weather": {}}) is None


class TestFormatLocationFromGeocode:
    def test_city_and_country(self) -> None:
        result = format_location_from_geocode(GEOCODE_FIXTURE, LAT, LON)
        assert result == "Istanbul, Turkey"

    def test_coordinate_fallback(self) -> None:
        result = format_location_from_geocode({}, LAT, LON)
        assert result == f"{LAT:.4f}°, {LON:.4f}°"


class TestWeatherServiceFetchWeather:
    def test_returns_json_on_success(
        self,
        service: WeatherService,
        mock_session: MagicMock,
        api_config: ApiConfig,
    ) -> None:
        mock_session.get.return_value = _ok_response(WEATHER_FIXTURE)

        data = service.fetch_weather(LAT, LON)

        assert data == WEATHER_FIXTURE
        mock_session.get.assert_called_once_with(
            api_config.weather_url,
            params={
                "latitude": LAT,
                "longitude": LON,
                "current_weather": "true",
            },
            timeout=api_config.timeout,
        )

    def test_raises_on_http_error(
        self, service: WeatherService, mock_session: MagicMock
    ) -> None:
        mock_session.get.return_value = _error_response(404)

        with pytest.raises(requests.HTTPError):
            service.fetch_weather(LAT, LON)


class TestWeatherServiceResolveLocationName:
    def test_returns_formatted_city(
        self, service: WeatherService, mock_session: MagicMock
    ) -> None:
        mock_session.get.return_value = _ok_response(GEOCODE_FIXTURE)

        location = service.resolve_location_name(LAT, LON)

        assert location == "Istanbul, Turkey"

    def test_falls_back_to_coordinates_on_api_error(
        self, service: WeatherService, mock_session: MagicMock
    ) -> None:
        mock_session.get.return_value = _error_response(503)

        location = service.resolve_location_name(LAT, LON)

        assert location == f"{LAT:.4f}°, {LON:.4f}°"


class TestWeatherServiceGetCurrentTemperature:
    def test_returns_location_and_temperature(
        self, service: WeatherService, mock_session: MagicMock
    ) -> None:
        mock_session.get.side_effect = [
            _ok_response(WEATHER_FIXTURE),
            _ok_response(GEOCODE_FIXTURE),
        ]

        location, temperature = service.get_current_temperature(LAT, LON)

        assert location == "Istanbul, Turkey"
        assert temperature == 18.5
        assert mock_session.get.call_count == 2

    def test_raises_when_weather_api_returns_404(
        self, service: WeatherService, mock_session: MagicMock
    ) -> None:
        mock_session.get.return_value = _error_response(404)

        with pytest.raises(requests.HTTPError):
            service.get_current_temperature(LAT, LON)

        mock_session.get.assert_called_once()

    def test_uses_coordinate_fallback_when_geocode_fails(
        self, service: WeatherService, mock_session: MagicMock
    ) -> None:
        mock_session.get.side_effect = [
            _ok_response(WEATHER_FIXTURE),
            _error_response(503),
        ]

        location, temperature = service.get_current_temperature(LAT, LON)

        assert location == f"{LAT:.4f}°, {LON:.4f}°"
        assert temperature == 18.5
        assert mock_session.get.call_count == 2

    def test_returns_none_temperature_when_weather_data_incomplete(
        self, service: WeatherService, mock_session: MagicMock
    ) -> None:
        mock_session.get.side_effect = [
            _ok_response({}),
            _ok_response(GEOCODE_FIXTURE),
        ]

        location, temperature = service.get_current_temperature(LAT, LON)

        assert location == "Istanbul, Turkey"
        assert temperature is None
    
