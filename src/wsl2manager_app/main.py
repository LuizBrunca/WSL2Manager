from __future__ import annotations

import sys
from pathlib import Path

import pystray
import win32api
import win32event
import winerror
from PIL import Image

from wsl2manager_app import config
from wsl2manager_app.tray import build_menu
from wsl2manager_app.wsl import controller

_MUTEX_NAME = "Global\\WSL2Manager-SingleInstance"


def _acquire_single_instance_lock():
    handle = win32event.CreateMutex(None, False, _MUTEX_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        return None
    return handle


def _icon_image_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)
    else:
        base = Path(__file__).resolve().parents[2]
    return base / "assets" / "app.ico"


def _ensure_first_run_seeded() -> None:
    cfg = config.load()
    if cfg.maintained_distros is not None:
        return
    try:
        cfg.maintained_distros = [d.name for d in controller.list_distros()]
    except controller.WslNotFoundError:
        cfg.maintained_distros = []
    config.save(cfg)


def main() -> None:
    lock = _acquire_single_instance_lock()
    if lock is None:
        return

    _ensure_first_run_seeded()

    image = Image.open(_icon_image_path())
    icon = pystray.Icon("WSL2Manager", image, "WSL2Manager", menu=build_menu())
    icon.run()
