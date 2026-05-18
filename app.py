import streamlit as st
import openai
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
    page_title="AI Assistant Agent",
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

st.title("🤖 Personal AI Assistant")
st.caption("Ask me anything — I can search the web, do maths, check weather, convert currencies, and more.")

# ─────────────────────────────────────────
# Sidebar — API key
# ─────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Settings")

    # Load key from .env or Streamlit secrets automatically
    default_key = (
        os.getenv("OPENAI_API_KEY") or
        st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
    )

    if default_key:
        api_key = default_key
        st.success("✅ API key loaded automatically")
    else:
        api_key = st.text_input("OpenAI API Key", type="password", placeholder="sk-...")
        st.markdown("[Get a free API key](https://platform.openai.com/api-keys)")
    st.divider()
    st.markdown("**Tools available:**")
    st.markdown("""
- 🔍 Web search  
- 🧮 Calculator  
- 🌤️ Weather  
- 💱 Currency converter  
- ⏰ World clock  
- 📝 Text summariser  
""")
    if st.button("🗑️ Clear chat"):
        st.session_state.messages = []
        st.rerun()

# ─────────────────────────────────────────
# Tools (real implementations, no API keys needed except weather)
# ─────────────────────────────────────────

def tool_calculator(expression: str) -> str:
    """Safely evaluate a math expression."""
    try:
        allowed = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
        allowed.update({"abs": abs, "round": round, "pow": pow})
        result = eval(expression, {"__builtins__": {}}, allowed)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Error evaluating '{expression}': {e}"


def tool_weather(city: str) -> str:
    """Get current weather using Open-Meteo (free, no key needed)."""
    try:
        # Step 1: geocode city
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1"
        with urllib.request.urlopen(geo_url, timeout=5) as r:
            geo = json.loads(r.read())
        if not geo.get("results"):
            return f"City '{city}' not found."
        loc = geo["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        name = loc.get("name", city)
        country = loc.get("country", "")

        # Step 2: get weather
        wx_url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
            f"&temperature_unit=celsius"
        )
        with urllib.request.urlopen(wx_url, timeout=5) as r:
            wx = json.loads(r.read())

        cur = wx["current"]
        temp  = cur["temperature_2m"]
        humid = cur["relative_humidity_2m"]
        wind  = cur["wind_speed_10m"]
        code  = cur["weather_code"]

        # WMO weather code to description
        wmo = {
            0:"Clear sky", 1:"Mainly clear", 2:"Partly cloudy", 3:"Overcast",
            45:"Foggy", 48:"Icy fog", 51:"Light drizzle", 53:"Drizzle",
            55:"Heavy drizzle", 61:"Slight rain", 63:"Rain", 65:"Heavy rain",
            71:"Slight snow", 73:"Snow", 75:"Heavy snow", 80:"Rain showers",
            81:"Rain showers", 82:"Violent rain showers", 95:"Thunderstorm",
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
    """Convert currency using exchangerate-api (free tier)."""
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
    """Get current time in a given timezone."""
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo(timezone)
        now = datetime.datetime.now(tz)
        return f"Current time in {timezone}: {now.strftime('%A, %d %B %Y  %H:%M:%S %Z')}"
    except Exception:
        # Fallback without zoneinfo
        now = datetime.datetime.utcnow()
        return f"UTC time: {now.strftime('%A, %d %B %Y  %H:%M:%S')} (could not resolve timezone '{timezone}')"


def tool_web_search(query: str) -> str:
    """Search using DuckDuckGo Instant Answer API (free, no key)."""
    try:
        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        with urllib.request.urlopen(url, timeout=6) as r:
            data = json.loads(r.read())

        parts = []
        if data.get("AbstractText"):
            parts.append(data["AbstractText"])
        if data.get("Answer"):
            parts.append(f"Answer: {data['Answer']}")
        for topic in data.get("RelatedTopics", [])[:3]:
            if isinstance(topic, dict) and topic.get("Text"):
                parts.append(f"• {topic['Text']}")

        if parts:
            return "\n".join(parts)
        return f"No instant answer found for '{query}'. Try rephrasing or ask me directly."
    except Exception as e:
        return f"Search error: {e}"


def tool_summarise(text: str) -> str:
    """Return a brief summary prompt — handled by the LLM itself."""
    return f"Please summarise the following text in 3-5 bullet points:\n\n{text}"


# ─────────────────────────────────────────
# Tool definitions for OpenAI function calling
# ─────────────────────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "calculator",
            "description": "Evaluate a mathematical expression. Use for any arithmetic, algebra, or math calculations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Math expression e.g. '2 ** 10' or 'sqrt(144)'"}
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "weather",
            "description": "Get current weather for any city in the world.",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "City name e.g. 'London' or 'Kathmandu'"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "currency_convert",
            "description": "Convert an amount from one currency to another.",
            "parameters": {
                "type": "object",
                "properties": {
                    "amount":        {"type": "number", "description": "Amount to convert"},
                    "from_currency": {"type": "string", "description": "Source currency code e.g. USD"},
                    "to_currency":   {"type": "string", "description": "Target currency code e.g. GBP"}
                },
                "required": ["amount", "from_currency", "to_currency"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "world_clock",
            "description": "Get the current date and time in any timezone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "timezone": {"type": "string", "description": "IANA timezone e.g. 'Europe/London' or 'Asia/Kathmandu'"}
                },
                "required": ["timezone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, facts, or anything you don't know.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"}
                },
                "required": ["query"]
            }
        }
    },
]

