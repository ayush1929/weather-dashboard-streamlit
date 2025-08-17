import streamlit as st
import pandas as pd
import altair as alt
import requests, base64, mimetypes, uuid
from pathlib import Path
from urllib.parse import urlencode
from datetime import date, timedelta, datetime
from zoneinfo import ZoneInfo
import streamlit.components.v1 as components

st.set_page_config(page_title="Weather Trends — Live & Historical", layout="wide")
alt.data_transformers.disable_max_rows()

# ---------- City presets ----------
CITIES = {
    "Hamilton (ON)": (43.2557, -79.8711),
    "Toronto": (43.65107, -79.347015),
    "New York": (40.7128, -74.0060),
    "London": (51.5072, -0.1276),
    "Tokyo": (35.6762, 139.6503),
    "Sydney": (-33.8688, 151.2093),
    "Custom…": None,
}

COL = {"min":"#4C78A8","mean":"#FFFFFF","max":"#E45756","rain":"#1F77B4","snow":"#9FD0FF","wind":"#9E9E9E"}

BASE   = Path(__file__).resolve().parents[1]
P_DAILY= BASE/"data/processed/daily_weather.csv"
P_SAMP = BASE/"data/processed/sample_daily_weather.csv"
P_CSS  = BASE/"app/static/hero.css"
BG_DIR = BASE/"app/static/hero_bg"
JS_PATH= BASE/"app/static/hero.js"

# ---------- CSS ----------
def inject_css(path: Path) -> str:
    try:
        css = path.read_text(encoding="utf-8")
        st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)
        return css
    except Exception:
        return ""
CSS_TEXT = inject_css(P_CSS)

# ---------- assets ----------
def load_bg_map() -> dict:
    out = {}
    for name in ["sunny","cloudy","rainy","snowy","storm"]:
        p = (BG_DIR/f"{name}.png")
        if not p.exists():
            p = BG_DIR/f"{name}.jpg"
        if p.exists():
            mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
            b64  = base64.b64encode(p.read_bytes()).decode("ascii")
            out[name] = f"data:{mime};base64,{b64}"
    return out
BG_MAP = load_bg_map()

def load_js() -> str:
    try:
        return JS_PATH.read_text(encoding="utf-8")
    except Exception:
        return ""
HERO_JS = load_js()

# ---------- session helpers ----------
def set_data(df: pd.DataFrame, source: str):
    st.session_state["daily_df"] = df
    st.session_state["data_source"] = source
def get_data():
    return st.session_state.get("daily_df"), st.session_state.get("data_source")

# ---------- fetchers ----------
@st.cache_data(show_spinner=False)
def fetch_live_hourly(lat: float, lon: float, past_hours: int) -> pd.DataFrame:
    base = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "hourly": "temperature_2m,precipitation,wind_speed_10m,snowfall",
              "timezone": "auto", "past_hours": past_hours, "forecast_hours": 0}
    r = requests.get(f"{base}?{urlencode(params)}", timeout=45, headers={"User-Agent":"AyushPortfolio/1.0"})
    r.raise_for_status()
    h = r.json()["hourly"]
    df = pd.DataFrame({
        "time": pd.to_datetime(h["time"]),
        "temp_c": h["temperature_2m"],
        "precip_mm": h["precipitation"],
        "wind_kmh": h["wind_speed_10m"],
        "snowfall_cm": h.get("snowfall", [0]*len(h["time"])),
    })
    daily = (df.set_index("time").resample("D").agg(
        temp_mean_c=("temp_c","mean"), temp_min_c=("temp_c","min"), temp_max_c=("temp_c","max"),
        precip_sum_mm=("precip_mm","sum"), wind_mean_kmh=("wind_kmh","mean"),
        snowfall_sum_cm=("snowfall_cm","sum"),
    ).reset_index().rename(columns={"time":"date"}))
    return daily

