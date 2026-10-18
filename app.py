
import math
from datetime import datetime, timezone

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

# ==========================================================
# HEATSHIELD AI — Scientific Climate Intelligence Dashboard
# Public Open-Meteo endpoints | No API key required
# ==========================================================

st.set_page_config(
    page_title="HeatShield AI",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 25

HOURLY_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "wind_speed_10m",
    "uv_index",
    "cloud_cover",
]

# -------------------- PROFESSIONAL LIGHT THEME --------------------

st.markdown("""
<style>
:root {
    --ink: #14263D;
    --muted: #52657B;
    --teal: #087E8B;
    --border: #D5E0EB;
    --panel: #FFFFFF;
    --canvas: #F2F6FA;
}

.stApp {
    background: var(--canvas);
    color: var(--ink);
    font-family: Arial, Helvetica, sans-serif;
}

[data-testid="stHeader"] {
    background: rgba(242,246,250,.97);
}

[data-testid="stSidebar"] {
    background: #FFFFFF;
    border-right: 1px solid var(--border);
}

[data-testid="stSidebar"] * {
    color: #20344B;
}

.block-container {
    max-width: 1500px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

h1, h2, h3, h4 {
    color: #14263D !important;
    font-weight: 750 !important;
    letter-spacing: -.02em;
}

p, li, label {
    color: #263A50;
    line-height: 1.55;
}

[data-testid="stCaptionContainer"] {
    color: #52657B !important;
}

.hs-hero {
    background: linear-gradient(115deg, #FFFFFF, #E5F4F5);
    border: 1px solid #C9DCE7;
    border-left: 7px solid #087E8B;
    border-radius: 15px;
    padding: 28px 30px;
    margin-bottom: 22px;
    box-shadow: 0 5px 18px rgba(20,38,61,.05);
}

.hs-eyebrow {
    color: #087E8B;
    font-size: 12px;
    letter-spacing: 2px;
    font-weight: 800;
}

.hs-hero h1 {
    color: #14263D !important;
    font-size: clamp(28px, 3vw, 42px) !important;
    margin: 9px 0;
}

.hs-hero p {
    color: #344A60 !important;
    font-size: 16px;
    line-height: 1.65;
    margin-bottom: 0;
}

.hs-card {
    background: #FFFFFF;
    border: 1px solid #D5E0EB;
    border-radius: 12px;
    padding: 17px;
    margin-bottom: 12px;
}

.hs-note {
    background: #FFFFFF;
    border: 1px solid #D5E0EB;
    border-radius: 10px;
    padding: 14px;
    color: #344A60;
    line-height: 1.6;
    font-size: 14px;
}

[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #D5E0EB;
    border-radius: 12px;
    padding: 16px;
    box-shadow: 0 3px 10px rgba(20,38,61,.035);
}

[data-testid="stMetricLabel"] {
    color: #52657B !important;
    font-size: 13px !important;
}

[data-testid="stMetricValue"] {
    color: #14263D !important;
    font-size: clamp(22px, 2vw, 30px) !important;
    font-weight: 800 !important;
}

[data-testid="stMetricDelta"] {
    font-weight: 650;
}

.stButton > button,
.stDownloadButton > button {
    background: #087E8B;
    color: #FFFFFF !important;
    border: 1px solid #087E8B;
    border-radius: 9px;
    min-height: 43px;
    font-weight: 750;
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    background: #066570;
    border-color: #066570;
}

button[data-baseweb="tab"] {
    color: #344A60 !important;
    font-weight: 700;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: #087E8B !important;
    border-bottom-color: #087E8B !important;
}

[data-baseweb="input"],
[data-baseweb="select"] > div,
[data-baseweb="textarea"] {
    background: #FFFFFF !important;
    border-color: #B9C9D9 !important;
}

input, textarea {
    color: #172033 !important;
}

[data-testid="stDataFrame"] {
    border: 1px solid #D5E0EB;
    border-radius: 10px;
    background: #FFFFFF;
}

[data-testid="stAlert"] {
    border-radius: 10px;
}

hr {
    border-color: #D5E0EB;
}

@media (max-width: 768px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }
    .hs-hero {
        padding: 20px;
    }
}
</style>
""", unsafe_allow_html=True)


