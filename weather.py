import requests

def get_current_temperature(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current_weather=true"
    )
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        temperature = data.get("current_weather", {}).get("temperature")
        if temperature is not None:
            print(f"Anlık sıcaklık: {temperature}°C")
        else:
            print("Sıcaklık bilgisi alınamadı.")
    except requests.RequestException as e:
        print(f"API isteği sırasında hata oluştu: {e}")

if __name__ == "__main__":
    try:
        lat = float(input("Enlem (latitude) girin: "))
        lon = float(input("Boylam (longitude) girin: "))
        get_current_temperature(lat, lon)
    except ValueError:
        print("Geçerli bir sayı giriniz.")