@st.cache_data(show_spinner=False)
def fetch_historical_daily(lat: float, lon: float, start: date, end: date) -> pd.DataFrame:
    base = "https://archive-api.open-meteo.com/v1/archive"
    params = {"latitude": lat, "longitude": lon, "start_date": start.isoformat(), "end_date": end.isoformat(),
              "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,snowfall_sum,wind_speed_10m_mean",
              "timezone": "auto"}
    r = requests.get(f"{base}?{urlencode(params)}", timeout=60, headers={"User-Agent":"AyushPortfolio/1.0"})
    r.raise_for_status()
    d = r.json().get("daily", {})
    if not d: return pd.DataFrame()
    return pd.DataFrame({
        "date": pd.to_datetime(d["time"]),
        "temp_max_c": d.get("temperature_2m_max"),
        "temp_min_c": d.get("temperature_2m_min"),
        "temp_mean_c": d.get("temperature_2m_mean"),
        "precip_sum_mm": d.get("precipitation_sum"),
        "snowfall_sum_cm": d.get("snowfall_sum"),
        "wind_mean_kmh": d.get("wind_speed_10m_mean"),
    })

@st.cache_data(ttl=300, show_spinner=False)
def fetch_current_conditions(lat: float, lon: float):
    base = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": lat, "longitude": lon, "timezone": "auto",
              "current_weather": "true",
              "current": "temperature_2m,weather_code,wind_speed_10m,precipitation"}
    r = requests.get(f"{base}?{urlencode(params)}", timeout=30, headers={"User-Agent":"AyushPortfolio/1.0"})
    r.raise_for_status()
    j  = r.json()
    cw = j.get("current_weather") or {}
    cur= j.get("current") or {}
    temp = cw.get("temperature",    cur.get("temperature_2m"))
    wind = cw.get("windspeed",      cur.get("wind_speed_10m"))
    code = cw.get("weathercode",    cur.get("weather_code"))
    precip = cur.get("precipitation", 0.0)
    tz   = j.get("timezone","local")
    rain = {51,53,55,56,57,61,63,65,66,67,80,81,82}
    snow = {71,73,75,77,85,86}
    storm= {95,96,99}
    cloud= {1,2,3,45,48}
    if code in snow:  cond,emoji,cat="Snowy","❄️","snowy"
    elif code in rain:cond,emoji,cat="Rainy","🌧️","rainy"
    elif code in storm:cond,emoji,cat="Thunderstorm","⛈️","storm"
    elif code in cloud:cond,emoji,cat="Cloudy","☁️","cloudy"
    else:             cond,emoji,cat="Sunny","☀️","sunny"
    if temp is not None and temp <= 0: cond,emoji=f"Cold · {cond}","🥶"
    try:
        local_dt = datetime.now(ZoneInfo(tz))
    except Exception:
        local_dt = datetime.now()
    time_line = local_dt.strftime("%I:%M %p").lstrip("0")
    date_line = local_dt.strftime("%A, %b %d, %Y")
    return {"condition":cond,"emoji":emoji,"category":cat,
            "temp_c":temp,"wind_kmh":wind,"precip_mm":precip,
            "date_line":date_line,"time_line":time_line,"timezone":tz}

# ---------- transforms ----------
def add_flags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.month
    df["year"]  = df["date"].dt.year
    df["day"]   = df["date"].dt.day
    df["hot_day"]    = df["temp_max_c"] >= 30
    df["freeze_day"] = df["temp_min_c"] <= 0
    df["rain_day"]   = df["precip_sum_mm"].fillna(0) >= 1.0
    df["snowfall_sum_cm"] = df.get("snowfall_sum_cm", pd.Series(0, index=df.index)).fillna(0)
    df["snow_day"]   = df["snowfall_sum_cm"] >= 1.0
    return df

def auto_granularity(df: pd.DataFrame) -> str:
    span = (df["date"].max() - df["date"].min()).days + 1
    return "Monthly" if span > 800 else ("Weekly" if span > 120 else "Daily")

