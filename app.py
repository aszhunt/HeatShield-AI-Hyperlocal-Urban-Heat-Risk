
import requests
import pandas as pd
import plotly.express as px
import streamlit as st
from datetime import datetime

# ==========================================================
# HeatShield AI | ASZ Climate Research Intelligence
# Forecasting • Hotspot Screening • Alerts • Reports
# ==========================================================

st.set_page_config(
    page_title="HeatShield AI | Climate Research",
    page_icon="🌡️",
    layout="wide",
)

GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = 20

st.markdown("""
<style>
.stApp {
    background: linear-gradient(140deg,#0b1220,#101c30 55%,#09101c);
    color: #edf4ff;
}
[data-testid="stSidebar"] {
    background: #101a2b;
}
.hero {
    padding: 26px;
    border: 1px solid #36506b;
    border-radius: 18px;
    background: linear-gradient(115deg,#122c40,#17263b,#38251e);
    margin-bottom: 18px;
}
.eyebrow {
    color: #72e3ed;
    font-size: 12px;
    letter-spacing: 3px;
    font-weight: 800;
}
.hero h1 {
    color: white;
    font-size: 38px;
    margin: 8px 0;
}
.hero p { color: #c6d5e7; }
[data-testid="stMetric"] {
    background: #111d2e;
    border: 1px solid #2c4057;
    padding: 14px;
    border-radius: 12px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="hero">
  <div class="eyebrow">ASZ • CLIMATE RESEARCH INTELLIGENCE</div>
  <h1>🌡️ HeatShield AI</h1>
  <p>Hyperlocal Urban Heat Risk Forecasting</p>
  <p>Weather forecasts, comparative risk screening, early-warning
  indicators and climate-planning reports.</p>
</div>
""", unsafe_allow_html=True)


# ---------------- DATA SERVICES ----------------

