# WSL2Manager — Project Spec

## 1. Overview

A Python desktop application that runs continuously in the background and lets the user start, stop, reboot, and open a terminal into WSL2 (and WSL1) distros without opening a terminal manually first. Lives in the system tray; the entire interface is a right-click tray menu — no separate windows.

## 2. Goals

- One-click control (start/stop/reboot/open terminal) of user-selected distros.
- Zero-friction background presence — sits in the system tray, not a heavy always-open window, no GUI toolkit dependency.
- The user explicitly chooses which distros the app manages ("maintained" distros), rather than the app assuming all installed distros are relevant.
- Windows-only (WSL2 is a Windows feature; no cross-platform requirement).

## 3. Core User Flow

1. App launches (optionally at Windows startup, opt-in) and goes straight to the system tray — single static icon (`assets/app.ico`), no idle/active variants.
2. On first run (no config file yet), every distro `wsl -l -v` reports is auto-selected as "maintained."
3. Right-click the tray icon → top-level menu lists each **maintained** distro, each with a submenu: **Start**, **Stop**, **Reboot**, **Open Terminal**.
4. Every menu open re-queries `wsl -l -v` on demand — there is no background polling or refresh timer. State shown is always current as of the last click.
5. **Manage Distros** submenu lists *every* distro `wsl -l -v` reports (WSL1 and WSL2, unfiltered) as checkable items — checking/unchecking adds/removes it from the maintained list and persists immediately.
6. **Shutdown WSL** stops the WSL2 VM entirely (`wsl --shutdown`), independent of individual distros.
7. **Start with Windows** is a checkable item, off by default; toggling it registers/unregisters the app in the Windows startup sequence.
8. **Quit** exits the tray app itself — this does not stop any running distro.
9. If `wsl.exe` can't be found when the menu is queried, the menu shows a single disabled "WSL not found" item plus Quit instead of the normal controls; re-checked on every subsequent menu open.
10. Only one instance of the app can run at a time (mutex-guarded); launching a second instance exits immediately.

## 4. Tech Stack

| Concern | Recommended library | Notes |
| --- | --- | --- |
| System tray icon | `pystray` | Tray icon + menu, including native checkable menu items (used for Manage Distros / Start with Windows). |
| Tray icon image | `Pillow` | Load `assets/app.ico` into the bitmap `pystray` needs. |
| WSL control | `subprocess` + `wsl.exe` | No native Python WSL API; wrap `wsl -l -v`, `wsl -d <name>`, `wsl -t <name>`, `wsl --shutdown`. |
| Terminal launch | `subprocess` | `wsl.exe -d <name>` directly (opens its own console host window). `wt.exe` was tried first but dropped — its CLI argument parsing collides with `wsl.exe`'s own `-d` flag and proved unreliable in testing (see section 9). |
| Single-instance guard | `pywin32` (`win32event.CreateMutex`) | Named mutex checked at startup; exit silently if already held. |
| Config/settings | `.json` file | Maintained-distro list, Start-with-Windows flag. No poll interval — on-demand model needs none. |
| Autostart on boot | Startup shortcut / registry `Run` key | Written/removed by the app itself when the "Start with Windows" item is toggled. |
| Packaging | `PyInstaller --onefile` | Single portable `.exe`, no console window, `app.ico` as the exe icon. Accepted tradeoff: slower cold start due to self-extraction, in exchange for single-file distribution. |
| Build/deps | `uv` + `pyproject.toml` | Mirrors EzTranslator: `src/` layout, `requires-python = ">=3.12"`, `PyInstaller` as a dev dependency. |

## 5. Architecture

```text
wsl2manager-app/
├── pyproject.toml
├── run.py                    # from wsl2manager_app.main import main; main()
├── src/
│   └── wsl2manager_app/
│       ├── main.py            # Entry point: single-instance guard, builds tray icon, runs pystray loop
│       ├── tray.py            # Menu construction: maintained distros, Manage Distros, Shutdown WSL, Start with Windows, Quit
│       ├── wsl/
│       │   └── controller.py  # list_distros(), start(), stop(), reboot(), open_terminal(), shutdown_all()
│       └── config.py          # Load/save %APPDATA%\WSL2Manager\config.json (maintained distros, autostart flag)
└── assets/
    └── app.ico
```

**No background thread.** `pystray`'s own event loop is the only thread running the tray; every `wsl.exe` call happens synchronously inside the menu-item callback that triggered it (menu construction included), since there's no polling loop to keep off a shared thread.

## 6. Key Features (MVP)