def resample_df(df: pd.DataFrame, granularity: str) -> pd.DataFrame:
    d = df.set_index("date")
    if granularity == "Daily":
        out = d.copy()
    elif granularity == "Weekly":
        out = d.resample("W").agg(
            temp_mean_c=("temp_mean_c","mean"),
            temp_min_c=("temp_min_c","mean"),
            temp_max_c=("temp_max_c","mean"),
            precip_sum_mm=("precip_sum_mm","sum"),
            snowfall_sum_cm=("snowfall_sum_cm","sum"),
            wind_mean_kmh=("wind_mean_kmh","mean"),
        )
    else:
        out = d.resample("MS").agg(
            temp_mean_c=("temp_mean_c","mean"),
            temp_min_c=("temp_min_c","mean"),
            temp_max_c=("temp_max_c","mean"),
            precip_sum_mm=("precip_sum_mm","sum"),
            snowfall_sum_cm=("snowfall_sum_cm","sum"),
            wind_mean_kmh=("wind_mean_kmh","mean"),
        )
    return out.reset_index()

def kpis_for_period(df: pd.DataFrame) -> dict:
    d = df.dropna(subset=["temp_mean_c"])
    if d.empty: return {}
    hot = d.loc[d["temp_mean_c"].idxmax()]
    cold= d.loc[d["temp_mean_c"].idxmin()]
    return {
        "avg_temp": float(d["temp_mean_c"].mean()),
        "avg_daily_rain": float(d["precip_sum_mm"].mean()),
        "avg_daily_snow": float(d["snowfall_sum_cm"].mean()),
        "total_rain": float(d["precip_sum_mm"].sum()),
        "total_snow": float(d["snowfall_sum_cm"].sum()),
        "hot_days": int(d["hot_day"].sum()),
        "rain_days": int(d["rain_day"].sum()),
        "snow_days": int(d["snow_day"].sum()),
        "freeze_days": int(d["freeze_day"].sum()),
        "avg_wind": float(d["wind_mean_kmh"].mean()),
        "hottest_date": hot["date"].date(), "hottest_temp": float(hot["temp_mean_c"]),
        "coldest_date": cold["date"].date(), "coldest_temp": float(cold["temp_mean_c"]),
    }

# ---------- charts ----------
def temp_chart(df: pd.DataFrame, title: str):
    folded = df[["date","temp_min_c","temp_mean_c","temp_max_c"]].melt("date", var_name="metric", value_name="value")
    color_scale = alt.Scale(domain=["temp_min_c","temp_mean_c","temp_max_c"], range=[COL["min"],COL["mean"],COL["max"]])
    base = alt.Chart(folded).mark_line().encode(
        x=alt.X("date:T", axis=alt.Axis(labelOverlap=True)),
        y=alt.Y("value:Q", title="°C"),
        color=alt.Color("metric:N", scale=color_scale, legend=alt.Legend(title=None, orient="top")),
        tooltip=[alt.Tooltip("date:T"), "metric:N", alt.Tooltip("value:Q", format=".1f")]
    ).properties(title=title, height=280)
    roll = df[["date","temp_mean_c"]].assign(smooth=df["temp_mean_c"].rolling(7, min_periods=3).mean())
    smooth = alt.Chart(roll).mark_line(strokeDash=[5,4], strokeWidth=2.5, color=COL["mean"]).encode(x="date:T", y="smooth:Q")
    return base + smooth

def bar_chart(df: pd.DataFrame, y_field: str, title: str, color: str):
    return alt.Chart(df).mark_bar(color=color).encode(
        x=alt.X("date:T", axis=alt.Axis(labelOverlap=True)),
        y=f"{y_field}:Q",
        tooltip=[alt.Tooltip("date:T"), alt.Tooltip(f"{y_field}:Q", format=".2f")]
    ).properties(title=title, height=180)

def line_chart(df: pd.DataFrame, y_field: str, title: str, color: str):
    return alt.Chart(df).mark_line(color=color).encode(
        x=alt.X("date:T", axis=alt.Axis(labelOverlap=True)),
        y=f"{y_field}:Q",
        tooltip=[alt.Tooltip("date:T"), alt.Tooltip(f"{y_field}:Q", format=".2f")]
    ).properties(title=title, height=180)

