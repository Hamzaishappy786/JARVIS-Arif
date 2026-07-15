"""Hibernate the PC."""
from ._power_utils import run


def hibernate_pc(_args: dict = None) -> str:
    run("shutdown", "/h")
    return "hibernating"
