"""Open websites for Arif. Alias lookup + bare-domain detection + search fallback."""
import re
import webbrowser
from urllib.parse import quote_plus

_ALIASES: dict[str, str] = {
    "youtube":      "https://youtube.com",
    "google":       "https://google.com",
    "facebook":     "https://facebook.com",
    "whatsapp":     "https://web.whatsapp.com",
    "whatsapp web": "https://web.whatsapp.com",
    "gmail":        "https://mail.google.com",
    "instagram":    "https://instagram.com",
    "twitter":      "https://twitter.com",
    "x":            "https://x.com",
    "github":       "https://github.com",
    "linkedin":     "https://linkedin.com",
    "netflix":      "https://netflix.com",
    "amazon":       "https://amazon.com",
    "wikipedia":    "https://wikipedia.org",
}

_DOMAIN_RE = re.compile(r"^[\w.-]+\.\w{2,}$")


def open_website(args: dict) -> str:
    name = args.get("name", "").strip()
    if not name:
        return "no website name provided"

    query = name.lower().strip()

    if query in _ALIASES:
        url = _ALIASES[query]
    else:
        matched = next((v for k, v in _ALIASES.items() if query in k or k in query), None)
        if matched:
            url = matched
        elif _DOMAIN_RE.match(query):
            url = f"https://{query}"
        else:
            url = f"https://www.google.com/search?q={quote_plus(name)}"

    webbrowser.open(url)
    return f"opened {url}"