def month_overlay_chart(d: pd.DataFrame, month_num: int):
    m = d[d["month"] == month_num].copy()
    if m.empty: return alt.Chart(pd.DataFrame({"day":[1],"temp_mean_c":[0]})).mark_line()
    latest_year = int(m["year"].max())
    m["day"] = m["date"].dt.day
    base = alt.Chart(m).mark_line(opacity=0.25).encode(
        x=alt.X("day:O", title="Day of month"),
        y=alt.Y("temp_mean_c:Q", title="°C"),
        color=alt.Color("year:N", legend=None),
        tooltip=["year:N","day:O", alt.Tooltip("temp_mean_c:Q", format=".1f")]
    ).properties(height=260)
    highlight = alt.Chart(m[m["year"]==latest_year]).mark_line(strokeWidth=3, color=COL["max"]).encode(x="day:O", y="temp_mean_c:Q")
    return base + highlight

# ------------------- export (dashboard without Today) -------------------
def build_dashboard_html_no_hero(kpi: dict, charts: list, granularity: str, css_text: str, title: str) -> bytes:
    chart_divs, scripts = [], []
    for i, ch in enumerate(charts, 1):
        if ch is None:
            continue
        spec = ch.to_json()
        chart_divs.append(f'<div id="c{i}" class="card"></div>')
        scripts.append(f'vegaEmbed("#c{i}", {spec}).catch(console.error);')
    charts_html = "\n".join(chart_divs) + f"\n<script>{''.join(scripts)}</script>"

    page_css = f"""
    <style>
      body{{background:#0E1117;color:#e8e8e8;font-family:system-ui,Segoe UI,Roboto,Helvetica,Arial;margin:0}}
      .wrap{{max-width:1200px;margin:24px auto;padding:0 16px}}
      .title{{font-size:28px;font-weight:900;margin-bottom:6px}}
      .sub{{opacity:.75;margin-bottom:12px}}
      .kpis{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:8px 0 6px}}
      .k{{border:1px solid #ffffff14;border-radius:10px;padding:12px}}
      .k .h{{opacity:.85;font-weight:600;font-size:13px;margin-bottom:6px}}
      .k .v{{font-size:24px;font-weight:800}}
      {css_text}
    </style>
    """

    kpi_html = f"""
    <div class="kpis">
      <div class="k"><div class="h">Avg Temp (°C)</div><div class="v">{kpi['avg_temp']:.1f}</div></div>
      <div class="k"><div class="h">Avg Daily Rain (mm)</div><div class="v">{kpi['avg_daily_rain']:.2f}</div></div>
      <div class="k"><div class="h">Avg Daily Snow (cm)</div><div class="v">{kpi['avg_daily_snow']:.2f}</div></div>
      <div class="k"><div class="h">Hot Days (≥30°C)</div><div class="v">{kpi['hot_days']}</div></div>
      <div class="k"><div class="h">Rainy Days (≥1mm)</div><div class="v">{kpi['rain_days']}</div></div>
      <div class="k"><div class="h">Freeze Days (≤0°C)</div><div class="v">{kpi['freeze_days']}</div></div>
      <div class="k"><div class="h">Hottest Day</div><div class="v">{kpi['hottest_temp']:.1f} °C · {kpi['hottest_date']}</div></div>
      <div class="k"><div class="h">Coldest Day</div><div class="v">{kpi['coldest_temp']:.1f} °C · {kpi['coldest_date']}</div></div>
    </div>
    """

    html = f"""<!doctype html><meta charset="utf-8">
    <title>{title}</title>
    <link rel="preconnect" href="https://cdn.jsdelivr.net">
    <script src="https://cdn.jsdelivr.net/npm/vega@5"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-lite@5"></script>
    <script src="https://cdn.jsdelivr.net/npm/vega-embed@6"></script>
    {page_css}
    <div class="wrap">
      <div class="title">{title}</div>
      <div class="sub">Charts at {granularity} resolution</div>
      {kpi_html}
      {charts_html}
    </div>
    """
    return html.encode("utf-8")

# ---------- hero component ----------
import uuid
import streamlit.components.v1 as components

