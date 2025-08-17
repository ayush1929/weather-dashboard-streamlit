# src/fetch_weather.py
import argparse, json, pathlib, requests
from datetime import datetime
from urllib.parse import urlencode

def build_url(lat: float, lon: float, hours: int) -> str:
    base = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,precipitation,wind_speed_10m",
        "timezone": "auto",
        "past_hours": hours,     # how many past hours to pull
        "forecast_hours": 0      # we only want history for this demo
    }
    return f"{base}?{urlencode(params)}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--hours", type=int, default=72)
    ap.add_argument("--city", type=str, default="City")
    args = ap.parse_args()

    url = build_url(args.lat, args.lon, args.hours)
    print("Fetching:", url)

    r = requests.get(url, timeout=30, headers={"User-Agent": "AyushPortfolio/1.0"})
    r.raise_for_status()
    data = r.json()

    out_dir = pathlib.Path("data/raw")
    out_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"open_meteo_{args.city}_{ts}.json"
    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Saved", out_path)

if __name__ == "__main__":
    main()