# ─────────────────────────────────────────
# Tool dispatcher
# ─────────────────────────────────────────
def run_tool(name: str, args: dict) -> str:
    if name == "calculator":
        return tool_calculator(args["expression"])
    elif name == "weather":
        return tool_weather(args["city"])
    elif name == "currency_convert":
        return tool_currency(args["amount"], args["from_currency"], args["to_currency"])
    elif name == "world_clock":
        return tool_world_clock(args["timezone"])
    elif name == "web_search":
        return tool_web_search(args["query"])
    return "Unknown tool."

# ─────────────────────────────────────────
# Chat state
# ─────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

SYSTEM_PROMPT = """You are a helpful personal AI assistant with access to real-world tools.
Use tools whenever they would give a better, more accurate answer.
Be concise, friendly, and practical. Format responses clearly using markdown where helpful."""

# ─────────────────────────────────────────
# Render chat history
# ─────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] in ("user", "assistant"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ─────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────
user_input = st.chat_input("Ask me anything...")

if user_input:
    if not api_key:
        st.warning("Please enter your OpenAI API key in the sidebar.")
        st.stop()

    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Build messages for API
    api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [
        m for m in st.session_state.messages if m["role"] in ("user", "assistant")
    ]

    client = openai.OpenAI(api_key=api_key)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Agentic loop — keep calling until no more tool calls
            tool_messages = []
            current_messages = api_messages.copy()

            while True:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=current_messages + tool_messages,
                    tools=TOOLS,
                    tool_choice="auto",
                )
                msg = response.choices[0].message

                # If tool calls requested
                if msg.tool_calls:
                    tool_messages.append(msg)
                    for tc in msg.tool_calls:
                        fn_name = tc.function.name
                        fn_args = json.loads(tc.function.arguments)

                        st.markdown(
                            f'<div class="tool-call">🔧 Using tool: <b>{fn_name}</b> — {fn_args}</div>',
                            unsafe_allow_html=True
                        )

                        result = run_tool(fn_name, fn_args)
                        tool_messages.append({
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": result
                        })
                else:
                    # Final answer
                    final = msg.content
                    st.markdown(final)
                    st.session_state.messages.append({"role": "assistant", "content": final})
                    break