# -------------------- API FUNCTIONS --------------------

@st.cache_data(ttl=1800, show_spinner=False)
def search_places(query):
    response = requests.get(
        GEO_URL,
        params={
            "name": query.strip(),
            "count": 8,
            "language": "en",
            "format": "json",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("results", []) or []


@st.cache_data(ttl=900, show_spinner=False)
def get_forecast(latitude, longitude, timezone_name="auto"):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "timezone": timezone_name,
        "forecast_days": 7,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,precipitation,"
            "wind_speed_10m,uv_index,cloud_cover"
        ),
        "hourly": ",".join(HOURLY_FIELDS),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "apparent_temperature_max,precipitation_probability_max,"
            "precipitation_sum,uv_index_max,wind_speed_10m_max"
        ),
    }

    response = requests.get(
        FORECAST_URL,
        params=params,
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    result = response.json()

    if "hourly" not in result or "daily" not in result:
        raise ValueError("Forecast data was incomplete.")

    return result


# -------------------- DATA PROCESSING --------------------

def place_name(place):
    parts = [place.get("name", "Unknown")]
    if place.get("admin1") and place["admin1"] != parts[0]:
        parts.append(place["admin1"])
    if place.get("country"):
        parts.append(place["country"])
    return ", ".join(parts)


def weather_description(code):
    try:
        code = int(code)
    except (ValueError, TypeError):
        return "Unknown"

    codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Fog",
        48: "Rime fog",
        51: "Light drizzle",
        53: "Drizzle",
        55: "Dense drizzle",
        56: "Freezing drizzle",
        57: "Freezing drizzle",
        61: "Light rain",
        63: "Moderate rain",
        65: "Heavy rain",
        66: "Freezing rain",
        67: "Heavy freezing rain",
        71: "Light snow",
        73: "Snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Rain showers",
        81: "Rain showers",
        82: "Heavy rain showers",
        85: "Snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with hail",
        99: "Thunderstorm with hail",
    }
    return codes.get(code, "Unknown conditions")


def score_band(score):
    if pd.isna(score):
        return "Unavailable"
    if score < 25:
        return "Lower screening level"
    if score < 50:
        return "Moderate screening level"
    if score < 75:
        return "Elevated screening level"
    return "High screening level"


def number(value, digits=1, suffix=""):
    try:
        value = float(value)
        if not math.isfinite(value):
            return "N/A"
        return f"{value:.{digits}f}{suffix}"
    except (ValueError, TypeError):
        return "N/A"


def hourly_frame(weather):
    frame = pd.DataFrame(weather["hourly"])
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")

    for column in frame.columns:
        if column != "time":
            frame[column] = pd.to_numeric(
                frame[column], errors="coerce"
            )

    apparent = frame["apparent_temperature"].fillna(
        frame["temperature_2m"]
    )
    humidity = frame["relative_humidity_2m"].fillna(50)
    uv = frame["uv_index"].fillna(0)
    wind = frame["wind_speed_10m"].fillna(10)

    # Transparent heuristic, not an official heat-stress index.
    thermal = ((apparent - 24) / 16 * 65).clip(0, 65)
    humidity_part = ((humidity - 40) / 60 * 20).clip(0, 20)
    uv_part = (uv / 11 * 10).clip(0, 10)
    wind_part = ((12 - wind) / 12 * 5).clip(0, 5)

    frame["heat_score"] = (
        thermal + humidity_part + uv_part + wind_part
    ).clip(0, 100).round(0)

    frame["screening_band"] = frame["heat_score"].apply(score_band)
    return frame


def daily_frame(weather):
    frame = pd.DataFrame(weather["daily"])
    frame["time"] = pd.to_datetime(frame["time"], errors="coerce")

    for column in frame.columns:
        if column != "time":
            frame[column] = pd.to_numeric(
                frame[column], errors="coerce"
            )

    frame["conditions"] = frame["weather_code"].apply(
        weather_description
    )
    return frame


