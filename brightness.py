"""Brightness control for Arif. Keeps display logic isolated from the main executor."""
import screen_brightness_control as sbc


def get_brightness() -> int:
    return sbc.get_brightness()[0]


def set_brightness(level: int) -> str:
    level = max(0, min(100, level))
    sbc.set_brightness(level)
    return f"brightness set to {level}%"


def adjust_brightness(delta: int) -> str:
    current = get_brightness()
    level = max(0, min(100, current + delta))
    sbc.set_brightness(level)
    return f"brightness changed from {current}% to {level}%"
