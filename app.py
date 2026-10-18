
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
import pycountry
from datetime import datetime, timezone

st.set_page_config(
    page_title="HeatShield AI | Global Climate",
    page_icon="🌍",
    layout="wide",
)

GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 25

# -------------------- LIGHT SCIENTIFIC THEME --------------------

st.markdown("""
<style>
.stApp {background:#F2F6FA;color:#14263D}
[data-testid="stHeader"] {background:#F2F6FA}
[data-testid="stSidebar"] {background:#FFFFFF;border-right:1px solid #D5E0EB}
.block-container {max-width:1500px;padding-top:1.5rem}
h1,h2,h3,h4 {color:#14263D!important;font-weight:750!important}
p,li,label {color:#263A50;line-height:1.55}
[data-testid="stMetric"] {
    background:#FFFFFF;border:1px solid #D5E0EB;
    border-radius:12px;padding:16px
}
[data-testid="stMetricLabel"] {color:#52657B!important}
[data-testid="stMetricValue"] {color:#14263D!important;font-weight:800}
.stButton>button,.stDownloadButton>button {
    background:#087E8B;color:white!important;border:1px solid #087E8B;
    border-radius:8px;min-height:42px;font-weight:700
}
.stButton>button:hover,.stDownloadButton>button:hover {
    background:#066570;color:white!important
}
.hs-hero {
    background:linear-gradient(110deg,#FFFFFF,#E5F4F5);
    border:1px solid #C9DCE7;border-left:7px solid #087E8B;
    border-radius:15px;padding:25px;margin-bottom:20px
}
.hs-hero h1 {font-size:clamp(28px,3vw,42px)!important}
.hs-muted {color:#52657B;font-size:14px;line-height:1.6}
[data-testid="stDataFrame"] {background:#FFFFFF;border-radius:10px}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hs-hero">
  <h1>🌍 HeatShield AI</h1>
  <p>GLOBAL CLIMATE INTELLIGENCE & HEAT SCREENING</p>
  <div class="hs-muted">
    Worldwide location search · Current weather · 7-day forecast ·
    City comparison · Downloadable reports
  </div>
</div>
""", unsafe_allow_html=True)

# -------------------- COUNTRIES: WORLDWIDE --------------------

countries = sorted(
    [(c.name, c.alpha_2) for c in pycountry.countries],
    key=lambda item: item[0].casefold(),
)

country_names = ["All countries"] + [name for name, _ in countries]
country_codes = {name: code for name, code in countries}