def styled_chart(fig, height=370):
    fig.update_layout(
        template="plotly_white",
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        font=dict(
            family="Arial, sans-serif",
            color="#263A50",
            size=13,
        ),
        title_font=dict(color="#14263D", size=19),
        height=height,
        margin=dict(l=15, r=15, t=60, b=15),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            font_color="#14263D",
            bordercolor="#B9C9D9",
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)",
            font=dict(color="#263A50"),
        ),
    )
    fig.update_xaxes(
        gridcolor="#E2E8F0",
        linecolor="#CBD5E1",
        tickfont=dict(color="#344A60"),
        title_font=dict(color="#344A60"),
    )
    fig.update_yaxes(
        gridcolor="#E2E8F0",
        linecolor="#CBD5E1",
        tickfont=dict(color="#344A60"),
        title_font=dict(color="#344A60"),
    )
    return fig


def report_text(label, current, hourly, daily, threshold):
    current_score = (
        hourly["heat_score"].iloc[0]
        if not hourly.empty else float("nan")
    )
    alerts = hourly[hourly["heat_score"] >= threshold]

    lines = [
        "HEATSHIELD AI — CLIMATE SCREENING REPORT",
        "=" * 48,
        f"Location: {label}",
        "Generated UTC: " + datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%d %H:%M"),
        "Source: Open-Meteo public forecast API",
        "",
        "CURRENT CONDITIONS",
        f"Air temperature: {number(current.get('temperature_2m'), 1, ' °C')}",
        f"Feels like: {number(current.get('apparent_temperature'), 1, ' °C')}",
        f"Humidity: {number(current.get('relative_humidity_2m'), 0, '%')}",
        f"Wind speed: {number(current.get('wind_speed_10m'), 1, ' km/h')}",
        f"UV index: {number(current.get('uv_index'), 1)}",
        "",
        "SCREENING ESTIMATE",
        f"Score: {number(current_score, 0)} / 100",
        f"User threshold: {threshold}/100",
        f"Forecast hours above threshold: {len(alerts)}",
        "",
        "LIMITATIONS",
        "The screening score is a heuristic, not a validated medical index or official warning.",
        "Forecast grid values are not street-level sensor measurements.",
        "Use local official weather and public-health guidance for safety decisions.",
        "",
        "7-DAY FORECAST",
    ]

    for _, row in daily.iterrows():
        day = (
            row["time"].strftime("%Y-%m-%d")
            if pd.notna(row["time"]) else "Unknown"
        )
        lines.append(
            f"{day}: high {number(row.get('temperature_2m_max'), 1, ' °C')}, "
            f"low {number(row.get('temperature_2m_min'), 1, ' °C')}, "
            f"feels-like high {number(row.get('apparent_temperature_max'), 1, ' °C')}, "
            f"{row.get('conditions', 'Unknown')}"
        )

    return "\n".join(lines)


# -------------------- SESSION STATE --------------------

