from __future__ import annotations

import functools
import sys
import winreg
from pathlib import Path

import pystray

from wsl2manager_app import config
from wsl2manager_app.wsl import controller

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_RUN_VALUE_NAME = "WSL2Manager"


def _startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    script = Path(__file__).resolve().parents[2] / "run.py"
    return f'"{pythonw}" "{script}"'


def is_autostart_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, _RUN_VALUE_NAME)
        return True
    except FileNotFoundError:
        return False


def set_autostart_enabled(enabled: bool) -> None:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, _RUN_VALUE_NAME, 0, winreg.REG_SZ, _startup_command())
        else:
            try:
                winreg.DeleteValue(key, _RUN_VALUE_NAME)
            except FileNotFoundError:
                pass


def _on_start(name: str, icon: pystray.Icon, item: pystray.MenuItem) -> None:
    controller.start(name)


def _on_stop(name: str, icon: pystray.Icon, item: pystray.MenuItem) -> None:
    controller.stop(name)


def _on_reboot(name: str, icon: pystray.Icon, item: pystray.MenuItem) -> None:
    controller.reboot(name)


def _on_open_terminal(name: str, icon: pystray.Icon, item: pystray.MenuItem) -> None:
    controller.open_terminal(name)


def _distro_submenu(distro: controller.Distro) -> pystray.Menu:
    return pystray.Menu(
        pystray.MenuItem(
            "Start", functools.partial(_on_start, distro.name), enabled=not distro.is_running
        ),
        pystray.MenuItem(
            "Stop", functools.partial(_on_stop, distro.name), enabled=distro.is_running
        ),
        pystray.MenuItem(
            "Reboot", functools.partial(_on_reboot, distro.name), enabled=distro.is_running
        ),
        pystray.MenuItem("Open Terminal", functools.partial(_on_open_terminal, distro.name)),
    )


def _const(value: bool):
    return lambda item: value


def _on_toggle_maintained(name: str, icon: pystray.Icon, item: pystray.MenuItem) -> None:
    cfg = config.load()
    maintained = set(cfg.maintained_distros or [])
    if name in maintained:
        maintained.discard(name)
    else:
        maintained.add(name)
    cfg.maintained_distros = sorted(maintained)
    config.save(cfg)


def _manage_distros_menu(
    distros: list[controller.Distro], maintained: set[str]
) -> pystray.Menu:
    return pystray.Menu(
        *(
            pystray.MenuItem(
                d.name,
                functools.partial(_on_toggle_maintained, d.name),
                checked=_const(d.name in maintained),
            )
            for d in distros
        )
    )


def _on_shutdown_all(icon: pystray.Icon, item: pystray.MenuItem) -> None:
    controller.shutdown_all()


def _on_toggle_autostart(icon: pystray.Icon, item: pystray.MenuItem) -> None:
    set_autostart_enabled(not is_autostart_enabled())


def _on_quit(icon: pystray.Icon, item: pystray.MenuItem) -> None:
    icon.stop()


def _build_menu_items() -> tuple[pystray.MenuItem, ...]:
    try:
        distros = controller.list_distros()
    except controller.WslNotFoundError:
        return (
            pystray.MenuItem("WSL not found", lambda icon, item: None, enabled=False),
            pystray.MenuItem("Quit", _on_quit),
        )

    maintained = set(config.load().maintained_distros or [])
    maintained_distros = [d for d in distros if d.name in maintained]

    items: list[pystray.MenuItem] = []
    for d in maintained_distros:
        label = f"{d.name} ({d.state})"
        if d.is_default:
            label += " *"
        items.append(pystray.MenuItem(label, _distro_submenu(d)))

    if items:
        items.append(pystray.Menu.SEPARATOR)

    items.append(pystray.MenuItem("Manage Distros", _manage_distros_menu(distros, maintained)))
    items.append(pystray.MenuItem("Shutdown WSL", _on_shutdown_all))
    items.append(pystray.Menu.SEPARATOR)
    items.append(
        pystray.MenuItem(
            "Start with Windows", _on_toggle_autostart, checked=_const(is_autostart_enabled())
        )
    )
    items.append(pystray.Menu.SEPARATOR)
    items.append(pystray.MenuItem("Quit", _on_quit))
    return tuple(items)


def build_menu() -> pystray.Menu:
    return pystray.Menu(_build_menu_items)
