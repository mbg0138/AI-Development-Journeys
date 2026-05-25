# Deployment Guide (Render Web Service)

## Architecture

| File | Purpose |
|------|---------|
| [main.py](main.py) | Flask web API (`GET /`, `GET /weather`) |
| [wheather.py](wheather.py) | `WeatherService` + `API_KEY` from environment |
| [requirements.txt](requirements.txt) | Production deps (Flask, gunicorn, requests) |
| [requirements-dev.txt](requirements-dev.txt) | Local dev + pytest |
| [render.yaml](render.yaml) | Render Blueprint (Web Service) |
| [Procfile](Procfile) | `gunicorn main:app` |

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `API_KEY` | No | Weather API key (`os.environ.get('API_KEY')`) |
| `WEATHER_LATITUDE` | No | Default latitude for `/weather` |
| `WEATHER_LONGITUDE` | No | Default longitude for `/weather` |
| `NOMINATIM_USER_AGENT` | Recommended | Nominatim contact string |
| `PORT` | Auto on Render | Set by platform |

## Render setup

1. Push repo to GitHub.
2. **New → Web Service** (or Blueprint with [render.yaml](render.yaml)).
3. **Build Command:** `pip install -r requirements.txt`
4. **Start Command:** `gunicorn main:app --bind 0.0.0.0:$PORT`
5. **Environment** → add `API_KEY` as secret (if needed).
6. Test: `https://<your-app>.onrender.com/weather?lat=41.0082&lon=28.9784`

## API endpoints

- `GET /` — health check
- `GET /weather?lat=41.0082&lon=28.9784` — location + temperature JSON

Example response:

```json
{
  "location": "İstanbul, Türkiye",
  "temperature_c": 16.6,
  "latitude": 41.0082,
  "longitude": 28.9784
}
```

## Local run

```bash
pip install -r requirements.txt
set API_KEY=your-key-if-needed
python main.py
```

Then open: http://127.0.0.1:5000/weather

Production-style local run:

```bash
gunicorn main:app --bind 0.0.0.0:5000
```

## Tests

```bash
pip install -r requirements-dev.txt
pytest test_weather.py -v
```

Interactive CLI is still available: `python wheather.py`
