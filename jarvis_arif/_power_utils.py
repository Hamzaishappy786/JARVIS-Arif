"""Shared helpers for power-management modules."""
import subprocess
import sys
from pathlib import Path


def run(*cmd):
    subprocess.Popen(list(cmd), shell=False)


def register_startup():
    try:
        import winreg
        run_py  = str(Path(__file__).parent.parent / "run.py")
        cmd_str = f'"{sys.executable}" "{run_py}"'
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "JarvisArif", 0, winreg.REG_SZ, cmd_str)
        winreg.CloseKey(key)
    except Exception:
        pass


def unregister_startup():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, "JarvisArif")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass
