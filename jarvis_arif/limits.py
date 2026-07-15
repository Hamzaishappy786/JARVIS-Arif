"""Show Arif's accurate API limits using local call tracking + Groq TPM header."""
import shutil
import re

from groq import Groq
from .config import GROQ_API_KEY, GROQ_LLM_MODEL
from .usage import get_stats

# ── ANSI colours ──────────────────────────────────────────────────────────────
_B  = "\033[38;5;39m"
_LB = "\033[38;5;75m"
_W  = "\033[97m"
_G  = "\033[38;5;82m"
_Y  = "\033[38;5;226m"
_R  = "\033[38;5;196m"
_BD = "\033[1m"
_RS = "\033[0m"

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")
_groq    = Groq(api_key=GROQ_API_KEY)


def _vlen(s: str) -> int:
    return len(_ANSI_RE.sub("", s))

def _rpad(s: str, width: int) -> str:
    return s + " " * max(0, width - _vlen(s))

def _cpad(s: str, width: int) -> str:
    gap = max(0, width - _vlen(s))
    return " " * (gap // 2) + s + " " * (gap - gap // 2)


def _color_rem(used: int, limit: int) -> str:
    remaining = max(0, limit - used)
    rem_s = f"{remaining:,}" if remaining >= 1_000 else str(remaining)
    lim_s = f"{limit:,}"    if limit     >= 1_000 else str(limit)
    pct   = remaining / limit if limit else 1
    color = _G if pct > 0.5 else (_Y if pct > 0.2 else _R)
    return f"{color}{rem_s}{_RS}{_LB}/{_RS}{_W}{lim_s}{_RS}"


def _fetch_tpm() -> tuple[int, int]:
    """Make one minimal Groq call and read TPM headers. Returns (remaining, limit)."""
    try:
        raw = _groq.with_raw_response.chat.completions.create(
            model=GROQ_LLM_MODEL,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        h = raw.headers
        return (
            int(h.get("x-ratelimit-remaining-tokens", -1)),
            int(h.get("x-ratelimit-limit-tokens", 6_000)),
        )
    except Exception:
        return (-1, 6_000)


def show_limits():
    term_cols = shutil.get_terminal_size((80, 20)).columns

    stats          = get_stats()
    llm            = stats["llm"]
    wh             = stats["whisper"]
    tpm_rem, tpm_lim = _fetch_tpm()

    # ── Build colored cell values ─────────────────────────────────────────────
    llm_rpm = _color_rem(llm["last_minute"], 30)
    llm_rpd = _color_rem(llm["today"],       14_400)
    llm_tpm = (
        f"{_LB}N/A{_RS}" if tpm_rem < 0
        else _color_rem(tpm_lim - tpm_rem, tpm_lim)
    )

    wh_rpm  = _color_rem(wh["last_minute"], 20)
    wh_rpd  = _color_rem(wh["today"],       2_000)
    wh_tpm  = f"{_LB}N/A{_RS}"

    rows = [
        ("LLaMA 3.1 8B (Brain)", llm_rpm, llm_rpd, llm_tpm),
        ("Whisper (Ears)",        wh_rpm,  wh_rpd,  wh_tpm),
    ]

    # ── Column widths (visual) ────────────────────────────────────────────────
    col_svc = max(len("Service"), max(len(r[0]) for r in rows)) + 2
    col_rpm = max(len("RPM"),     max(_vlen(r[1]) for r in rows)) + 2
    col_rpd = max(len("RPD"),     max(_vlen(r[2]) for r in rows)) + 2
    col_tpm = max(len("TPM"),     max(_vlen(r[3]) for r in rows)) + 2
    inner   = 2 + col_svc + col_rpm + col_rpd + col_tpm + 2

    def box_row(c1, c2, c3, c4) -> str:
        body = "  " + _rpad(c1, col_svc) + _cpad(c2, col_rpm) + _cpad(c3, col_rpd) + _cpad(c4, col_tpm) + "  "
        return f"{_B}{_BD}║{_RS}{body}{_B}{_BD}║{_RS}"

    title = "⚡  ARIF'S LIMITS  (remaining / max)"
    lines = [
        f"{_B}{_BD}╔{'═' * inner}╗{_RS}",
        f"{_B}{_BD}║{_RS}{_W}{_BD}{_cpad(title, inner)}{_RS}{_B}{_BD}║{_RS}",
        f"{_B}{_BD}╠{'═' * inner}╣{_RS}",
        box_row(f"{_LB}{_BD}Service{_RS}", f"{_LB}{_BD}RPM{_RS}",
                f"{_LB}{_BD}RPD{_RS}",    f"{_LB}{_BD}TPM{_RS}"),
        f"{_B}║{'─' * inner}║{_RS}",
    ]
    for svc, rpm, rpd, tpm in rows:
        lines.append(box_row(f"{_W}{svc}{_RS}", rpm, rpd, tpm))
    lines.append(f"{_B}{_BD}╚{'═' * inner}╝{_RS}")

    indent  = max(0, term_cols - inner - 6)
    pad_str = " " * indent

    print()
    for line in lines:
        print(pad_str + line)
    print()

    from .tts import speak
    speak("یہ لیجیے سر")
