"""
Dictation into Notepad/Word. Re-transcribes the same utterance's audio natively in
Urdu script (the LLM only ever sees an English translation, useless for typing real
Urdu), then pastes it via the clipboard into whichever editor window is focused.
"""
import time

import pygetwindow as gw
import pyautogui
import win32clipboard
import win32con

from .stt import transcribe_urdu_native

_TARGET_HINTS = ["notepad", "word", "wordpad"]


def _focus_target_window() -> str | None:
    for win in gw.getAllWindows():
        title = win.title.lower()
        if win.title.strip() and any(hint in title for hint in _TARGET_HINTS):
            win.activate()
            time.sleep(0.3)   # let window focus settle before injecting keys
            return win.title
    return None


def _set_clipboard_unicode(text: str):
    win32clipboard.OpenClipboard()
    win32clipboard.EmptyClipboard()
    win32clipboard.SetClipboardData(win32con.CF_UNICODETEXT, text)
    win32clipboard.CloseClipboard()


def dictate(args: dict) -> str:
    audio_path = args.get("audio_path", "")
    if not audio_path:
        return "ERROR: no audio_path provided for dictation"

    urdu_text = transcribe_urdu_native(audio_path)
    if not urdu_text:
        return "ERROR: could not transcribe dictation audio"

    window_title = _focus_target_window()
    if not window_title:
        return "ERROR: no Notepad/Word window found to dictate into"

    _set_clipboard_unicode(urdu_text)
    pyautogui.hotkey("ctrl", "v")

    return f"dictated into '{window_title}': {urdu_text}"
