"""Current weather via OpenWeatherMap, with Groq LLM fallback."""
import re
import requests
from groq import Groq

from .config import OPEN_WEATHER_API_KEY, DEFAULT_CITY, GROQ_API_KEY, GROQ_LLM_MODEL

_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
_groq = Groq(api_key=GROQ_API_KEY)


def _format_temps(celsius: float, condition: str, city: str) -> str:
    fahrenheit = celsius * 9 / 5 + 32
    kelvin     = celsius + 273.15
    return f"{city}: {celsius:.1f}°C / {fahrenheit:.1f}°F / {kelvin:.2f}K, {condition}"


def _groq_fallback(city: str) -> str:
    """Ask Groq for the current temperature when the API is unavailable."""
    prompt = (
        f"What is the approximate current temperature in {city} right now? "
        "Reply with ONLY a number in Celsius (e.g. 34.5) and the sky condition "
        "(e.g. clear sky, partly cloudy) separated by a comma. No other text."
    )
    try:
        resp = _groq.chat.completions.create(
            model=GROQ_LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=30,
        )
        raw = resp.choices[0].message.content.strip()
        # Parse "34.5, clear sky" or "34.5"
        parts = raw.split(",", 1)
        celsius = float(re.search(r"[\d.]+", parts[0]).group())
        condition = parts[1].strip() if len(parts) > 1 else "unknown"
        return _format_temps(celsius, condition, city)
    except Exception as e:
        return f"ERROR: fallback also failed for {city}: {e}"


def get_weather(args: dict) -> str:
    city = args.get("city") or DEFAULT_CITY

    # Try OpenWeatherMap first
    if OPEN_WEATHER_API_KEY:
        try:
            resp = requests.get(
                _CURRENT_URL,
                params={"q": city, "appid": OPEN_WEATHER_API_KEY, "units": "metric"},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            temp      = float(data["main"]["temp"])
            condition = (data.get("weather") or [{}])[0].get("description", "unknown")
            return _format_temps(temp, condition, city)
        except Exception:
            pass   # fall through to Groq

    # Groq fallback (API key missing or OWM request failed)
    return _groq_fallback(city)