defaults = {
    "query": "Sialkot",
    "weather": None,
    "place": None,
    "hourly": None,
    "daily": None,
    "loaded_query": None,
    "load_error": None,
    "comparisons": [],
    "comparison_errors": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -------------------- HEADER --------------------

st.markdown("""
<div class="hs-hero">
    <div class="hs-eyebrow">CLIMATE INTELLIGENCE • RESEARCH PLATFORM</div>
    <h1>🌡️ HeatShield AI</h1>
    <p>
      Explore weather forecasts, compare locations, inspect heat-screening
      alerts and export climate summaries in a clear scientific workspace.
    </p>
</div>
""", unsafe_allow_html=True)


# -------------------- SIDEBAR --------------------

with st.sidebar:
    st.markdown("## Control centre")

    query = st.text_input(
        "Search city or place",
        value=st.session_state.query,
        placeholder="e.g. Sialkot, Lahore, Karachi",
    )

    threshold = st.slider(
        "Screening alert threshold",
        min_value=10,
        max_value=95,
        value=60,
        step=5,
        help="Threshold for this app's heuristic score, not an official warning level.",
    )

    st.markdown("---")
    st.markdown("### Hotspot comparison")
    compare_text = st.text_area(
        "Cities (one per line)",
        value="Lahore\nKarachi\nIslamabad",
        height=115,
    )

    refresh = st.button(
        "↻ Refresh forecast",
        use_container_width=True,
    )

    st.markdown("---")
    st.caption("DATA SOURCE")
    st.caption("Open-Meteo public forecast and geocoding APIs.")
    st.caption("No API key is required for these public endpoints.")
    st.caption(
        "The heat score is a screening estimate, not a validated medical index."
    )


# -------------------- LOAD FORECAST --------------------

if query.strip():
    should_load = (
        refresh
        or st.session_state.weather is None
        or st.session_state.loaded_query != query.strip().lower()
    )

    if should_load:
        try:
            with st.spinner("Loading location and forecast data…"):
                places = search_places(query.strip())

                if not places:
                    raise ValueError(
                        "Place not found. Try a larger city or check spelling."
                    )

                place = places[0]
                weather = get_forecast(
                    float(place["latitude"]),
                    float(place["longitude"]),
                    place.get("timezone", "auto") or "auto",
                )

                st.session_state.place = place
                st.session_state.weather = weather
                st.session_state.hourly = hourly_frame(weather)
                st.session_state.daily = daily_frame(weather)
                st.session_state.loaded_query = query.strip().lower()
                st.session_state.load_error = None

        except requests.RequestException as exc:
            st.session_state.load_error = (
                f"Network/API request failed: {exc}"
            )
        except (ValueError, KeyError, TypeError) as exc:
            st.session_state.load_error = str(exc)

if st.session_state.load_error:
    st.error(st.session_state.load_error)

if st.session_state.weather is None:
    st.info("Enter a city in the sidebar to load its forecast.")
    st.stop()


weather = st.session_state.weather
place = st.session_state.place
hourly = st.session_state.hourly
daily = st.session_state.daily
current = weather.get("current", {})
location = place_name(place)

current_score = (
    float(hourly["heat_score"].iloc[0])
    if not hourly.empty else float("nan")
)
alert_hours = hourly[hourly["heat_score"] >= threshold]

st.markdown(f"### 📍 {location}")
st.caption(
    f"Timezone: {weather.get('timezone', 'Provider local time')} · "
    f"Coordinates: {float(place['latitude']):.3f}, "
    f"{float(place['longitude']):.3f}"
)


# -------------------- KPI CARDS --------------------

m1, m2, m3, m4, m5 = st.columns(5)

m1.metric(
    "Air temperature",
    number(current.get("temperature_2m"), 1, " °C"),
)
m2.metric(
    "Feels like",
    number(current.get("apparent_temperature"), 1, " °C"),
)
m3.metric(
    "Humidity",
    number(current.get("relative_humidity_2m"), 0, "%"),
)
m4.metric(
    "UV index",
    number(current.get("uv_index"), 1),
)
m5.metric(
    "Heat screening score",
    number(current_score, 0, "/100"),
)

if pd.notna(current_score) and current_score >= threshold:
    st.warning(
        f"Screening threshold reached: {current_score:.0f}/100. "
        "Check official local heat guidance."
    )
else:
    st.info(
        "The current screening estimate is below your chosen threshold. "
        "This does not guarantee that conditions are safe."
    )


# -------------------- DASHBOARD TABS --------------------

overview, forecast_tab, hotspots, alerts, reports, methodology = st.tabs([
    "Overview",
    "Forecast",
    "Hotspot comparison",
    "Alerts",
    "Reports & export",
    "Methodology",
])


# -------------------- OVERVIEW --------------------

with overview:
    st.markdown("## Heat outlook")

    left, right = st.columns([1.5, 1])

    with left:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=hourly["time"],
            y=hourly["temperature_2m"],
            name="Air temperature",
            mode="lines",
            line=dict(color="#087E8B", width=3),
        ))

        fig.add_trace(go.Scatter(
            x=hourly["time"],
            y=hourly["apparent_temperature"],
            name="Feels like",
            mode="lines",
            line=dict(color="#D97706", width=3, dash="dot"),
        ))

        fig.update_layout(
            title="Air temperature vs apparent temperature",
            xaxis_title="Local time",
            yaxis_title="Temperature (°C)",
            hovermode="x unified",
        )

        st.plotly_chart(
            styled_chart(fig, 390),
            use_container_width=True,
        )

    with right:
        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=hourly["time"],
            y=hourly["heat_score"],
            name="Screening score",
            mode="lines",
            line=dict(color="#B45309", width=3),
            fill="tozeroy",
            fillcolor="rgba(217,119,6,0.12)",
        ))

        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="#B91C1C",
            annotation_text="Selected threshold",
        )

        fig.update_layout(
            title="Heat screening estimate",
            xaxis_title="Local time",
            yaxis_title="Score (0–100)",
            yaxis_range=[0, 100],
        )

        st.plotly_chart(
            styled_chart(fig, 390),
            use_container_width=True,
        )

    st.markdown("## 7-day forecast")

    daily_table = daily.copy()
    daily_table["Date"] = daily_table["time"].dt.strftime("%a, %d %b")

    daily_table = daily_table.rename(columns={
        "temperature_2m_max": "High °C",
        "temperature_2m_min": "Low °C",
        "apparent_temperature_max": "Feels-like high °C",
        "precipitation_probability_max": "Rain chance %",
        "uv_index_max": "Max UV",
        "wind_speed_10m_max": "Max wind km/h",
        "conditions": "Conditions",
    })

    display_cols = [
        "Date",
        "High °C",
        "Low °C",
        "Feels-like high °C",
        "Rain chance %",
        "Max UV",
        "Max wind km/h",
        "Conditions",
    ]

    st.dataframe(
        daily_table[display_cols].round(1),
        use_container_width=True,
        hide_index=True,
    )


