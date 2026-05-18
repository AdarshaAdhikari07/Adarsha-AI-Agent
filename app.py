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
# Sidebar — API key
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
    st.markdown("**Tools available:**")
    st.markdown("""
- 🔍 Web search  
- 🧮 Calculator  
- 🌤️ Weather  
- 💱 Currency converter  
- ⏰ World clock  
""")
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
        return f"UTC time: {now.strftime('%A, %d %B %Y  %H:%M:%S')} (could not resolve '{timezone}')"


def tool_web_search(query: str) -> str:
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
        return "\n".join(parts) if parts else f"No instant answer found for '{query}'."
    except Exception as e:
        return f"Search error: {e}"


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
# Tool declarations (new google-genai style)
# ─────────────────────────────────────────
TOOLS = [
    types.Tool(function_declarations=[
        types.FunctionDeclaration(
            name="calculator",
            description="Evaluate a mathematical expression. Use for any arithmetic or math calculations.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "expression": types.Schema(
                        type=types.Type.STRING,
                        description="Math expression e.g. '2 ** 10' or 'sqrt(144)'"
                    )
                },
                required=["expression"]
            )
        ),
        types.FunctionDeclaration(
            name="weather",
            description="Get current weather for any city in the world.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "city": types.Schema(
                        type=types.Type.STRING,
                        description="City name e.g. 'London' or 'Kathmandu'"
                    )
                },
                required=["city"]
            )
        ),
        types.FunctionDeclaration(
            name="currency_convert",
            description="Convert an amount from one currency to another.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "amount":        types.Schema(type=types.Type.NUMBER,  description="Amount to convert"),
                    "from_currency": types.Schema(type=types.Type.STRING,  description="Source currency code e.g. USD"),
                    "to_currency":   types.Schema(type=types.Type.STRING,  description="Target currency code e.g. GBP"),
                },
                required=["amount", "from_currency", "to_currency"]
            )
        ),
        types.FunctionDeclaration(
            name="world_clock",
            description="Get the current date and time in any timezone.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "timezone": types.Schema(
                        type=types.Type.STRING,
                        description="IANA timezone e.g. 'Europe/London' or 'Asia/Kathmandu'"
                    )
                },
                required=["timezone"]
            )
        ),
        types.FunctionDeclaration(
            name="web_search",
            description="Search the web for current information, news, or facts.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="Search query")
                },
                required=["query"]
            )
        ),
    ])
]

SYSTEM_PROMPT = """You are a helpful personal AI assistant with access to real-world tools.
Use tools whenever they would give a better, more accurate answer.
Be concise, friendly, and practical. Format responses clearly using markdown where helpful."""

# ─────────────────────────────────────────
# Chat state
# ─────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    # Only render visible chat items (ignoring complex API objects if any slipped in)
    if isinstance(msg.get("content"), str):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ─────────────────────────────────────────
# Chat input
# ─────────────────────────────────────────
user_input = st.chat_input("Ask me anything...")

if user_input:
    if not api_key:
        st.warning("Please enter your Gemini API key in the sidebar.")
        st.stop()

    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # Reconstruct raw history blocks for Gemini
    contents = []
    for m in st.session_state.messages:
        if m["role"] == "user":
            contents.append(types.Content(role="user", parts=[types.Part(text=m["content"])]))
        elif m["role"] == "assistant":
            contents.append(types.Content(role="model", parts=[types.Part(text=m["content"])]))
        elif m["role"] == "raw_interaction":
            # Appends raw function_calls or function_responses to preserve history structure
            contents.extend(m["content"])

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                client = genai.Client(api_key=api_key)

                # Agentic loop
                while True:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=SYSTEM_PROMPT,
                            tools=TOOLS,
                        )
                    )

                    candidate = response.candidates[0].content

                    # Check if any part is a function call
                    fn_calls = [p for p in candidate.parts if p.function_call is not None]

                    if fn_calls:
                        # Append model intent to active scope
                        contents.append(candidate)
                        # Save the model's tool intent to st.session_state to avoid breaking future context
                        st.session_state.messages.append({"role": "raw_interaction", "content": [candidate]})

                        # Execute each tool and collect results
                        tool_result_parts = []
                        for part in fn_calls:
                            fn_name = part.function_call.name
                            fn_args = dict(part.function_call.args)

                            st.markdown(
                                f'<div class="tool-call">🔧 Using tool: <b>{fn_name}</b> — {fn_args}</div>',
                                unsafe_allow_html=True
                            )

                            result = run_tool(fn_name, fn_args)
                            tool_result_parts.append(
                                types.Part(
                                    function_response=types.FunctionResponse(
                                        name=fn_name,
                                        response={"result": result}
                                    )
                                )
                            )

                        tool_content = types.Content(role="user", parts=tool_result_parts)
                        
                        # Feed result back to running context and history
                        contents.append(tool_content)
                        st.session_state.messages.append({"role": "raw_interaction", "content": [tool_content]})

                    else:
                        # Final text answer
                        final = response.text
                        st.markdown(final)
                        st.session_state.messages.append({"role": "assistant", "content": final})
                        break

            except Exception as e:
                st.error(f"Error: {e}")
