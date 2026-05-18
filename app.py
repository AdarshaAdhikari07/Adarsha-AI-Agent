import streamlit as st
from google import genai
from google.genai import types
import json
import math
import datetime
import urllib.request
import urllib.parse
import os

# Load .env file if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ─────────────────────────────────────────
# Page config
# ─────────────────────────────────────────
st.set_page_config(
    page_title="AI Agent",
    page_icon="🤖",
    layout="centered"
)

st.markdown("""
<style>
    .stChatMessage { border-radius: 12px; }
    .tool-call {
        background: #1a1a2e;
        border-left: 3px solid #6c63ff;
        padding: 0.5rem 1rem;
        border-radius: 6px;
        font-size: 0.82rem;
        color: #9090b8;
        margin: 4px 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🤖 AI Agent")
st.caption("Ask me anything — I can search the web, do maths, check weather, convert currencies, and more.")

# ─────────────────────────────────────────
# Sidebar — API key & Interactive Toggles
# ─────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    default_key = os.getenv("GEMINI_API_KEY", "")
    if not default_key and hasattr(st, "secrets"):
        default_key = st.secrets.get("GEMINI_API_KEY", "")

    if default_key:
        api_key = default_key
        st.success("✅ Gemini API key loaded")
    else:
        api_key = st.text_input("Gemini API Key", type="password", placeholder="AIza...")
        st.markdown("[Get a FREE Gemini API key](https://aistudio.google.com/app/apikey)")

    st.divider()
    st.markdown("**Model:** Gemini 2.5 Flash ⚡")
    st.markdown("**Free tier:** 15 req/min · 1,500 req/day")
    st.divider()
    
    # Fully interactive checkboxes
    st.markdown("**Toggle Active Tools:**")
    use_search = st.checkbox("🔍 Web search", value=True)
    use_calc   = st.checkbox("🧮 Calculator", value=True)
    use_weather= st.checkbox("🌤️ Weather", value=True)
    use_currency=st.checkbox("💱 Currency converter", value=True)
    use_clock  = st.checkbox("⏰ World clock", value=True)
    
    st.divider()
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ─────────────────────────────────────────
# Tool implementations (all free, no extra keys)
# ─────────────────────────────────────────

def tool_calculator(expression: str) -> str:
    try:
        allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        allowed.update({"abs": abs, "round": round, "pow": pow})
        result = eval(expression, {"__builtins__": {}}, allowed)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error evaluating '{expression}': {e}"


def tool_weather(city: str) -> str:
    try:
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        with urllib.request.urlopen(geo_url, timeout=5) as r:
            geo = json.loads(r.read())
        if not geo.get("results"):
            return f"City '{city}' not found."
        loc     = geo["results"][0]
        lat     = loc["latitude"]
        lon     = loc["longitude"]
        name    = loc.get("name", city)
        country = loc.get("country", "")

        wx_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            f"&temperature_unit=celsius"
        )
        with urllib.request.urlopen(wx_url, timeout=5) as r:
            wx = json.loads(r.read())

        cur   = wx["current"]
        temp  = cur["temperature_2m"]
        humid = cur["relative_humidity_2m"]
        wind  = cur["wind_speed_10m"]
        code  = cur["weather_code"]

        wmo = {
            0:"Clear sky", 1:"Mainly clear", 2:"Partly cloudy", 3:"Overcast",
            45:"Foggy", 48:"Icy fog", 51:"Light drizzle", 53:"Drizzle",
            55:"Heavy drizzle", 61:"Slight rain", 63:"Rain", 65:"Heavy rain",
            71:"Slight snow", 73:"Snow", 75:"Heavy snow", 80:"Rain showers",
            81:"Rain showers", 82:"Violent showers", 95:"Thunderstorm",
            96:"Thunderstorm with hail", 99:"Thunderstorm with heavy hail"
        }
        desc = wmo.get(code, f"Code {code}")

        return (
            f"Weather in {name}, {country}:\n"
            f"🌡️ Temperature: {temp}°C\n"
            f"💧 Humidity: {humid}%\n"
            f"💨 Wind: {wind} km/h\n"
            f"☁️ Condition: {desc}"
        )
    except Exception as e:
        return f"Could not fetch weather: {e}"


def tool_currency(amount: float, from_currency: str, to_currency: str) -> str:
    try:
        url = f"https://open.er-api.com/v6/latest/{from_currency.upper()}"
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        if data.get("result") != "success":
            return "Could not fetch exchange rates."
        rate = data["rates"].get(to_currency.upper())
        if not rate:
            return f"Currency '{to_currency}' not found."
        converted = round(amount * rate, 2)
        return f"{amount} {from_currency.upper()} = {converted} {to_currency.upper()} (rate: {rate})"
    except Exception as e:
        return f"Currency conversion error: {e}"


def tool_world_clock(timezone: str) -> str:
    try:
        import zoneinfo
        tz  = zoneinfo.ZoneInfo(timezone)
        now = datetime.datetime.now(tz)
        return f"Current time in {timezone}: {now.strftime('%A, %d %B %Y  %H:%M:%S %Z')}"
    except Exception:
        now = datetime.datetime.utcnow()
        return f"UTC
