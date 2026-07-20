from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass


class WslNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class Distro:
    name: str
    state: str
    version: str
    is_default: bool

    @property
    def is_running(self) -> bool:
        return self.state.strip().lower() == "running"


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(
            ["wsl.exe", *args],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
            check=False,
        )
    except FileNotFoundError as exc:
        raise WslNotFoundError("wsl.exe was not found on this machine") from exc
    text = result.stdout.decode("utf-16-le", errors="ignore")
    return text.lstrip(chr(0xFEFF)).strip()


def list_distros() -> list[Distro]:
    output = _run(["-l", "-v"])
    distros: list[Distro] = []
    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        is_default = line.startswith("*")
        parts = line.lstrip("*").split()
        if not parts or parts[0].upper() == "NAME":
            continue
        name = parts[0]
        state = parts[1] if len(parts) > 1 else "Unknown"
        version = parts[2] if len(parts) > 2 else "1"
        distros.append(Distro(name=name, state=state, version=version, is_default=is_default))
    return distros


def start(name: str) -> None:
    try:
        subprocess.Popen(
            ["wsl.exe", "-d", name, "--", "sleep", "infinity"],
            creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
        )
    except FileNotFoundError as exc:
        raise WslNotFoundError("wsl.exe was not found on this machine") from exc


def stop(name: str) -> None:
    _run(["--terminate", name])


def reboot(name: str) -> None:
    stop(name)
    start(name)


def shutdown_all() -> None:
    _run(["--shutdown"])


def open_terminal(name: str) -> None:
    wt_path = shutil.which("wt.exe") or shutil.which("wt")
    try:
        if wt_path:
            subprocess.Popen([wt_path, "wsl.exe", "-d", name])
        else:
            subprocess.Popen(["wsl.exe", "-d", name])
    except FileNotFoundError as exc:
        raise WslNotFoundError("wsl.exe was not found on this machine") from exc