def render_today_hero(city_label: str, cur: dict, *, height_px: int = 320):
    cat  = (cur.get("category") or "sunny").lower()
    tz   = cur.get("timezone","local")
    wind = int(cur["wind_kmh"]) if cur.get("wind_kmh") is not None else 0
    temp = f'{cur["temp_c"]:.1f} °C' if cur.get("temp_c") is not None else "—"
    emoji= cur.get("emoji","")
    cond = cur.get("condition","")
    date_line = cur.get("date_line","")
    time_line = cur.get("time_line","")
    precip    = float(cur.get("precip_mm", 0.0) or 0.0)
    bg_uri    = BG_MAP.get(cat, "")

    hero_id = f"hero-{uuid.uuid4().hex[:8]}"

    html = f"""<!doctype html>
<meta charset="utf-8">
<style>
  :root{{ color-scheme:dark; }}
  html,body{{ margin:0; padding:0; background:transparent; }}
  .wrap{{
    position:relative; width:100%; height:{height_px}px;
    border-radius:16px; overflow:hidden; background:#0f141b;
    box-shadow:0 0 0 1px rgba(255,255,255,.07) inset;
  }}
  .hero-canvas{{ position:absolute; inset:0; width:100%; height:100%; display:block }}
  .shade{{ position:absolute; inset:0;
           background:linear-gradient(180deg, rgba(0,0,0,.10), rgba(0,0,0,.28) 58%, rgba(0,0,0,.38));
           pointer-events:none; }}

  /* Grid overlay that fits to container height (via --h set in JS) */
  .inner{{
    position:relative; z-index:1;
    display:grid;
    grid-template-columns: 1.4fr auto;
    align-items:center;
    gap:16px;
    height:100%;
    padding:16px 20px;
    color:#fff; text-shadow:0 1px 0 rgba(0,0,0,.25);
  }}
  .left{{ display:flex; flex-direction:column; justify-content:center; min-width:0; }}
  .hero-title{{
    margin:0;
    font-weight:900;
    font-size: clamp(20px, calc(var(--h, {height_px}px) * 0.16), 38px);
    line-height:1.08;
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  }}
  .hero-sub{{
    margin-top:6px;
    font-weight:800;
    opacity:.95;
    font-size: clamp(12px, calc(var(--h, {height_px}px) * 0.075), 18px);
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  }}
  .bullet{{ opacity:.7; margin:0 .5ch }}
  .hero-cond{{
    margin-top:6px;
    font-weight:800;
    font-size: clamp(13px, calc(var(--h, {height_px}px) * 0.085), 19px);
    white-space:nowrap; overflow:hidden; text-overflow:ellipsis;
  }}
  .emoji{{ font-size: 1.1em; vertical-align:-3px; }}
  .hero-now{{
    font-weight:900;
    text-align:right;
    white-space:nowrap;
    font-size: clamp(26px, calc(var(--h, {height_px}px) * 0.32), 64px);
  }}

  @media (max-width: 680px){{
    .inner{{ grid-template-columns: 1fr; align-items:flex-start; }}
    .hero-now{{ text-align:left; }}
  }}
</style>

<div id="{hero_id}" class="wrap"
     data-cat="{cat}" data-precip="{precip}" data-wind="{wind}"
     data-bg="{bg_uri}">
  <canvas class="hero-canvas"></canvas>
  <div class="shade"></div>
  <div class="inner">
    <div class="left">
      <h1 class="hero-title">Today in {city_label}</h1>
      <div class="hero-sub">{date_line} · {time_line}
        <span class="bullet">•</span> wind {wind} km/h
        <span class="bullet">•</span> ({tz})
      </div>
      <div class="hero-cond"><span class="emoji">{emoji}</span> {cond}</div>
    </div>
    <div class="hero-now">{temp}</div>
  </div>
</div>

<script>{HERO_JS}</script>
<script>initHero(document.getElementById("{hero_id}"));</script>
"""
    components.html(html, height=height_px + 14, scrolling=False)

