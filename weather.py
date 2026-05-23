import requests

WEATHER_API_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_weather_data(lat: float, lon: float) -> dict:
    response = requests.get(
        WEATHER_API_URL,
        params={
            "latitude": lat,
            "longitude": lon,
            "current_weather": "true",
        },
    )
    response.raise_for_status()
    return response.json()


def extract_temperature(data: dict) -> float | None:
    return data.get("current_weather", {}).get("temperature")


def print_temperature(temperature: float | None) -> None:
    if temperature is not None:
        print(f"Anlık sıcaklık: {temperature}°C")
    else:
        print("Sıcaklık bilgisi alınamadı.")


def get_current_temperature(lat: float, lon: float) -> None:
    try:
        data = fetch_weather_data(lat, lon)
        print_temperature(extract_temperature(data))
    except requests.RequestException as e:
        print(f"API isteği sırasında hata oluştu: {e}")


def prompt_coordinates() -> tuple[float, float]:
    lat = float(input("Enlem (latitude) girin: "))
    lon = float(input("Boylam (longitude) girin: "))
    return lat, lon


if __name__ == "__main__":
    try:
        get_current_temperature(*prompt_coordinates())
    except ValueError:
        print("Geçerli bir sayı giriniz.")
