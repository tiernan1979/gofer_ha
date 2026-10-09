# Gofer

A Go companion agent for Home Assistant — the Go-flavoured sibling of HASS.Agent.

Gofer runs on your devices, sends telemetry sensors to Home Assistant, exposes
buttons/switches to run commands (including arbitrary executables), receives
notifications, and appears as a media player. Configuration happens from a
tray icon + desktop window.

## Status

In development: agent, integration, desktop app, notifications, media
player, packaging and extras (M0–M9) are implemented; the client expansion
(frameless GUI with sensor/command editors, diagnostics log, Windows
installer) is in.

## Features

- 18 built-in sensors — cpu_load, memory_usage, storage, network_rx/tx,
  battery, uptime, last_boot, hostname, os_version, ip_address, load_avg,
  temperature, process_count, process_running, ping, public_ip, gpu_usage —
  published to MQTT with HA discovery (units/device classes included)
- Commands: buttons and switches — run executables, open URIs, lock the
  session, power/volume actions, per-device `execute`/`switch` platforms
- Notifications: sent from Home Assistant with the `gofer.notify` service
  or the notify entity (`notify.send_message`); the agent shows them
  natively (DBus/PowerShell toast/osascript) and action buttons post
  `gofer_notification_action` back to Home Assistant
- Media player: HA media_player entity controls the agent (play/pause/stop,
  volume) via MPRIS on Linux and media keys on Windows
- Tray icon + frameless desktop window (Wails v2) with sidebar navigation:
  connection setup, quick-add sensor/command templates, editors,
  notification settings with test button, diagnostics (live log with
  levels, config path), headless builds for servers/CI, per-user
  installers (systemd/launchd)

## Installation

Build from source (Go 1.26+):

```sh
make gui        # desktop app (linux also needs libgtk-3-dev libwebkit2gtk-4.1-dev)
make build      # headless daemon (bin/goferd)
```

Linux — per-user systemd service:

```sh
./scripts/install-linux.sh gui      # or: headless
```

macOS — per-user launchd agent:

```sh
./scripts/install-macos.sh gui      # or: headless
```

Windows — installer (Add/Remove Programs, Start menu, autostart):

```powershell
.\gofer-installer.exe
```

`gofer-installer.exe /no-autostart` skips the login-start entry,
`/uninstall` removes Gofer. Alternatively a logon scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install-windows.ps1
```

Uninstall: `./scripts/uninstall.sh` (linux/macos) or
`scripts\install-windows.ps1 -Uninstall`. Tagged releases are built by
`.github/workflows/release.yml`; `make dist VERSION=x.y.z` packages locally.

## Configuration

Interactive setup (both binaries):

```sh
./bin/goferd setup          # or: ./bin/gofer setup
./bin/goferd check          # verify MQTT + Home Assistant connectivity
./bin/goferd sensors        # print current values of all configured sensors
```

Flags (`-ha-url`, `-ha-token`, `-mqtt-host`, …) make `setup` scriptable.
First run creates the config at `~/.config/gofer/gofer.yaml`
(`$XDG_CONFIG_HOME` respected) on linux/macOS, `%APPDATA%\gofer\gofer.yaml`
on Windows — see `config.example.yaml` for all fields. The desktop app
edits it from the tray window.

## Layout

| Path | Purpose |
|---|---|
| `cmd/goferd/` | Headless daemon (services, servers, CI builds) |
| `cmd/gofer/` | Desktop app: tray + config window + daemon, with embedded frontend (M5) |
| `cmd/gofer-installer/` | Windows installer (Add/Remove Programs, Start menu, autostart) |
| `internal/` | Shared daemon code (config, transports, sensors, commands, notify, media player, app control) |
| `custom_components/gofer/` | Home Assistant integration (HACS) |
| `packaging/` | systemd units, launchd plists |
| `scripts/` | Install/uninstall scripts (linux, macos, windows) |
| `winres/` | Windows icon/version resources (go-winres) |

## Development

```sh
make check        # vet + tests + python compile check
make check-gui    # typecheck GUI code (windows cross-build)
make build        # bin/goferd
make gui          # bin/gofer (needs libgtk-3-dev + libwebkit2gtk-4.1-dev)
make gui-win      # bin/gofer-windows-amd64.exe (no CGO needed)
make installer    # bin/gofer-installer.exe (windows installer with embedded app)
make winres       # regenerate windows icon/version resources (go-winres)
make cross        # linux amd64/arm64 + windows amd64 (headless)
make lint         # golangci-lint (if installed)
```

The desktop app (`cmd/gofer`) is built with the `gui` + `production` tags
(Wails v2 requires `production` for the real app runner; without it the
binary shows a "correct build tags" error dialog). Default builds are
headless CGO-free binaries that run the same agent. Linux GUI builds
additionally need the `webkit2_41` tag — use the make targets, they set
everything:

## Integration

Install `custom_components/gofer` via HACS (or copy it into
`<config>/custom_components/`), restart Home Assistant, then add the
"Gofer" integration.

- Devices are announced automatically over MQTT (retained announcement →
  config flow), no manual entry needed
- Sensors and commands are registered once via MQTT discovery (retained,
  stable unique ids) — the agent re-publishes them after a broker
  reconnect, Home Assistant ignores unchanged payloads
- Notifications: `gofer.notify` (targets device_id, supports action
  buttons) or the per-device notify entity via `notify.send_message`
- Media player entity: play/pause/stop and volume control
- Device options: rename the device; diagnostics are available from the
  device page (Developer tools → Actions → Download diagnostics)
