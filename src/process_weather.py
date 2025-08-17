# src/process_weather.py
import json, glob, pathlib
import pandas as pd

RAW_DIR = pathlib.Path("data/raw")
OUT_DIR = pathlib.Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def tidy_from_json(path: str) -> pd.DataFrame:
    """Load one Open-Meteo JSON file and return a tidy hourly DataFrame."""
    with open(path, "r", encoding="utf-8") as f:
        j = json.load(f)
    h = j["hourly"]
    df = pd.DataFrame({
        "time": pd.to_datetime(h["time"]),
        "temp_c": h["temperature_2m"],
        "precip_mm": h["precipitation"],
        "wind_kmh": h["wind_speed_10m"],
    })
    df["source_lat"] = j["latitude"]
    df["source_lon"] = j["longitude"]
    return df

def main():
    paths = sorted(glob.glob(str(RAW_DIR / "open_meteo_*.json")))
    if not paths:
        print("No raw JSON found in data/raw. Run fetch_weather.py first.")
        return

    # Combine all raw files (so you can fetch multiple times and append)
    frames = [tidy_from_json(p) for p in paths]
    df = pd.concat(frames, ignore_index=True).drop_duplicates(subset=["time"])
    df.sort_values("time", inplace=True)

    # Save hourly data
    hourly_path = OUT_DIR / "hourly_weather.csv"
    df.to_csv(hourly_path, index=False)

    # Aggregate to daily metrics the app uses
    daily = (
        df.set_index("time")
          .resample("D")
          .agg(
              temp_mean_c=("temp_c", "mean"),
              temp_min_c=("temp_c", "min"),
              temp_max_c=("temp_c", "max"),
              precip_sum_mm=("precip_mm", "sum"),
              wind_mean_kmh=("wind_kmh", "mean"),
          )
          .reset_index()
          .rename(columns={"time": "date"})
    )
    daily_path = OUT_DIR / "daily_weather.csv"
    daily.to_csv(daily_path, index=False)

    print(f"Wrote {hourly_path}")
    print(f"Wrote {daily_path}")

if __name__ == "__main__":
    main()
