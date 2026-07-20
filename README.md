# WSL2Manager

Background system-tray app to start, stop, reboot, and open terminals into WSL distros — no console commands required. See [wsl2manager-app-spec.md](wsl2manager-app-spec.md) for the full design.

## Development

```
uv sync
uv run run.py
```

## Packaging

```
uv run pyinstaller --onefile --noconsole --icon assets/app.ico --add-data "assets/app.ico;assets" --name wsl2manager-app run.py
```
