# Weather Dashboard (Streamlit)

Interactive weather dashboard with an animated “Today” header, live conditions, and historical trends.  
Built with **Streamlit**, **Altair**, and **Open-Meteo** APIs. Desktop-first layout that scales well on mobile.

<p align="center">
  <img alt="Weather Dashboard hero" src="app/static/hero_bg/sunny.png" width="640">
</p>

---

## Live demo
- App: https://weather-dashboard-ayush1929.streamlit.app/
- Embedded on my site: https://ayush1929.github.io/weather/

---

## Features
- Animated “Today” banner with background visuals matched to current conditions (sunny / cloudy / rainy / snowy / storm)
- Search by **city name** (geocoding) — no latitude/longitude required
- Historical charts (daily / weekly / monthly): min / mean / max temperature, precipitation, snowfall, wind
- KPI cards (hottest/coldest day, averages, totals, counts)
- One-click **CSV** export of the daily data in view
- One-click **standalone HTML** export (charts only) for sharing or offline viewing
- Desktop-first design with responsive behavior for smaller screens

---

## Tech stack
- Python, Streamlit
- Altair (charts)
- Pandas (transformations)
- Open-Meteo Forecast & Archive APIs + Geocoding (no API keys needed)

---

## Project structure

app/
  WeatherDashboard.py        # main Streamlit app
  static/
    hero.css                 # styles for hero + small utilities
    hero.js                  # canvas animation + fit-text logic
    hero_bg/                 # background images (sunny/cloudy/rainy/snowy/storm)
data/
  processed/
    sample_daily_weather.csv # optional small sample for first-load charts
requirements.txt
README.md
LICENSE

---

## Getting started (local)

1) Create & activate a virtual environment (optional, recommended)

    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS / Linux:
    source .venv/bin/activate

2) Install dependencies

    pip install -r requirements.txt

3) Run the app

    streamlit run app/WeatherDashboard.py

Open the local URL Streamlit prints (usually http://localhost:8501).

---

## Deploy (Streamlit Community Cloud)

1. Push this repo to GitHub.
2. Go to https://share.streamlit.io → New app  
   Repo: ayush1929/weather-dashboard-streamlit  
   Branch: main  
   Main file: app/WeatherDashboard.py
3. Deploy and copy the app URL (use it in the “Live demo” section above and for embedding).

**Embed example (GitHub Pages / Jekyll page)**

    <iframe
      src="https://REPLACE_WITH_STREAMLIT_APP_URL/?embed=true"
      width="100%" height="1100"
      style="border:1px solid #1f2937; border-radius:14px;"
      frameborder="0" loading="lazy" allow="fullscreen">
    </iframe>

---

## Data sources

- Live & hourly: Open-Meteo Forecast API (https://open-meteo.com/)
- Historical daily: Open-Meteo Archive API (ERA5/ERA5-Land) (https://open-meteo.com/)
- Geocoding: Open-Meteo Geocoding API (https://open-meteo.com/)

No API keys required. Requests are anonymous and rate-limited by Open-Meteo.

---

## Usage notes

- City search: type a city name; the app fetches geocoding results and remembers your selection during the session
- Modes:
  - Live (past days) resamples recent hourly data into daily aggregates
  - Historical (date range) fetches daily values directly from the archive
- Granularity: Auto / Daily / Weekly / Monthly (Auto picks based on date span)
- Downloads:
  - CSV — exports the current daily dataset
  - HTML — single-file dashboard with all charts (excludes the “Today” banner)

---

## Configuration & customization

- Hero visuals & sizing
  - Images: app/static/hero_bg/*.png
  - Height/layout: see render_today_hero in WeatherDashboard.py
  - Text auto-fit: controlled in app/static/hero.js (the constant “k” adjusts how much of the hero height the text occupies)
- Styling
  - Global/hero tweaks in app/static/hero.css
  - Minimal inline CSS in the hero HTML where necessary
- Sample data
  - If data/processed/sample_daily_weather.csv exists, it’s used on first load so charts render immediately even before fetching

---

## Requirements

    streamlit>=1.36
    pandas>=2.1
    altair>=5.2
    requests>=2.31

---

## Troubleshooting

- Blank page in embed: add ?embed=true to the Streamlit app URL inside the iframe
- Large image assets: if any PNG exceeds GitHub’s size limits, use Git LFS:

      git lfs install
      git lfs track "app/static/hero_bg/*.png"
      git add .gitattributes
      git commit -m "Track hero images with LFS"

---

## License
This project is licensed under the MIT License. See #LICENSE for details.

---

## Acknowledgments
Weather data and geocoding by Open-Meteo (https://open-meteo.com/).