@st.cache_data(ttl=1800, show_spinner=False)
def search_locations(city, country_code):
    params = {
        "name": city.strip(),
        "count": 100,
        "language": "en",
        "format": "json",
    }
    if country_code:
        params["countryCode"] = country_code

    response = requests.get(GEO_URL, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json().get("results", []) or []

@st.cache_data(ttl=600, show_spinner=False)
def get_weather(lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "timezone": "auto",
        "forecast_days": 7,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,precipitation,"
            "wind_speed_10m,uv_index,cloud_cover"
        ),
        "hourly": (
            "temperature_2m,apparent_temperature,"
            "relative_humidity_2m,precipitation_probability,"
            "precipitation,wind_speed_10m,uv_index,cloud_cover"
        ),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "apparent_temperature_max,precipitation_probability_max,"
            "precipitation_sum,uv_index_max,wind_speed_10m_max"
        ),
    }
    response = requests.get(WEATHER_URL, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    data = response.json()
    if "current" not in data or "hourly" not in data:
        raise ValueError("Weather provider returned incomplete data.")
    return data

def location_label(place):
    parts = [place.get("name", "Unknown")]
    for key in ("admin1", "country"):
        value = place.get(key)
        if value and value not in parts:
            parts.append(value)
    return ", ".join(parts)

def heat_screening_score(hourly):
    # Heuristic for dashboard screening, not an official heat index.
    apparent = pd.to_numeric(
        hourly["apparent_temperature"], errors="coerce"
    ).fillna(pd.to_numeric(hourly["temperature_2m"], errors="coerce"))
    humidity = pd.to_numeric(
        hourly["relative_humidity_2m"], errors="coerce"
    ).fillna(50)
    uv = pd.to_numeric(
        hourly["uv_index"], errors="coerce"
    ).fillna(0)
    wind = pd.to_numeric(
        hourly["wind_speed_10m"], errors="coerce"
    ).fillna(10)

    thermal = ((apparent - 24) / 16 * 65).clip(0, 65)
    humidity_part = ((humidity - 40) / 60 * 20).clip(0, 20)
    uv_part = (uv / 11 * 10).clip(0, 10)
    wind_part = ((12 - wind) / 12 * 5).clip(0, 5)

    return (thermal + humidity_part + uv_part + wind_part).clip(0, 100)

def weather_description(code):
    descriptions = {
        0: "Clear", 1: "Mainly clear", 2: "Partly cloudy",
        3: "Overcast", 45: "Fog", 48: "Rime fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Dense drizzle",
        61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
        71: "Light snow", 73: "Snow", 75: "Heavy snow",
        80: "Rain showers", 81: "Rain showers",
        82: "Heavy showers", 95: "Thunderstorm",
        96: "Thunderstorm with hail", 99: "Thunderstorm with hail",
    }
    try:
        return descriptions.get(int(code), "Other conditions")
    except (ValueError, TypeError):
        return "Unknown"

def safe_num(value, suffix="", digits=1):
    try:
        if pd.isna(value):
            return "N/A"
        return f"{float(value):.{digits}f}{suffix}"
    except (TypeError, ValueError):
        return "N/A"

# -------------------- SEARCH CONTROLS --------------------

st.sidebar.header("🌐 Global location finder")

selected_country = st.sidebar.selectbox(
    "1. Select country",
    country_names,
    index=country_names.index("Pakistan"),
)

city_query = st.sidebar.text_input(
    "2. Type a city or place",
    placeholder="e.g. Sialkot, London, Tokyo",
)

search_clicked = st.sidebar.button(
    "🔎 Find matching locations",
    use_container_width=True,
)

st.sidebar.caption(
    "Choose any country, then type a city. Matching results are loaded "
    "from worldwide geocoding data."
)

st.sidebar.divider()
st.sidebar.header("Heat alerts")

threshold = st.sidebar.slider(
    "Screening threshold",
    min_value=10,
    max_value=95,
    value=60,
    step=5,
)

if "matches" not in st.session_state:
    st.session_state.matches = []
if "selected_place" not in st.session_state:
    st.session_state.selected_place = None
if "weather" not in st.session_state:
    st.session_state.weather = None
if "weather_place" not in st.session_state:
    st.session_state.weather_place = None
if "search_message" not in st.session_state:
    st.session_state.search_message = ""

if search_clicked:
    if len(city_query.strip()) < 2:
        st.session_state.search_message = (
            "Please type at least two characters of a city or place name."
        )
        st.session_state.matches = []
    else:
        try:
            with st.spinner("Searching worldwide locations..."):
                code = (
                    country_codes.get(selected_country)
                    if selected_country != "All countries"
                    else None
                )
                found = search_locations(city_query, code)
                st.session_state.matches = found
                st.session_state.search_message = (
                    f"{len(found)} matching location(s) returned."
                    if found else
                    "No matches found. Try another spelling or choose All countries."
                )
        except requests.RequestException as exc:
            st.session_state.search_message = f"Location search failed: {exc}"
            st.session_state.matches = []

if st.session_state.search_message:
    st.info(st.session_state.search_message)

matches = st.session_state.matches

# The results are selectable and include country and region where available.
if matches:
    labels = [location_label(p) for p in matches]
    chosen_label = st.selectbox(
        "3. Select the exact location",
        labels,
        key="location_result_selector",
    )
    chosen_place = matches[labels.index(chosen_label)]

    if st.button("🌦️ Load selected location weather", type="primary"):
        try:
            with st.spinner("Loading current conditions and forecast..."):
                data = get_weather(
                    float(chosen_place["latitude"]),
                    float(chosen_place["longitude"]),
                )
                st.session_state.weather = data
                st.session_state.weather_place = chosen_place
                st.session_state.selected_place = chosen_place
        except (requests.RequestException, ValueError, KeyError) as exc:
            st.error(f"Could not load weather: {exc}")

# Load an initial city so the dashboard is not empty on first open.
if st.session_state.weather is None:
    try:
        initial = search_locations("Sialkot", "PK")
        if initial:
            p = initial[0]
            st.session_state.weather = get_weather(
                float(p["latitude"]), float(p["longitude"])
            )
            st.session_state.weather_place = p
            st.session_state.selected_place = p
    except (requests.RequestException, ValueError, KeyError):
        pass

weather = st.session_state.weather
place = st.session_state.weather_place

if weather is None or place is None:
    st.warning("Search for a location above to load weather data.")
    st.stop()

current = weather["current"]
hourly = pd.DataFrame(weather["hourly"])
daily = pd.DataFrame(weather["daily"])

hourly["time"] = pd.to_datetime(hourly["time"], errors="coerce")
daily["time"] = pd.to_datetime(daily["time"], errors="coerce")
hourly["heat_score"] = heat_screening_score(hourly)
hourly["screening_band"] = pd.cut(
    hourly["heat_score"],
    bins=[-1, 25, 50, 75, 100],
    labels=[
        "Lower screening level",
        "Moderate screening level",
        "Elevated screening level",
        "High screening level",
    ],
)

location = location_label(place)

# -------------------- MAIN DASHBOARD --------------------

st.markdown(f"## 📍 {location}")
st.caption(
    f"Local timezone: {weather.get('timezone', 'provider timezone')} · "
    f"Latitude {float(place['latitude']):.3f}, "
    f"longitude {float(place['longitude']):.3f}"
)

st.caption(
    "Forecast provider data · Retrieved when requested · "
    "Not a street-level sensor feed"
)

current_score = (
    float(hourly["heat_score"].iloc[0]) if not hourly.empty else 0
)

a, b, c, d, e = st.columns(5)
a.metric("Air temperature", safe_num(current.get("temperature_2m"), " °C"))
b.metric("Feels like", safe_num(current.get("apparent_temperature"), " °C"))
c.metric("Humidity", safe_num(current.get("relative_humidity_2m"), "%", 0))
d.metric("Wind speed", safe_num(current.get("wind_speed_10m"), " km/h"))
e.metric("Heat screening score", f"{current_score:.0f}/100")

tabs = st.tabs([
    "Overview",
    "7-day forecast",
    "Hourly data",
    "Alerts",
    "Reports",
    "Compare cities",
])

# -------------------- OVERVIEW --------------------

with tabs[0]:
    left, right = st.columns(2)

    with left:
        fig = px.line(
            hourly,
            x="time",
            y=["temperature_2m", "apparent_temperature"],
            title="Air temperature vs feels-like temperature",
            labels={
                "time": "Local time",
                "value": "Temperature (°C)",
                "variable": "Variable",
            },
        )
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font_color="#263A50",
        )
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = px.line(
            hourly,
            x="time",
            y="heat_score",
            title="Heat screening estimate",
            labels={"time": "Local time", "heat_score": "Score / 100"},
        )
        fig.add_hline(
            y=threshold,
            line_dash="dash",
            line_color="#B91C1C",
            annotation_text="Selected threshold",
        )
        fig.update_yaxes(range=[0, 100])
        fig.update_layout(
            template="plotly_white",
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            font_color="#263A50",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("### Today's hourly outlook")
    st.dataframe(
        hourly[[
            "time", "temperature_2m", "apparent_temperature",
            "relative_humidity_2m", "precipitation_probability",
            "wind_speed_10m", "uv_index", "heat_score",
        ]].head(24).round(1),
        use_container_width=True,
        hide_index=True,
    )

# -------------------- 7-DAY FORECAST --------------------

with tabs[1]:
    st.markdown("### Seven-day weather outlook")

    daily["Conditions"] = daily["weather_code"].apply(weather_description)
    daily["Date"] = daily["time"].dt.strftime("%a, %d %b")

    columns = {
        "Date": "Date",
        "temperature_2m_max": "High °C",
        "temperature_2m_min": "Low °C",
        "apparent_temperature_max": "Feels-like high °C",
        "precipitation_probability_max": "Rain chance %",
        "precipitation_sum": "Rain mm",
        "uv_index_max": "Max UV",
        "wind_speed_10m_max": "Max wind km/h",
        "Conditions": "Conditions",
    }

    forecast_table = daily[list(columns.keys())].rename(columns=columns)
    st.dataframe(
        forecast_table.round(1),
        use_container_width=True,
        hide_index=True,
    )

    fig = px.bar(
        daily,
        x="time",
        y=["temperature_2m_max", "temperature_2m_min"],
        barmode="group",
        title="Daily minimum and maximum temperatures",
        labels={"time": "Date", "value": "Temperature (°C)", "variable": "Measure"},
    )
    fig.update_layout(template="plotly_white", font_color="#263A50")
    st.plotly_chart(fig, use_container_width=True)

# -------------------- HOURLY DATA --------------------

with tabs[2]:
    st.markdown("### Forecast variables")

    variable_map = {
        "Air temperature (°C)": "temperature_2m",
        "Feels-like temperature (°C)": "apparent_temperature",
        "Humidity (%)": "relative_humidity_2m",
        "Rain probability (%)": "precipitation_probability",
        "Wind speed (km/h)": "wind_speed_10m",
        "UV index": "uv_index",
        "Cloud cover (%)": "cloud_cover",
        "Heat screening score": "heat_score",
    }

    selected_variable = st.selectbox(
        "Choose a variable",
        list(variable_map.keys()),
    )
    field = variable_map[selected_variable]

    fig = px.line(
        hourly,
        x="time",
        y=field,
        title=selected_variable,
        labels={"time": "Local time", field: selected_variable},
    )
    if field == "heat_score":
        fig.add_hline(y=threshold, line_dash="dash", line_color="#B91C1C")
        fig.update_yaxes(range=[0, 100])

    fig.update_layout(template="plotly_white", font_color="#263A50")
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(hourly, use_container_width=True, hide_index=True)

# -------------------- ALERTS --------------------

with tabs[3]:
    st.markdown("### Configurable forecast threshold alerts")
    st.caption(
        "These alerts are generated by the dashboard's heuristic. "
        "They are not official weather warnings."
    )

    alert_hours = hourly[hourly["heat_score"] >= threshold]

    x, y = st.columns(2)
    x.metric("Chosen threshold", f"{threshold}/100")
    y.metric("Forecast hours at or above threshold", len(alert_hours))

    if not alert_hours.empty:
        st.warning(
            "Some forecast hours meet your selected threshold. "
            "Review official local weather and public-health guidance."
        )
        st.dataframe(
            alert_hours[[
                "time", "temperature_2m", "apparent_temperature",
                "relative_humidity_2m", "uv_index", "heat_score",
            ]].round(1),
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Download alert-hours CSV",
            alert_hours.to_csv(index=False).encode("utf-8"),
            file_name="heatshield_alerts.csv",
            mime="text/csv",
        )
    else:
        st.success(
            "No forecast hours meet this threshold. This does not guarantee safety."
        )

# -------------------- REPORTS --------------------

with tabs[4]:
    st.markdown("### Export climate data")

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report = f"""
HEATSHIELD AI — CLIMATE SCREENING REPORT
Location: {location}
Generated: {generated}
Source: Open-Meteo public forecast API

CURRENT CONDITIONS
Air temperature: {safe_num(current.get('temperature_2m'), ' °C')}
Feels like: {safe_num(current.get('apparent_temperature'), ' °C')}
Humidity: {safe_num(current.get('relative_humidity_2m'), '%', 0)}
Wind: {safe_num(current.get('wind_speed_10m'), ' km/h')}
UV index: {safe_num(current.get('uv_index'))}
Screening score: {current_score:.0f}/100
Selected threshold: {threshold}/100

LIMITATIONS
The score is a heuristic, not a validated medical heat index.
The forecast is not a street-level sensor measurement or official warning.
Use local official weather and public-health guidance.
    """.strip()

    st.download_button(
        "Download text report",
        report.encode("utf-8"),
        file_name="heatshield_report.txt",
        mime="text/plain",
        type="primary",
    )

    st.download_button(
        "Download hourly CSV",
        hourly.to_csv(index=False).encode("utf-8"),
        file_name="heatshield_hourly.csv",
        mime="text/csv",
    )

    st.download_button(
        "Download 7-day CSV",
        daily.to_csv(index=False).encode("utf-8"),
        file_name="heatshield_7day.csv",
        mime="text/csv",
    )

    with st.expander("Preview report"):
        st.text(report)

# -------------------- CITY COMPARISON --------------------

with tabs[5]:
    st.markdown("### Compare multiple cities worldwide")
    st.write(
        "Enter city names separated by commas. The currently selected country "
        "will be used as the filter; choose All countries for a global search."
    )

    compare_input = st.text_input(
        "Cities to compare",
        placeholder="e.g. Sialkot, London, Tokyo, Dubai",
    )

    if st.button("Compare entered cities"):
        names = list(dict.fromkeys(
            name.strip() for name in compare_input.split(",")
            if name.strip()
        ))[:8]

        results = []
        errors = []

        country_code = (
            country_codes.get(selected_country)
            if selected_country != "All countries" else None
        )

        progress = st.progress(0) if names else None

        for index, name in enumerate(names):
            try:
                places = search_locations(name, country_code)
                if not places:
                    errors.append(f"{name}: no matching location.")
                else:
                    p = places[0]
                    fc = get_weather(float(p["latitude"]), float(p["longitude"]))
                    h = pd.DataFrame(fc["hourly"])
                    scores = heat_screening_score(h)
                    cur = fc["current"]

                    results.append({
                        "Location": location_label(p),
                        "Air °C": cur.get("temperature_2m"),
                        "Feels-like °C": cur.get("apparent_temperature"),
                        "Humidity %": cur.get("relative_humidity_2m"),
                        "UV": cur.get("uv_index"),
                        "Screening score": float(scores.iloc[0]),
                        "Latitude": float(p["latitude"]),
                        "Longitude": float(p["longitude"]),
                    })
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                errors.append(f"{name}: {exc}")

            if progress:
                progress.progress((index + 1) / len(names))

        if progress:
            progress.empty()

        if errors:
            with st.expander("Search errors"):
                for error in errors:
                    st.write(error)

        if results:
            result_df = pd.DataFrame(results).sort_values(
                "Screening score", ascending=False
            )
            st.dataframe(
                result_df.round(2),
                use_container_width=True,
                hide_index=True,
            )

            fig = px.bar(
                result_df,
                x="Screening score",
                y="Location",
                orientation="h",
                color="Screening score",
                color_continuous_scale=["#A7DAD5", "#F6C56F", "#C2413B"],
                range_color=[0, 100],
                title="Forecast screening comparison",
            )
            fig.update_layout(
                template="plotly_white",
                font_color="#263A50",
                yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig, use_container_width=True)

            st.download_button(
                "Download comparison CSV",
                result_df.to_csv(index=False).encode("utf-8"),
                file_name="heatshield_city_comparison.csv",
                mime="text/csv",
            )

st.divider()
st.caption(
    "HeatShield AI · Powered by Open-Meteo public weather data. "
    "Forecasts update when refreshed or fetched again. No API key is entered "
    "or stored by this app. Data and availability depend on the provider."
)
