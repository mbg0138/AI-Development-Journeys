import os

import requests
from flask import Flask, jsonify, request

from wheather import (
    USER_FRIENDLY_ERROR_MSG,
    WeatherService,
    load_config_from_env,
    logger,
)

DEFAULT_LATITUDE = 41.0082
DEFAULT_LONGITUDE = 28.9784

app = Flask(__name__)
weather_service = WeatherService(config=load_config_from_env())


def _parse_coordinates() -> tuple[float, float]:
    try:
        latitude = float(
            request.args.get("lat", os.getenv("WEATHER_LATITUDE", DEFAULT_LATITUDE))
        )
        longitude = float(
            request.args.get("lon", os.getenv("WEATHER_LONGITUDE", DEFAULT_LONGITUDE))
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("lat and lon must be valid numbers") from exc
    return latitude, longitude


@app.get("/")
def health() -> tuple[dict[str, str], int]:
    return jsonify({"status": "ok", "service": "weather"}), 200


@app.get("/weather")
def get_weather() -> tuple[dict, int]:
    try:
        latitude, longitude = _parse_coordinates()
    except ValueError as exc:
        logger.error("Invalid query parameters: %s", exc)
        return jsonify({"error": "lat ve lon geçerli sayılar olmalıdır."}), 400

    try:
        location, temperature = weather_service.get_current_temperature(
            latitude, longitude
        )
    except requests.RequestException as exc:
        logger.error(
            "Weather API error via web: lat=%s lon=%s error=%s",
            latitude,
            longitude,
            exc,
        )
        return jsonify({"error": USER_FRIENDLY_ERROR_MSG}), 502

    if temperature is None:
        logger.error(
            "Temperature unavailable via web: lat=%s lon=%s location=%s",
            latitude,
            longitude,
            location,
        )
        return jsonify({"error": USER_FRIENDLY_ERROR_MSG}), 502

    return (
        jsonify(
            {
                "location": location,
                "temperature_c": temperature,
                "latitude": latitude,
                "longitude": longitude,
            }
        ),
        200,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)