# ---------- geocoding (city name -> lat/lon) ----------
@st.cache_data(ttl=24*3600, show_spinner=False)
def geocode_city(name: str, count: int = 5) -> list[dict]:
    """Return up to `count` matches for a city name using Open-Meteo’s geocoding API."""
    try:
        url = "https://geocoding-api.open-meteo.com/v1/search"
        params = {"name": name, "count": count, "language": "en", "format": "json"}
        r = requests.get(url, params=params, timeout=20, headers={"User-Agent":"AyushPortfolio/1.0"})
        r.raise_for_status()
        results = (r.json() or {}).get("results") or []
        out = []
        for it in results:
            lat, lon = it.get("latitude"), it.get("longitude")
            if lat is None or lon is None: 
                continue
            label = ", ".join(x for x in [
                it.get("name",""),
                it.get("admin1") or it.get("admin2") or "",
                it.get("country_code") or it.get("country") or "",
            ] if x)
            out.append({"label": label, "lat": float(lat), "lon": float(lon)})
        return out
    except Exception:
        return []


# ------------------- Sidebar -------------------
with st.sidebar:
    st.header("Location")

    # Keep a growing list of user-added cities in session (persists during the session)
    dynamic = st.session_state.setdefault("dynamic_cities", {})
    all_cities = {**CITIES, **dynamic}

    loc_mode = st.radio("How do you want to choose?", ["Search by name", "Pick preset"], index=0)

    city_label = None
    lat = lon = None

    if loc_mode == "Search by name":
        query = st.text_input("City name", value="", placeholder="e.g., Paris · Tokyo · Mumbai · New York")
        if query.strip():
            matches = geocode_city(query.strip(), count=7)
            if matches:
                choice = st.selectbox(
                    "Matches",
                    [m["label"] for m in matches],
                    index=0,
                    help="Pick the exact city if multiple results appear."
                )
                sel = next(m for m in matches if m["label"] == choice)
                city_label, lat, lon = sel["label"], sel["lat"], sel["lon"]
                # auto-add to the list for this session
                st.session_state["dynamic_cities"][city_label] = (lat, lon)
                st.caption(f"Using **{city_label}** · {lat:.4f}, {lon:.4f}")
            else:
                st.warning("No matches found. Try a different spelling, or pick a preset below.")
        # If user hasn't typed yet or no match, provide a gentle preset fallback
        if lat is None:
            preset = st.selectbox("Presets", list(all_cities.keys()), index=0)
            lat, lon = all_cities[preset]; city_label = preset

    else:
        preset = st.selectbox("City", list(all_cities.keys()), index=0)
        lat, lon = all_cities[preset]; city_label = preset

    st.header("Data mode")
    mode = st.radio("Choose", ["Live (past days)", "Historical (date range)"], index=1)
    if mode == "Live (past days)":
        days = st.slider("Past days", 1, 31, 7)
        load_clicked = st.button("Load / Refresh")
    else:
        today = date.today(); max_end = today - timedelta(days=5)
        default_start = max_end - timedelta(days=365)
        start_date, end_date = st.date_input(
            "Historical range",
            value=(default_start, max_end),
            min_value=date(1940,1,1),
            max_value=max_end
        )
        if isinstance(start_date, (list, tuple)): start_date = start_date[0]
        if isinstance(end_date, (list, tuple)):   end_date = end_date[1]
        if start_date > end_date: start_date, end_date = end_date, start_date
        load_clicked = st.button("Load / Refresh")

# ---------- Load / persist ----------
daily, source = get_data()
if load_clicked:
    if mode == "Live (past days)":
        new = fetch_live_hourly(lat, lon, days*24)
        new = add_flags(new)
        set_data(new, f"Live: {city_label} — {new['date'].min().date()} → {new['date'].max().date()}")
    else:
        new = fetch_historical_daily(lat, lon, start_date, end_date)
        if new.empty: st.warning("No data returned; try changing the range.")
        else:
            new = add_flags(new)
            set_data(new, f"Historical: {city_label} — {new['date'].min().date()} → {new['date'].max().date()}")
    daily, source = get_data()

if daily is None:
    if P_DAILY.exists():
        daily = add_flags(pd.read_csv(P_DAILY, parse_dates=["date"]))
        set_data(daily, f"Local file: {P_DAILY.name}")
    elif P_SAMP.exists():
        daily = add_flags(pd.read_csv(P_SAMP, parse_dates=["date"]))
        set_data(daily, f"Local file: {P_SAMP.name}")

