# Weather Dashboard (Streamlit)

Live & historical weather dashboard with an Apple-style animated “Today” header, high-quality background images, and Altair charts.  
Data from **Open-Meteo** (live & archive). Desktop-first, mobile friendly.  
Includes one-click **CSV** export and **standalone HTML dashboard** (charts only).

## Live demo
- App (Streamlit Cloud): <!-- add when deployed -->  
- Embedded on my site: <!-- add your Pages URL -->

## Features
- 🖼️ Apple-like animated hero (rain/snow/storm/sunny/cloudy)
- 🌍 Type a **city name** (geocoding) — no lat/lon needed
- 📈 Altair charts: temps, precip, snow, wind
- 📥 Downloads: daily CSV and dashboard HTML (without Today banner)
- ⚙️ Desktop-first layout; responsive on mobile

## Tech
- **Python**, **Streamlit**, **Altair**, **Pandas**
- API: **Open-Meteo** Forecast & Archive + Geocoding

## Run locally
```bash
pip install -r requirements.txt
streamlit run app/WeatherDashboard.py