- [ ] Runs in system tray; single instance enforced via named mutex
- [ ] "Start with Windows" toggle in tray menu, opt-in, off by default
- [ ] Detects distros via `wsl -l -v` (name, state, version) — unfiltered by WSL version
- [ ] **Manage Distros** checkable submenu selects which distros are "maintained"; auto-selects all on first run (no config file yet)
- [ ] Per-maintained-distro **Start** / **Stop** / **Reboot** / **Open Terminal**
- [ ] Menu queries live state on demand every time it's opened — no stale cache, no timer
- [ ] **Shutdown WSL** (stops the whole WSL2 VM)
- [ ] Graceful "WSL not found" menu state if `wsl.exe` is missing
- [ ] **Quit** app (leaves distros untouched)
- [ ] Config persisted to `%APPDATA%\WSL2Manager\config.json`

## 7. Nice-to-Have (post-MVP)

- Resource usage view per distro (memory via `vmmem`/`Get-Process`, or `wsl --status`)
- Quick action: open `.wslconfig` / distro-specific `wsl.conf` in the default editor

## 8. Non-Functional Requirements

- Memory footprint: target <100MB idle.
- No admin/elevation required for normal start/stop/reboot/open-terminal operations.
- Graceful handling when WSL isn't installed or `wsl.exe` is missing (see section 3, item 9) — never crash the tray app.
- Startup time is best-effort rather than a hard target: `--onefile` packaging means a self-extraction step on every launch, which was accepted in exchange for single-file distribution (see section 4).

## 9. Resolved Decisions

- **Control granularity**: per-distro Start/Stop/Reboot/Open Terminal, scoped to explicitly user-selected "maintained" distros — not all installed distros automatically.
- **Distro selection UI**: checkable items in a "Manage Distros" tray submenu, not a separate settings window — keeps the app dependency-free of any GUI toolkit.
- **Reboot semantics**: terminate (`wsl -t <name>`) immediately followed by start (`wsl -d <name>`) — affects only that one distro, not the whole VM.
- **State freshness model**: on-demand only. No background polling thread, no poll-interval setting, no idle/active icon variants.
- **Autostart default**: opt-in, off by default.
- **First-run distro selection**: all discovered distros auto-selected as maintained; user prunes via Manage Distros.
- **Single instance**: enforced via named mutex.
- **Open Terminal implementation**: always launches `wsl.exe -d <name>` directly, no `wt.exe` involvement. Tried `wt.exe -- wsl.exe -d <name>` (documented separator) and `wt.exe -p <name>` (profile-name lookup) during testing; both were unreliable (`-d` collision / no matching profile), each producing a visible error or silently falling back to the wrong shell. Plain `wsl.exe -d <name>` was confirmed to work reliably, so the fancier "open as a tab in Windows Terminal" behavior was dropped in favor of correctness.
- **Config location/format**: `%APPDATA%\WSL2Manager\config.json`.
- **`wsl.exe` missing**: app still runs in the tray with a disabled "WSL not found" item, re-checked on every menu open, rather than exiting.
- **Open Terminal**: promoted to MVP (not deferred).
- **Desktop notifications**: dropped — incompatible with the on-demand model (nothing is watched between menu opens to notify about).
- **Distro version filtering**: none — WSL1 and WSL2 distros both shown in Manage Distros.
- **Packaging**: `PyInstaller --onefile`, accepting slower cold start for single-file portability.
- **Icon**: `assets/app.ico` (provided), not a placeholder.
- **License**: MIT, Copyright (c) 2026 Luiz Brunca — matches EzTranslator.

## 10. Development Process

- This spec was stress-tested via the `/grill-me` skill before implementation began, consistent with the EzTranslator project. Re-run it against any section that changes materially before resuming implementation.

## 11. Suggested Milestones

1. **Skeleton**: `uv`/`pyproject.toml` scaffolding, tray icon + Quit menu, single-instance mutex guard.
2. **Distro discovery**: parse `wsl -l -v`, populate Manage Distros checkable submenu, persist to `%APPDATA%\WSL2Manager\config.json`, auto-select-all on first run.
3. **Controls**: wire up Start/Stop/Reboot/Open Terminal per maintained distro, plus Shutdown WSL — all on-demand, no polling.
4. **Robustness**: "WSL not found" menu state, single-instance exit path.
5. **Start with Windows**: opt-in autostart toggle (registry `Run` key or Startup shortcut).
6. **Packaging**: `PyInstaller --onefile` build using `assets/app.ico`, no console window.