# -------------------- FORECAST EXPLORER --------------------

with forecast_tab:
    st.markdown("## Forecast explorer")

    options = {
        "Apparent temperature (°C)": ("apparent_temperature", "°C", "#D97706"),
        "Air temperature (°C)": ("temperature_2m", "°C", "#087E8B"),
        "Relative humidity (%)": ("relative_humidity_2m", "%", "#2563EB"),
        "Rain probability (%)": ("precipitation_probability", "%", "#4F46E5"),
        "Wind speed (km/h)": ("wind_speed_10m", "km/h", "#0F766E"),
        "UV index": ("uv_index", "Index", "#B45309"),
        "Cloud cover (%)": ("cloud_cover", "%", "#64748B"),
        "Heat screening score": ("heat_score", "Score / 100", "#B45309"),
    }

    selected_metric = st.selectbox(
        "Forecast variable",
        list(options.keys()),
    )

    field, unit, color = options[selected_metric]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=hourly["time"],
        y=hourly[field],
        mode="lines",
        name=selected_metric,
        line=dict(color=color, width=3),
    ))

    if field == "heat_score":
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="#B91C1C",
            annotation_text="Selected threshold",
        )
        fig.update_yaxes(range=[0, 100])

    fig.update_layout(
        title=selected_metric,
        xaxis_title="Local time",
        yaxis_title=unit,
        hovermode="x unified",
    )

    st.plotly_chart(
        styled_chart(fig, 440),
        use_container_width=True,
    )

    st.markdown("### Hourly forecast records")

    hourly_table = hourly.copy()
    hourly_table["time"] = hourly_table["time"].dt.strftime(
        "%Y-%m-%d %H:%M"
    )

    st.dataframe(
        hourly_table,
        use_container_width=True,
        hide_index=True,
    )


# -------------------- HOTSPOT COMPARISON --------------------

