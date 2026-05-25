import requests
from flask import Flask, jsonify, request

from wheather import (
    WeatherService,
    get_user_error_message,
    load_app_settings,
    load_config_from_env,
    logger,
)

app_settings = load_app_settings()
app = Flask(__name__)
weather_service = WeatherService(config=load_config_from_env())


def _parse_coordinates() -> tuple[float, float]:
    lat_raw = request.args.get("lat")
    lon_raw = request.args.get("lon")
    if lat_raw is None or lon_raw is None:
        raise ValueError(
            "lat ve lon query parametreleri zorunludur. "
            "Örnek: /weather?lat=41.0082&lon=28.9784"
        )
    try:
        return float(lat_raw), float(lon_raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("lat ve lon geçerli sayılar olmalıdır") from exc


@app.get("/")
def index() -> tuple[dict, int]:
    return (
        jsonify(
            {
                "service": "weather",
                "usage": "/weather?lat=<latitude>&lon=<longitude>",
                "example": "/weather?lat=41.0082&lon=28.9784",
            }
        ),
        200,
    )


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
        return jsonify({"error": get_user_error_message()}), 502

    if temperature is None:
        logger.error(
            "Temperature unavailable via web: lat=%s lon=%s location=%s",
            latitude,
            longitude,
            location,
        )
        return jsonify({"error": get_user_error_message()}), 502

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
    app.run(host="0.0.0.0", port=app_settings.port)