# ---------- Today hero ----------
def _fallback_cur(tz="local"):
    now = datetime.now()
    return {"condition":"—","emoji":"","category":"sunny","temp_c":None,"wind_kmh":None,"precip_mm":0.0,
            "date_line": now.strftime("%A, %b %d, %Y"),
            "time_line": now.strftime("%I:%M %p").lstrip("0"),
            "timezone": tz}
try:
    cur = fetch_current_conditions(lat, lon) or _fallback_cur()
except Exception:
    cur = _fallback_cur()

render_today_hero(city_label, cur, height_px=320)  

# ---------- Granularity ----------
with st.sidebar:
    st.header("3) Chart granularity")
    auto_g = auto_granularity(daily)
    g = st.radio("Resolution", ["Auto", "Daily", "Weekly", "Monthly"], index=0)
    granularity = auto_g if g == "Auto" else g
    st.caption(f"Auto picked: **{auto_g}** based on your date span.")

agg = resample_df(daily, granularity)
chart_temp = temp_chart(agg, f"Temperature — {granularity}")
chart_prec = bar_chart(agg, "precip_sum_mm", f"Precipitation — {granularity}", COL["rain"])
chart_snow = bar_chart(agg, "snowfall_sum_cm", f"Snowfall — {granularity}", COL["snow"]) if (daily["snowfall_sum_cm"].sum() or 0) > 0 else None
chart_wind = line_chart(agg, "wind_mean_kmh", f"Wind Speed — {granularity}", COL["wind"])

# ---------- Tabs ----------
tab_overview, tab_month, tab_compare, tab_climatology = st.tabs(["Overview","Month view","Compare (YoY)","Climatology"])