with hotspots:
    st.markdown("## Location comparison")

    st.markdown("""
    <div class="hs-note">
    Compare forecast conditions at different geocoded locations.
    This is a comparison of forecast values, not direct measurement of
    urban heat islands or street-level surface temperatures.
    </div>
    """, unsafe_allow_html=True)

    if st.button("Run location comparison", type="primary"):
        names = []
        for raw in compare_text.splitlines():
            name = raw.strip()
            if name and name.casefold() not in [
                existing.casefold() for existing in names
            ]:
                names.append(name)

        names = names[:8]
        results = []
        errors = []

        if not names:
            st.warning("Enter at least one city in the sidebar.")
        else:
            progress = st.progress(0)

            for index, name in enumerate(names):
                try:
                    matches = search_places(name)

                    if not matches:
                        errors.append(f"{name}: no matching place found.")
                    else:
                        loc = matches[0]
                        fc = get_forecast(
                            float(loc["latitude"]),
                            float(loc["longitude"]),
                            loc.get("timezone", "auto") or "auto",
                        )

                        hf = hourly_frame(fc)
                        cur = fc.get("current", {})

                        score = (
                            float(hf["heat_score"].iloc[0])
                            if not hf.empty else float("nan")
                        )

                        results.append({
                            "Location": place_name(loc),
                            "Latitude": float(loc["latitude"]),
                            "Longitude": float(loc["longitude"]),
                            "Air temp °C": cur.get("temperature_2m"),
                            "Feels like °C": cur.get("apparent_temperature"),
                            "Humidity %": cur.get("relative_humidity_2m"),
                            "Wind km/h": cur.get("wind_speed_10m"),
                            "UV index": cur.get("uv_index"),
                            "Screening score": score,
                            "Screening band": score_band(score),
                        })

                except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                    errors.append(f"{name}: {exc}")

                progress.progress((index + 1) / len(names))

            st.session_state.comparisons = results
            st.session_state.comparison_errors = errors
            progress.empty()

    results = st.session_state.comparisons
    errors = st.session_state.comparison_errors

    if errors:
        with st.expander(f"Locations not loaded: {len(errors)}"):
            for error in errors:
                st.write("• " + error)

    if results:
        comparison_df = pd.DataFrame(results).sort_values(
            "Screening score",
            ascending=False,
            na_position="last",
        )

        st.markdown("### Comparison ranking")

        st.dataframe(
            comparison_df.round(2),
            use_container_width=True,
            hide_index=True,
        )

        fig = px.bar(
            comparison_df,
            x="Screening score",
            y="Location",
            orientation="h",
            color="Screening score",
            color_continuous_scale=[
                "#A7DAD5",
                "#F6C56F",
                "#C2413B",
            ],
            range_color=[0, 100],
            title="Current forecast screening comparison",
            hover_data=[
                "Air temp °C",
                "Feels like °C",
                "Humidity %",
                "UV index",
            ],
        )

        fig.update_layout(
            xaxis_title="Screening score / 100",
            yaxis_title="",
            yaxis={"categoryorder": "total ascending"},
        )

        st.plotly_chart(
            styled_chart(fig, max(350, 65 * len(comparison_df))),
            use_container_width=True,
        )

        map_fig = px.scatter_geo(
            comparison_df,
            lat="Latitude",
            lon="Longitude",
            color="Screening score",
            size="Screening score",
            hover_name="Location",
            hover_data=[
                "Air temp °C",
                "Feels like °C",
                "Screening band",
            ],
            color_continuous_scale=[
                "#A7DAD5",
                "#F6C56F",
                "#C2413B",
            ],
            range_color=[0, 100],
            title="Geographic comparison",
        )

        map_fig.update_geos(
            showland=True,
            landcolor="#F1F5F9",
            showocean=True,
            oceancolor="#EAF3FA",
            showcountries=True,
            countrycolor="#B9C9D9",
        )

        st.plotly_chart(
            styled_chart(map_fig, 430),
            use_container_width=True,
        )

        st.download_button(
            "Download comparison CSV",
            data=comparison_df.to_csv(index=False).encode("utf-8"),
            file_name="heatshield_comparison.csv",
            mime="text/csv",
        )
    else:
        st.info("Click 'Run location comparison' to generate the ranking and map.")


# -------------------- ALERTS --------------------

