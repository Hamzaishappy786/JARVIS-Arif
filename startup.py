"""
Startup banner, spinner, and ready screen for Arif.
Suppresses noisy library warnings before any heavy import happens.
"""
import os
import sys
import time
import threading
import itertools

# ── UTF-8 output + ANSI colours on Windows ────────────────────────────────────
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
os.system("")

# ── Colour palette ─────────────────────────────────────────────────────────────
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
CYAN   = "\033[38;5;51m"
ORANGE = "\033[38;5;214m"
WHITE  = "\033[97m"
GREY   = "\033[38;5;242m"
GREEN  = "\033[38;5;82m"
RED    = "\033[38;5;196m"

BANNER = f"""
{CYAN}{BOLD}
  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
  ░                                                     ░
  ░   {ORANGE}     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗      {CYAN}░
  ░   {ORANGE}     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝      {CYAN}░
  ░   {ORANGE}     ██║███████║██████╔╝██║   ██║██║███████╗      {CYAN}░
  ░   {ORANGE}██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║      {CYAN}░
  ░   {ORANGE}╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║      {CYAN}░
  ░   {ORANGE} ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝      {CYAN}░
  ░                                                     ░
  ░          {WHITE}A  R  I  F    —    عارف{CYAN}                    ░
  ░       {GREY}Your Personal Urdu AI Voice Assistant{CYAN}         ░
  ░                                                     ░
  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░
{RESET}"""

READY_LINE = f"\n  {GREEN}{BOLD}✓{RESET}  {WHITE}Arif is online — {ORANGE}Hold [F9] to talk{RESET}\n"


class Spinner:
    """Animated spinner that runs in a background thread."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, label: str = "Initializing"):
        self._label   = label
        self._stop    = threading.Event()
        self._thread  = threading.Thread(target=self._spin, daemon=True)

    def _spin(self):
        for frame in itertools.cycle(self.FRAMES):
            if self._stop.is_set():
                break
            sys.stdout.write(
                f"\r  {CYAN}{BOLD}{frame}{RESET}  {WHITE}{self._label}…{RESET}   "
            )
            sys.stdout.flush()
            time.sleep(0.08)
        # Clear the spinner line
        sys.stdout.write("\r" + " " * 60 + "\r")
        sys.stdout.flush()

    def start(self, label: str | None = None):
        if label:
            self._label = label
        self._thread.start()
        return self

    def stop(self):
        self._stop.set()
        self._thread.join()


def show_banner():
    """Clear the screen and print the startup banner."""
    os.system("cls")
    print(BANNER)


def show_ready():
    """Replace spinner area with the green ready message."""
    print(READY_LINE)


def choose_mode() -> str:
    """
    Prompt the user to choose input mode.
    Returns "ptt" (push-to-talk) or "vad" (always-on).
    Saves the choice to a temp file so it persists across the session.
    """
    print(f"""  {CYAN}┌──────────────────────────────────────────────────┐
  │{WHITE}{BOLD}              SELECT INPUT MODE                   {CYAN}│
  ├──────────────────────────────────────────────────┤
  │  {ORANGE}[1]{WHITE}  Push-to-Talk   —  Hold F9 each time          {CYAN}│
  │  {ORANGE}[2]{WHITE}  Always-On Mic  —  Speak freely, auto-detect{CYAN}│
  └──────────────────────────────────────────────────┘{RESET}
""")

    print(f"  {WHITE}History saved to:{RESET} {GREY}logs/history.json  &  logs/conversation.txt{RESET}\n")
    print(f"  {ORANGE}>{RESET} ", end="", flush=True)

    while True:
        choice = input().strip()
        if choice in ("1", "ptt", "f9", "push"):
            print(f"\n  {GREEN}{BOLD}✓{RESET}  {WHITE}Push-to-Talk mode selected.{RESET}\n")
            return "ptt"
        elif choice in ("2", "vad", "always", "open"):
            print(f"\n  {GREEN}{BOLD}✓{RESET}  {WHITE}Always-On Mic mode selected.{RESET}\n")
            return "vad"
        else:
            print(f"  Enter {ORANGE}1{RESET} or {ORANGE}2{RESET}: ", end="", flush=True)


def suppress_warnings():
    """
    Silence the noisy third-party warnings that appear on every startup
    (requests urllib3 mismatch, huggingface resume_download, transformers tokens).
    """
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", message=".*resume_download.*")
    warnings.filterwarnings("ignore", message=".*urllib3.*")
    warnings.filterwarnings("ignore", message=".*chardet.*")
    warnings.filterwarnings("ignore", message=".*Special tokens.*")

    # Also suppress via env vars (caught before Python warnings system)
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    # Redirect stderr temporarily while heavy libs import
    # (some warnings go straight to stderr, bypassing warnings module)
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("DATASETS_VERBOSITY", "error")