with tab_overview:
    k = kpis_for_period(daily)

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Avg Temp (°C)", f"{k['avg_temp']:.1f}")
    c2.metric("Avg Daily Rain (mm)", f"{k['avg_daily_rain']:.2f}")
    c3.metric("Avg Daily Snow (cm)", f"{k['avg_daily_snow']:.2f}")
    c4.metric("Hot Days (≥30°C)", str(k["hot_days"]))
    c5.metric("Rainy Days (≥1mm)", str(k["rain_days"]))
    c6.metric("Freeze Days (≤0°C)", str(k["freeze_days"]))
    d1,d2 = st.columns(2)
    d1.metric("Hottest Day", f"{k['hottest_temp']:.1f} °C", str(k['hottest_date']))
    d2.metric("Coldest Day", f"{k['coldest_temp']:.1f} °C", str(k['coldest_date']))

    st.altair_chart(chart_temp, use_container_width=True)
    cA, cB = st.columns(2)
    cA.altair_chart(chart_prec, use_container_width=True)
    if chart_snow is not None:
        cB.altair_chart(chart_snow, use_container_width=True)
    else:
        cB.info("No snow during this period.")
    st.altair_chart(chart_wind, use_container_width=True)

    # ---- Always-visible downloads (right column) ----
    dl_left, dl_right = st.columns([7,3], gap="large")
    with dl_right:
        st.markdown('<div class="actions-right">', unsafe_allow_html=True)
        st.download_button(
            "Download daily CSV",
            data=daily.to_csv(index=False).encode("utf-8"),
            file_name=f"{city_label.replace(' ','_').lower()}_daily.csv",
            mime="text/csv",
            use_container_width=True,
        )
        title = f"Weather Dashboard — {city_label} ({daily['date'].min().date()} → {daily['date'].max().date()})"
        html_bytes = build_dashboard_html_no_hero(
            kpi=k,
            charts=[chart_temp, chart_prec, chart_snow, chart_wind],
            granularity=granularity,
            css_text=CSS_TEXT,
            title=title
        )
        st.download_button(
            "Download dashboard (HTML)",
            data=html_bytes,
            file_name=f"{city_label.replace(' ','_').lower()}_{granularity.lower()}_dashboard.html",
            mime="text/html",
            use_container_width=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

with tab_month:
    months_present = sorted(daily["month"].unique().tolist())
    month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    options = [f"{m:02d} — {month_map[m]}" for m in months_present] if months_present else ["—"]
    sel = st.selectbox("Which month?", options)
    month_num = int(sel.split(" — ")[0]) if " — " in sel else months_present[0]
    st.caption("Lines show the selected month across all years; latest year highlighted in red.")
    st.altair_chart(month_overlay_chart(daily, month_num), use_container_width=True)
    st.altair_chart(bar_chart(daily[daily['month']==month_num], "precip_sum_mm", f"Precipitation — {month_map.get(month_num,'')}", COL['rain']), use_container_width=True)

with tab_compare:
    if daily["year"].nunique() < 2:
        st.info("Load multiple years in Historical mode to compare year-over-year.")
    else:
        months_present = sorted(daily["month"].unique())
        month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
        sel = st.selectbox("Compare month", [f"{m:02d} — {month_map[m]}" for m in months_present])
        month_num = int(sel.split(" — ")[0])
        m = daily[daily["month"] == month_num].copy()
        yearly = (m.groupby("year")
                    .agg(temp_mean=("temp_mean_c","mean"),
                         rain_sum=("precip_sum_mm","sum"),
                         snow_sum=("snowfall_sum_cm","sum"))
                    .reset_index())
        c1,c2,c3 = st.columns(3)
        c1.altair_chart(alt.Chart(yearly).mark_bar(color=COL["max"]).encode(x="year:O", y="temp_mean:Q"), use_container_width=True)
        c2.altair_chart(alt.Chart(yearly).mark_bar(color=COL["rain"]).encode(x="year:O", y="rain_sum:Q"), use_container_width=True)
        if yearly["snow_sum"].sum() > 0:
            c3.altair_chart(alt.Chart(yearly).mark_bar(color=COL["snow"]).encode(x="year:O", y="snow_sum:Q"), use_container_width=True)
        else:
            c3.info("No snow in the chosen month across the selected years.")

with tab_climatology:
    s = (daily.groupby(daily["month"])
           .agg(temp_min=("temp_min_c","mean"),
                temp_mean=("temp_mean_c","mean"),
                temp_max=("temp_max_c","mean"),
                rain=("precip_sum_mm","mean"),
                snow=("snowfall_sum_cm","mean"),
                wind=("wind_mean_kmh","mean"))
           .reset_index(names="month"))
    s["month_name"] = pd.Categorical(
        s["month"].map({1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}),
        categories=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], ordered=True
    )
    folded = s.melt("month_name", ["temp_min","temp_mean","temp_max"], "metric", "value")
    color_scale = alt.Scale(domain=["temp_min","temp_mean","temp_max"], range=[COL["min"],COL["mean"],COL["max"]])
    ctemp = alt.Chart(folded).mark_line().encode(
        x=alt.X("month_name:N", title="Month"), y=alt.Y("value:Q", title="Temperature (°C)"),
        color=alt.Color("metric:N", scale=color_scale, legend=alt.Legend(title=None, orient="top")),
    ).properties(title="Typical Monthly Temperatures", height=280)
    cprec = alt.Chart(s).mark_bar(color=COL["rain"]).encode(x="month_name:N", y="rain:Q").properties(height=180, title="Typical Monthly Rain")
    if s["snow"].sum() > 0:
        csnow = alt.Chart(s).mark_bar(color=COL["snow"]).encode(x="month_name:N", y="snow:Q").properties(height=180, title="Typical Monthly Snow")
        st.altair_chart(ctemp, use_container_width=True)
        a,b = st.columns(2); a.altair_chart(cprec, use_container_width=True); b.altair_chart(csnow, use_container_width=True)
    else:
        st.altair_chart(ctemp, use_container_width=True)
        st.altair_chart(cprec, use_container_width=True)
        st.info("No snow during this period.")

with st.expander("About data", expanded=False):
    st.caption(st.session_state.get("data_source") or "")
    st.caption("Live: Open-Meteo Forecast API (recent hours). Historical: Open-Meteo ERA5/ERA5-Land (daily).")
