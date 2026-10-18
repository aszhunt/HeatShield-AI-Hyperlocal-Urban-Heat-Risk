
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

# =========================================================
# HEATSHIELD AI | ASZ CLIMATE INTELLIGENCE
# Hyperlocal Urban Heat Risk Forecasting
# =========================================================

st.set_page_config(
    page_title="HeatShield AI | Urban Heat Intelligence",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 25

st.markdown("""
<style>
.stApp {
    background: radial-gradient(
        circle at 10% 0%, #172554 0%, #090f20 42%, #070a12 100%
    );
    color: #f1f5f9;
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #111b32, #080d19);
}
.hero {
    padding: 28px;
    border: 1px solid #334b70;
    border-radius: 20px;
    background: linear-gradient(
        120deg, rgba(14,165,233,.19), rgba(249,115,22,.14)
    );
    margin-bottom: 20px;
}
.eyebrow {
    color: #67e8f9;
    letter-spacing: 3px;
    font-size: 12px;
    font-weight: 800;
}
.hero h1 {
    color: white;
    font-size: 40px;
    margin: 8px 0;
}
.hero p { color: #cbd5e1; }
[data-testid="stMetric"] {
    background: rgba(15,23,42,.75);
    border: 1px solid #334155;
    padding: 15px;
    border-radius: 14px;
}
.section-card {
    padding: 20px;
    border: 1px solid #334155;
    border-radius: 15px;
    background: rgba(15,23,42,.65);
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
    <div class="eyebrow">ASZ • CLIMATE INTELLIGENCE</div>
    <h1>🌡️ HeatShield AI</h1>
    <p>
    Hyperlocal Urban Heat Risk Forecasting<br>
    Weather intelligence for safer cities, outdoor workers
    and climate-resilient communities.
    </p>
</div>
""", unsafe_allow_html=True)


# ---------------- LOCATION SEARCH ----------------

def search_location(place):
    response = requests.get(
        GEOCODE_URL,
        params={
            "name": place,
            "count": 8,
            "language": "en",
            "format": "json",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("results", [])


# ---------------- WEATHER FORECAST ----------------

def get_forecast(latitude, longitude):
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": latitude,
            "longitude": longitude,
            "timezone": "auto",
            "forecast_days": 7,
            "current": (
                "temperature_2m,relative_humidity_2m,"
                "apparent_temperature,wind_speed_10m,uv_index"
            ),
            "hourly": (
                "temperature_2m,relative_humidity_2m,"
                "apparent_temperature,precipitation_probability,"
                "wind_speed_10m,uv_index"
            ),
            "daily": (
                "temperature_2m_max,temperature_2m_min,"
                "apparent_temperature_max,uv_index_max"
            ),
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# ---------------- TRANSPARENT RISK MODEL ----------------

def calculate_risk(feels_like, humidity, uv, wind):
    """
    Heuristic screening index from 0 to 100.
    This is NOT an official heat warning or WBGT model.
    """
    thermal = max(0, min(70, (feels_like - 20) * 3))
    humidity_factor = max(0, min(12, (humidity - 45) * 0.18))
    uv_factor = max(0, min(12, uv * 1.4))
    wind_relief = max(0, min(8, wind * 0.22))

    score = thermal + humidity_factor + uv_factor - wind_relief
    return round(max(0, min(100, score)))


def risk_category(score):
    if score < 20:
        return "LOW", "🟢"
    if score < 40:
        return "MODERATE", "🟡"
    if score < 60:
        return "HIGH", "🟠"
    if score < 80:
        return "VERY HIGH", "🔴"
    return "EXTREME", "🟣"


def build_hourly_dataframe(hourly):
    df = pd.DataFrame(hourly)

    if df.empty or "time" not in df.columns:
        return df

    required = [
        "apparent_temperature",
        "relative_humidity_2m",
        "uv_index",
        "wind_speed_10m",
    ]

    for column in required:
        if column not in df.columns:
            df[column] = 0

    df["time"] = pd.to_datetime(df["time"], errors="coerce")

    df["risk_score"] = df.apply(
        lambda row: calculate_risk(
            row["apparent_temperature"],
            row["relative_humidity_2m"],
            row["uv_index"],
            row["wind_speed_10m"],
        ),
        axis=1,
    )

    df["risk_level"] = df["risk_score"].apply(
        lambda score: risk_category(score)[0]
    )

    return df.dropna(subset=["time"])


# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.markdown("## 🛰️ CONTROL CENTER")
    st.caption("Hyperlocal weather intelligence")

    location_input = st.text_input(
        "City / Town / Locality",
        value="Sialkot, Pakistan",
        placeholder="e.g. Lahore, Pakistan",
    )

    run_button = st.button(
        "🚀 RUN HEAT SCAN",
        type="primary",
        use_container_width=True,
    )

    st.divider()

    st.markdown("### 📊 Risk scale")
    st.markdown(
        "🟢 0–19: Low\n\n"
        "🟡 20–39: Moderate\n\n"
        "🟠 40–59: High\n\n"
        "🔴 60–79: Very High\n\n"
        "🟣 80–100: Extreme"
    )

    st.divider()
    st.caption("Data provider: Open-Meteo")
    st.caption("No API key required.")
    st.caption("Internet access is required.")


# ---------------- SESSION STATE ----------------

if "locations" not in st.session_state:
    st.session_state.locations = []

if "weather" not in st.session_state:
    st.session_state.weather = None

if "selected_index" not in st.session_state:
    st.session_state.selected_index = 0


# ---------------- EXECUTE SEARCH ----------------

if run_button:
    if not location_input.strip():
        st.error("Please enter a city or locality.")
    else:
        try:
            with st.spinner("🔎 Finding your location..."):
                matches = search_location(location_input.strip())

            if not matches:
                st.session_state.locations = []
                st.session_state.weather = None
                st.error(
                    "Location not found. Try adding the country name."
                )
            else:
                st.session_state.locations = matches
                st.session_state.selected_index = 0

                with st.spinner("🌡️ Loading forecast data..."):
                    first = matches[0]
                    st.session_state.weather = get_forecast(
                        first["latitude"],
                        first["longitude"],
                    )

        except requests.RequestException:
            st.error(
                "Weather service could not be reached. "
                "Check your internet connection and retry."
            )
        except (ValueError, KeyError, TypeError):
            st.error(
                "The location or weather response could not be processed."
            )


# ---------------- LOCATION SELECTION ----------------

locations = st.session_state.locations

if locations:
    def location_label(index):
        item = locations[index]
        parts = [
            item.get("name"),
            item.get("admin1"),
            item.get("country"),
        ]
        return ", ".join(str(part) for part in parts if part)

    selected = st.selectbox(
        "📍 Confirm your location",
        options=list(range(len(locations))),
        format_func=location_label,
        index=min(
            st.session_state.selected_index,
            len(locations) - 1,
        ),
    )

    if selected != st.session_state.selected_index:
        st.session_state.selected_index = selected
        item = locations[selected]

        try:
            with st.spinner("Updating local forecast..."):
                st.session_state.weather = get_forecast(
                    item["latitude"],
                    item["longitude"],
                )
        except requests.RequestException:
            st.error("Unable to load this location's forecast.")

weather = st.session_state.weather

if weather and locations:
    selected_location = locations[
        st.session_state.selected_index
    ]

    # ---------------- CURRENT CONDITIONS ----------------

    current = weather.get("current", {})

    temperature = current.get("temperature_2m", 0)
    feels_like = current.get("apparent_temperature", temperature)
    humidity = current.get("relative_humidity_2m", 50)
    wind = current.get("wind_speed_10m", 0)
    uv = current.get("uv_index", 0)

    score = calculate_risk(feels_like, humidity, uv, wind)
    category, emoji = risk_category(score)

    place_name = location_label(
        st.session_state.selected_index
    )

    st.markdown(f"## 📍 {place_name}")
    st.caption(
        f"Forecast grid point: "
        f"{selected_location['latitude']:.3f}, "
        f"{selected_location['longitude']:.3f}"
        f" • Time zone: {weather.get('timezone', 'local')}"
    )

    # ---------------- METRIC CARDS ----------------

    col1, col2, col3, col4, col5 = st.columns(5)

    col1.metric("HEAT RISK", f"{score}/100", category)
    col2.metric("AIR TEMP", f"{temperature} °C")
    col3.metric("FEELS LIKE", f"{feels_like} °C")
    col4.metric("HUMIDITY", f"{humidity}%")
    col5.metric("UV INDEX", str(uv))

    st.markdown(f"## {emoji} Current screening level: {category}")

    if score >= 80:
        st.error(
            "EXTREME SIGNAL: Avoid strenuous outdoor activity "
            "where possible. Seek a cool environment, hydrate, "
            "and check on vulnerable people. Follow official alerts."
        )
    elif score >= 60:
        st.warning(
            "VERY HIGH SIGNAL: Plan outdoor work for cooler hours, "
            "provide shade and frequent rest breaks, and ensure "
            "water is readily available."
        )
    elif score >= 40:
        st.warning(
            "HIGH SIGNAL: Reduce prolonged direct sun exposure, "
            "take cooling breaks, and watch for heat-illness symptoms."
        )
    elif score >= 20:
        st.info(
            "MODERATE SIGNAL: Stay hydrated and use shade during "
            "the warmest hours, especially during physical activity."
        )
    else:
        st.success(
            "LOW SIGNAL under this screening model. "
            "Normal heat-safety precautions may still be appropriate."
        )

    # ---------------- HOURLY ANALYTICS ----------------

    hourly = weather.get("hourly", {})
    hourly_df = build_hourly_dataframe(hourly)

    st.divider()
    st.markdown("## 📈 SEVEN-DAY FORECAST INTELLIGENCE")

    if not hourly_df.empty:
        chart1 = px.line(
            hourly_df,
            x="time",
            y="apparent_temperature",
            title="Feels-Like Temperature Forecast",
            labels={
                "time": "Local time",
                "apparent_temperature": "Feels-like °C",
            },
        )
        chart1.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(chart1, use_container_width=True)

        chart2 = px.area(
            hourly_df,
            x="time",
            y="risk_score",
            title="HeatShield Hourly Risk Index",
            labels={
                "time": "Local time",
                "risk_score": "Risk index",
            },
        )
        chart2.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis_range=[0, 100],
        )
        st.plotly_chart(chart2, use_container_width=True)

        st.markdown("### ⚠️ Highest-Risk Forecast Hours")

        peaks = hourly_df.nlargest(10, "risk_score")[
            [
                "time",
                "apparent_temperature",
                "relative_humidity_2m",
                "uv_index",
                "wind_speed_10m",
                "risk_score",
                "risk_level",
            ]
        ].copy()

        peaks["time"] = peaks["time"].dt.strftime(
            "%a, %d %b • %H:%M"
        )

        peaks = peaks.rename(
            columns={
                "time": "Local time",
                "apparent_temperature": "Feels-like °C",
                "relative_humidity_2m": "Humidity %",
                "uv_index": "UV",
                "wind_speed_10m": "Wind km/h",
                "risk_score": "Index",
                "risk_level": "Risk level",
            }
        )

        st.dataframe(
            peaks,
            use_container_width=True,
            hide_index=True,
        )

        st.download_button(
            "⬇️ DOWNLOAD HOURLY FORECAST CSV",
            data=hourly_df.to_csv(index=False).encode("utf-8"),
            file_name="heatshield_hourly_forecast.csv",
            mime="text/csv",
        )
    else:
        st.warning("Hourly forecast data is not available.")

    # ---------------- DAILY OUTLOOK ----------------

    daily = weather.get("daily", {})
    daily_df = pd.DataFrame(daily)

    if not daily_df.empty:
        daily_df = daily_df.rename(
            columns={
                "time": "Date",
                "temperature_2m_max": "Maximum °C",
                "temperature_2m_min": "Minimum °C",
                "apparent_temperature_max": "Maximum feels-like °C",
                "uv_index_max": "Maximum UV",
            }
        )

        st.markdown("### 🗓️ Daily Outlook")
        st.dataframe(
            daily_df,
            use_container_width=True,
            hide_index=True,
        )

    # ---------------- ACTION CENTER ----------------

    st.divider()
    st.markdown("## 🛡️ HEAT SAFETY ACTION CENTER")

    a, b = st.columns(2)

    with a:
        st.markdown("""
        <div class="section-card">
        <h4>🦺 Outdoor Operations</h4>
        • Schedule heavy work for cooler hours.<br>
        • Provide shaded recovery areas.<br>
        • Make drinking water accessible.<br>
        • Monitor workers for heat-illness symptoms.
        </div>
        """, unsafe_allow_html=True)

        st.write("")

        st.markdown("""
        <div class="section-card">
        <h4>🏫 Schools & Communities</h4>
        • Review peak forecast hours.<br>
        • Plan indoor or shaded alternatives.<br>
        • Establish cooling and emergency plans.
        </div>
        """, unsafe_allow_html=True)

    with b:
        st.markdown("""
        <div class="section-card">
        <h4>🤝 Vulnerable People</h4>
        • Check on older adults and infants.<br>
        • Consider people without reliable cooling.<br>
        • Seek urgent medical help for severe symptoms.
        </div>
        """, unsafe_allow_html=True)

        st.write("")

        st.markdown("""
        <div class="section-card">
        <h4>🏙️ Urban Planning</h4>
        • Expand tree canopy and shade.<br>
        • Improve access to drinking water.<br>
        • Consider cool roofs and heat-resilient spaces.<br>
        • Combine forecasts with local sensor data.
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    st.caption(
        "HEATSHIELD AI DISCLAIMER: This is an experimental "
        "weather-based screening tool, not an official warning "
        "system, medical diagnosis, validated WBGT model, or "
        "street-level temperature measurement. Weather forecasts "
        "cannot fully capture shade, buildings, surface temperatures, "
        "indoor conditions, or individual vulnerability. Consult "
        "official local alerts and qualified safety professionals."
    )

else:
    st.markdown("""
    <div class="section-card">
    <h3>🚀 Your local heat scan starts here</h3>
    Enter a city or locality in the sidebar and click
    <b>RUN HEAT SCAN</b> to load the seven-day weather forecast,
    calculate the screening index, discover higher-risk hours,
    and download the forecast data.
    </div>
    """, unsafe_allow_html=True)

    st.write("")

    x, y, z = st.columns(3)

    x.markdown("""
    <div class="section-card">
    <h4>🌡️ Heat Analytics</h4>
    Understand temperature and feels-like trends.
    </div>
    """, unsafe_allow_html=True)

    y.markdown("""
    <div class="section-card">
    <h4>📊 Forecast Intelligence</h4>
    Explore hourly and daily forecast patterns.
    </div>
    """, unsafe_allow_html=True)

    z.markdown("""
    <div class="section-card">
    <h4>🛡️ Safety Planning</h4>
    Turn forecast signals into practical precautions.
    </div>
    """, unsafe_allow_html=True)