@st.cache_data(ttl=1800, show_spinner=False)
def geocode(place):
    response = requests.get(
        GEOCODE_URL,
        params={
            "name": place,
            "count": 5,
            "language": "en",
            "format": "json",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    return response.json().get("results", [])


@st.cache_data(ttl=900, show_spinner=False)
def get_forecast(lat, lon):
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": lat,
            "longitude": lon,
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


# ---------------- TRANSPARENT SCREENING MODEL ----------------

def calculate_risk(feels, humidity, uv, wind):
    """Heuristic index, not an official warning or validated WBGT."""
    thermal = max(0, min(70, (float(feels) - 20) * 3))
    humidity_factor = max(
        0, min(12, (float(humidity) - 45) * 0.18)
    )
    uv_factor = max(0, min(12, float(uv) * 1.4))
    wind_relief = max(0, min(8, float(wind) * 0.22))

    return round(max(
        0, min(100, thermal + humidity_factor
               + uv_factor - wind_relief)
    ))


def risk_label(score):
    if score < 20:
        return "LOW", "🟢"
    if score < 40:
        return "MODERATE", "🟡"
    if score < 60:
        return "HIGH", "🟠"
    if score < 80:
        return "VERY HIGH", "🔴"
    return "EXTREME", "🟣"


def make_hourly_frame(hourly):
    df = pd.DataFrame(hourly)
    if df.empty or "time" not in df.columns:
        return df

    defaults = {
        "apparent_temperature": 0,
        "relative_humidity_2m": 50,
        "uv_index": 0,
        "wind_speed_10m": 0,
    }
    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default

    df["time"] = pd.to_datetime(df["time"], errors="coerce")
    df["risk_index"] = df.apply(
        lambda row: calculate_risk(
            row["apparent_temperature"],
            row["relative_humidity_2m"],
            row["uv_index"],
            row["wind_speed_10m"],
        ),
        axis=1,
    )
    df["risk_level"] = df["risk_index"].apply(
        lambda value: risk_label(value)[0]
    )
    return df.dropna(subset=["time"])


def place_name(location):
    return ", ".join(
        str(location[key])
        for key in ("name", "admin1", "country")
        if location.get(key)
    )


def current_summary(location, weather):
    current = weather.get("current", {})
    temp = current.get("temperature_2m", 0)
    feels = current.get("apparent_temperature", temp)
    humidity = current.get("relative_humidity_2m", 50)
    uv = current.get("uv_index", 0)
    wind = current.get("wind_speed_10m", 0)
    score = calculate_risk(feels, humidity, uv, wind)
    label, _ = risk_label(score)

    return {
        "Location": place_name(location),
        "Latitude": location["latitude"],
        "Longitude": location["longitude"],
        "Temperature °C": temp,
        "Feels-like °C": feels,
        "Humidity %": humidity,
        "UV index": uv,
        "Wind km/h": wind,
        "Risk index": score,
        "Risk level": label,
    }


# ---------------- SIDEBAR ----------------

with st.sidebar:
    st.markdown("## 🛰️ Research controls")
    search_place = st.text_input(
        "Primary location",
        value="Sialkot, Pakistan",
    )
    run_scan = st.button(
        "RUN CLIMATE SCAN",
        type="primary",
        use_container_width=True,
    )

    st.divider()
    st.markdown("### Early-warning threshold")
    alert_threshold = st.slider(
        "Risk index that triggers an alert",
        min_value=20,
        max_value=90,
        value=60,
        step=5,
    )

    st.markdown("### Risk classification")
    st.caption(
        "0–19 Low · 20–39 Moderate · 40–59 High · "
        "60–79 Very High · 80–100 Extreme"
    )

    st.divider()
    st.caption("Weather data: Open-Meteo")
    st.caption("No API key required for this prototype.")
    st.caption("Internet access required.")


# ---------------- SESSION STATE ----------------

if "location" not in st.session_state:
    st.session_state.location = None
if "weather" not in st.session_state:
    st.session_state.weather = None

if run_scan:
    if not search_place.strip():
        st.error("Enter a location first.")
    else:
        try:
            with st.spinner("Resolving location and retrieving forecast..."):
                results = geocode(search_place.strip())

                if not results:
                    st.session_state.location = None
                    st.session_state.weather = None
                    st.error(
                        "Location not found. Add a country or region."
                    )
                else:
                    st.session_state.location = results[0]
                    st.session_state.weather = get_forecast(
                        results[0]["latitude"],
                        results[0]["longitude"],
                    )
        except requests.RequestException:
            st.error(
                "The weather service is unavailable. "
                "Check your connection and retry."
            )
        except (ValueError, KeyError, TypeError):
            st.error("The location or forecast response was invalid.")


# ---------------- MAIN DASHBOARD ----------------

location = st.session_state.location
weather = st.session_state.weather

if location and weather:
    current = weather.get("current", {})
    temp = current.get("temperature_2m", 0)
    feels = current.get("apparent_temperature", temp)
    humidity = current.get("relative_humidity_2m", 50)
    uv = current.get("uv_index", 0)
    wind = current.get("wind_speed_10m", 0)

    score = calculate_risk(feels, humidity, uv, wind)
    label, emoji = risk_label(score)

    st.markdown(f"## 📍 {place_name(location)}")
    st.caption(
        f"Forecast grid point: {location['latitude']:.3f}, "
        f"{location['longitude']:.3f} · "
        f"Timezone: {weather.get('timezone', 'local')}"
    )

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Risk index", f"{score}/100", label)
    m2.metric("Temperature", f"{temp} °C")
    m3.metric("Feels-like", f"{feels} °C")
    m4.metric("Humidity", f"{humidity}%")
    m5.metric("UV index", str(uv))

    if score >= alert_threshold:
        st.warning(
            f"⚠️ HEAT RISK ALERT: Screening index {score} "
            f"has reached your threshold of {alert_threshold}. "
            "Review the forecast and follow official local guidance."
        )
    else:
        st.info(
            f"Current screening index is below your configured "
            f"alert threshold ({alert_threshold}). "
            "This does not guarantee safe conditions."
        )

    hourly_df = make_hourly_frame(weather.get("hourly", {}))
    daily_df = pd.DataFrame(weather.get("daily", {}))

    dashboard_tab, hotspot_tab, alerts_tab, report_tab = st.tabs([
        "📊 Forecast dashboard",
        "🗺️ Hotspot screening",
        "🚨 Early warnings",
        "📑 Reports & export",
    ])

    # ---------------- FORECAST DASHBOARD ----------------

    with dashboard_tab:
        st.subheader("Seven-day forecast analytics")

        if not hourly_df.empty:
            temperature_chart = px.line(
                hourly_df,
                x="time",
                y="apparent_temperature",
                title="Hourly feels-like temperature",
                labels={
                    "time": "Local time",
                    "apparent_temperature": "Feels-like °C",
                },
            )
            temperature_chart.update_layout(template="plotly_dark")
            st.plotly_chart(
                temperature_chart,
                use_container_width=True,
            )

            risk_chart = px.area(
                hourly_df,
                x="time",
                y="risk_index",
                title="Hourly heat screening index",
                labels={
                    "time": "Local time",
                    "risk_index": "Screening index",
                },
            )
            risk_chart.update_layout(
                template="plotly_dark",
                yaxis_range=[0, 100],
            )
            st.plotly_chart(risk_chart, use_container_width=True)

        if not daily_df.empty:
            daily_display = daily_df.rename(columns={
                "time": "Date",
                "temperature_2m_max": "Maximum °C",
                "temperature_2m_min": "Minimum °C",
                "apparent_temperature_max": "Maximum feels-like °C",
                "uv_index_max": "Maximum UV",
            })
            st.subheader("Daily forecast")
            st.dataframe(
                daily_display,
                use_container_width=True,
                hide_index=True,
            )

    # ---------------- HOTSPOT SCREENING ----------------

    with hotspot_tab:
        st.subheader("Compare forecast conditions across locations")
        st.write(
            "Enter comma-separated city or town names. "
            "The app compares available forecast grid points; "
            "it does not measure street-level urban heat islands."
        )

        comparison_text = st.text_input(
            "Locations to compare",
            value="Sialkot, Pakistan; Lahore, Pakistan; Multan, Pakistan",
            key="comparison_locations",
        )

        if st.button("COMPARE LOCATIONS", type="primary"):
            places = [
                item.strip()
                for item in comparison_text.split(";")
                if item.strip()
            ]
            if not places:
                st.warning("Enter at least one location.")
            elif len(places) > 8:
                st.warning("Compare up to 8 locations at a time.")
            else:
                summaries = []
                errors = []

                progress = st.progress(0)
                for index, place_text in enumerate(places):
                    try:
                        matches = geocode(place_text)
                        if not matches:
                            errors.append(f"{place_text}: not found")
                        else:
                            chosen = matches[0]
                            forecast = get_forecast(
                                chosen["latitude"],
                                chosen["longitude"],
                            )
                            summaries.append(
                                current_summary(chosen, forecast)
                            )
                    except requests.RequestException:
                        errors.append(
                            f"{place_text}: weather service request failed"
                        )
                    progress.progress((index + 1) / len(places))

                st.session_state.hotspot_results = summaries
                st.session_state.hotspot_errors = errors

        summaries = st.session_state.get("hotspot_results", [])
        errors = st.session_state.get("hotspot_errors", [])

        if errors:
            for message in errors:
                st.warning(message)

        if summaries:
            comparison = pd.DataFrame(summaries).sort_values(
                "Risk index", ascending=False
            )
            st.markdown("### Comparative risk ranking")
            st.dataframe(
                comparison,
                use_container_width=True,
                hide_index=True,
            )

            fig = px.bar(
                comparison,
                x="Location",
                y="Risk index",
                color="Risk level",
                title="Forecast-based location screening comparison",
                hover_data=[
                    "Temperature °C",
                    "Feels-like °C",
                    "Humidity %",
                ],
            )
            fig.update_layout(template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

            map_fig = px.scatter_geo(
                comparison,
                lat="Latitude",
                lon="Longitude",
                color="Risk index",
                size="Risk index",
                hover_name="Location",
                hover_data=["Risk level", "Feels-like °C"],
                title="Forecast comparison locations",
            )
            map_fig.update_layout(
                template="plotly_dark",
                geo=dict(
                    showland=True,
                    showcountries=True,
                    showcoastlines=True,
                ),
            )
            st.plotly_chart(map_fig, use_container_width=True)

            st.caption(
                "Highest index means highest score under this "
                "screening formula, not proof of a measured urban "
                "heat island or a validated health-risk ranking."
            )

    # ---------------- ALERT CENTER ----------------

    with alerts_tab:
        st.subheader("Early-warning indicators")
        st.write(
            f"Configured trigger: screening index ≥ {alert_threshold}"
        )

        if not hourly_df.empty:
            upcoming = hourly_df[
                hourly_df["risk_index"] >= alert_threshold
            ].copy()

            if upcoming.empty:
                st.success(
                    "No forecast hours reached this configured "
                    "threshold in the retrieved hourly forecast."
                )
            else:
                st.warning(
                    f"{len(upcoming)} forecast hours reach or exceed "
                    "your selected threshold."
                )
                alert_view = upcoming[
                    [
                        "time",
                        "apparent_temperature",
                        "relative_humidity_2m",
                        "uv_index",
                        "risk_index",
                        "risk_level",
                    ]
                ].rename(columns={
                    "time": "Local time",
                    "apparent_temperature": "Feels-like °C",
                    "relative_humidity_2m": "Humidity %",
                    "uv_index": "UV index",
                    "risk_index": "Screening index",
                    "risk_level": "Screening level",
                })
                st.dataframe(
                    alert_view,
                    use_container_width=True,
                    hide_index=True,
                )

                st.download_button(
                    "Download alert hours CSV",
                    data=alert_view.to_csv(index=False).encode("utf-8"),
                    file_name="heatshield_alert_hours.csv",
                    mime="text/csv",
                )

        st.markdown("### Recommended precautions")
        st.markdown("""
        - Review official weather and heat-health alerts.
        - Schedule strenuous outdoor work for cooler hours.
        - Provide drinking water, shade and recovery breaks.
        - Check on older adults, infants and people without cooling.
        - Seek urgent medical assistance for suspected severe
          heat illness.
        """)

        st.caption(
            "These are in-app forecast indicators only. They do not "
            "send SMS, email or push notifications in the background."
        )

    # ---------------- REPORTS & EXPORT ----------------

    with report_tab:
        st.subheader("Climate research export center")

        report = pd.DataFrame([current_summary(location, weather)])
        st.markdown("### Current location summary")
        st.dataframe(report, use_container_width=True, hide_index=True)

        if not hourly_df.empty:
            st.download_button(
                "⬇️ Download full hourly forecast CSV",
                data=hourly_df.to_csv(index=False).encode("utf-8"),
                file_name="heatshield_hourly_forecast.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if not daily_df.empty:
            st.download_button(
                "⬇️ Download daily forecast CSV",
                data=daily_df.to_csv(index=False).encode("utf-8"),
                file_name="heatshield_daily_forecast.csv",
                mime="text/csv",
                use_container_width=True,
            )

        report_text = f"""
HEATSHIELD AI — CLIMATE SCREENING REPORT
Generated: {datetime.now().isoformat(timespec="minutes")}
Location: {place_name(location)}
Latitude: {location["latitude"]}
Longitude: {location["longitude"]}
Timezone: {weather.get("timezone", "local")}

CURRENT WEATHER
Temperature: {temp} °C
Feels-like temperature: {feels} °C
Relative humidity: {humidity}%
UV index: {uv}
Wind speed: {wind} km/h

HEAT SCREENING
Index: {score}/100
Category: {label}
Configured alert threshold: {alert_threshold}

METHODOLOGY AND LIMITATIONS
The score is a heuristic screening index based on apparent
temperature, humidity, UV and wind. It is not a validated
medical model, official warning, WBGT measurement or a
street-level heat observation. Forecasts represent model
grid points and can miss local shade, buildings and surface
temperatures. Consult official local alerts.
"""
        st.download_button(
            "⬇️ Download text research report",
            data=report_text,
            file_name="heatshield_research_report.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.divider()
    st.caption(
        "Data source: Open-Meteo public forecast and geocoding APIs. "
        "Forecast values can change. This app is an experimental "
        "decision-support prototype, not an official warning system. "
        "No API key is configured or required by this code."
    )

else:
    st.info(
        "Enter a city or locality in the sidebar and click "
        "**RUN CLIMATE SCAN** to begin."
    )

    st.markdown("### Platform modules")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Module 01", "Forecasting")
    c2.metric("Module 02", "Hotspot screening")
    c3.metric("Module 03", "Risk alerts")
    c4.metric("Module 04", "Reports")