with alerts:
    st.markdown("## Forecast screening alerts")

    st.caption(
        "These are app-generated threshold alerts, not official weather warnings."
    )

    c1, c2, c3 = st.columns(3)

    c1.metric("Your threshold", f"{threshold}/100")
    c2.metric("Hours meeting threshold", len(alert_hours))
    c3.metric(
        "Highest forecast score",
        number(hourly["heat_score"].max(), 0, "/100"),
    )

    if not alert_hours.empty:
        st.warning(
            "Some forecast hours meet or exceed your selected screening threshold."
        )

        alert_table = alert_hours[[
            "time",
            "temperature_2m",
            "apparent_temperature",
            "relative_humidity_2m",
            "uv_index",
            "wind_speed_10m",
            "heat_score",
            "screening_band",
        ]].copy()

        alert_table["time"] = alert_table["time"].dt.strftime(
            "%Y-%m-%d %H:%M"
        )

        st.dataframe(
            alert_table,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "Download alert hours CSV",
            data=alert_table.to_csv(index=False).encode("utf-8"),
            file_name="heatshield_alert_hours.csv",
            mime="text/csv",
        )
    else:
        st.success(
            "No forecast hours meet your selected threshold. "
            "This does not guarantee that conditions are safe."
        )

    st.markdown("""
    <div class="hs-note">
    Alerts are calculated from the loaded forecast when the dashboard runs.
    No background monitoring, SMS, email or push notifications are configured.
    Follow official local weather and public-health guidance.
    </div>
    """, unsafe_allow_html=True)


# -------------------- REPORTS & EXPORT --------------------

with reports:
    st.markdown("## Reports & data export")

    report = report_text(
        location,
        current,
        hourly,
        daily,
        threshold,
    )

    st.download_button(
        "Download climate report (.txt)",
        data=report.encode("utf-8"),
        file_name="heatshield_report.txt",
        mime="text/plain",
        type="primary",
        use_container_width=True,
    )

    c1, c2 = st.columns(2)

    hourly_export = hourly.copy()
    daily_export = daily.copy()

    hourly_export["time"] = hourly_export["time"].astype(str)
    daily_export["time"] = daily_export["time"].astype(str)

    with c1:
        st.download_button(
            "Download hourly forecast CSV",
            data=hourly_export.to_csv(index=False).encode("utf-8"),
            file_name="heatshield_hourly.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with c2:
        st.download_button(
            "Download daily forecast CSV",
            data=daily_export.to_csv(index=False).encode("utf-8"),
            file_name="heatshield_daily.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with st.expander("Preview report"):
        st.code(report, language="text")


# -------------------- METHODOLOGY --------------------

with methodology:
    st.markdown("## Methodology & limitations")

    st.markdown("""
    **Weather provider:** Open-Meteo public geocoding and forecast endpoints.

    **Forecast variables:** Air temperature, apparent temperature, relative
    humidity, precipitation, precipitation probability, wind speed, UV index
    and cloud cover where available.

    **Heat screening score:** A simple heuristic derived from apparent
    temperature, humidity, UV and wind. It is scaled from 0 to 100 for
    dashboard screening. It is not a validated physiological heat-stress
    measure and is not the probability of illness.

    **Hotspot comparison:** Compares forecast conditions at selected locations.
    It does not directly measure urban heat islands or land-surface temperature.
    Validated sensors or suitable satellite observations would be needed for
    those analyses.

    **Alerts:** Threshold alerts are displayed in this session only. They are
    not official warnings and are not sent to the user outside the app.

    **Privacy:** Place names and coordinates are sent to the public weather
    provider to obtain geocoding and forecast data.
    """)

    st.markdown("### Loaded location metadata")

    st.json({
        "name": place.get("name"),
        "region": place.get("admin1"),
        "country": place.get("country"),
        "latitude": place.get("latitude"),
        "longitude": place.get("longitude"),
        "timezone": weather.get("timezone"),
        "elevation_m": weather.get("elevation"),
    })


# -------------------- FOOTER --------------------

st.divider()

st.markdown("""
<div class="hs-note">
<strong>HeatShield AI</strong> — Climate information and forecast screening.
Not an official meteorological service, medical device, or emergency alert system.
</div>
""", unsafe_allow_html=True)
