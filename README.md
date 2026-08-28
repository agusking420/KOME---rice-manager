<h1 align="center">
 KOME 🍚</h1>
```text
 ██╗  ██╗  ██████╗ ███╗   ███╗███████╗
 ██║ ██╔╝ ██╔═══██╗████╗ ████║██╔════╝
 █████═╝  ██║   ██║██╔████╔██║█████╗  
 ██╔═██╗  ██║   ██║██║╚██╔╝██║██╔══╝  
 ██║ ╚██╗ ╚██████╔╝██║ ╚═╝ ██║███████╗
 ╚═╝  ╚═╝  ╚═════╝ ╚═╝     ╚═╝╚══════╝

**🍚 Rice manager for Linux**

*Switch desktop themes with symlinks — fast, safe, reversible.*

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/downloads/)

</div>

---

## What is KOME?

**KOME** (米, Japanese for *rice*) is a lightweight CLI tool that lets you switch between Linux desktop customizations (*rices*) instantly using symbolic links.

Instead of copying and overwriting your dotfiles — risking data loss and leaving orphan configs behind — KOME creates symlinks from `~/.config/` to a centralized rice directory. Switching themes is instant, safe, and fully reversible.

### Why symlinks?

| Approach | Risk | Cleanup |
|---|---|---|
| Copy & overwrite | Destroys original configs | Manual |
| **Symlinks (KOME)** | **Zero — originals untouched** | **Automatic** |

## Features

- **🔗 Symlink-based** — No files are copied or destroyed
- **💾 Automatic backup** — Your original `~/.config/` is archived on first run
- **🔄 Hot reload** — Each rice can include a `reload.sh` to restart WM, bars, etc.
- **📦 Dependency checking** — Warns you about missing programs before applying
- **🗺️ Extra mappings** — Support files outside `~/.config/` (`.Xresources`, `.bashrc`, etc.)
- **📁 Archive import** — Add rices from `.zip` or `.tar.gz` files
- **🛡️ Conflict safety** — Existing files are renamed to `.bak`, never deleted
- **📊 Status & integrity** — Verify your symlinks haven't been broken

## Installation

```bash
# Clone the repo
git clone https://github.com/agusdev/kome.git
cd kome

# Install in development mode
pip install -e .

# Verify installation
kome --version
```

## Quick Start

```bash
# 1. Add a rice from a local directory
kome add ~/Downloads/cyber-neon

# 2. See what's available
kome list

# 3. Apply it!
kome apply cyber-neon

# 4. Check status
kome status

# 5. Don't like it? Go back to your original setup
kome restore
```

## Commands

| Command | Description |
|---|---|
| `kome list` | List all available rices |
| `kome apply <name>` | Apply a rice (creates symlinks + runs reload) |
| `kome restore` | Restore original config from backup |
| `kome status` | Show active rice and symlink integrity |
| `kome add <path>` | Import a rice from directory or archive |
| `kome remove <name>` | Remove a rice from the library |

### Flags

| Flag | Command | Description |
|---|---|---|
| `--force`, `-f` | `apply` | Skip dependency checks, reapply even if active |
| `--no-reload` | `apply` | Don't run `reload.sh` after applying |

### Aliases

- `kome ls` → `kome list`
- `kome switch` → `kome apply`
- `kome rm` → `kome remove`

## Rice Structure

A rice is a directory with this structure:

```
my-rice/
├── .config/              # [REQUIRED*] Mirror of ~/.config/
│   ├── hyprland/
│   ├── waybar/
│   ├── kitty/
│   └── ...
├── reload.sh             # [OPTIONAL] Script to restart processes
├── deps.txt              # [OPTIONAL] Required programs (one per line)
├── mapping.json          # [OPTIONAL] Extra links outside ~/.config/
├── preview.jpg           # [OPTIONAL] Screenshot of the rice
└── README.md             # [OPTIONAL] Documentation
```

> *`.config/` is required unless `mapping.json` is present.

### `deps.txt`

List the programs your rice needs, one per line. Comments (`#`) and blank lines are ignored.

```
hyprland
waybar
kitty
rofi
dunst
```

KOME checks these with `which` before applying and warns you about missing ones.

### `mapping.json`

For files that live outside `~/.config/` (like `~/.Xresources` or `~/.bashrc`):

```json
{
  "extra_links": [
    { "source": ".Xresources", "target": "~/.Xresources" },
    { "source": "wallpapers",  "target": "~/Pictures/wallpapers" }
  ]
}
```

- `source`: Path relative to the rice directory
- `target`: Absolute destination path (`~` is expanded)

### `reload.sh`

A bash script that restarts the processes affected by your rice. Example for Hyprland:

```bash
#!/bin/bash

# Kill existing instances
killall -q waybar dunst

# Wait for processes to close
sleep 0.5

# Restart
waybar &
dunst &

# Reload Hyprland config
hyprctl reload
```

## How It Works

```
~/.config/i3      →  ~/.local/share/kome/rices/cyber-neon/.config/i3
~/.config/polybar →  ~/.local/share/kome/rices/cyber-neon/.config/polybar
~/.config/kitty   →  ~/.local/share/kome/rices/cyber-neon/.config/kitty
```

When you run `kome apply`, KOME:

1. **Backs up** your `~/.config/` to a `.tar.gz` (first time only)
2. **Checks dependencies** from `deps.txt`
3. **Removes** symlinks from the previous rice
4. **Backs up** conflicting files to `.bak`
5. **Creates** new symlinks pointing to the rice
6. **Records** everything in `state.json`
7. **Runs** `reload.sh` to restart your environment

## File Locations

KOME follows the [XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/latest/):

| Path | Purpose |
|---|---|
| `~/.local/share/kome/rices/` | Rice storage |
| `~/.local/share/kome/backups/` | Full config backups |
| `~/.local/state/kome/state.json` | Active state tracking |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest -v

# Run a specific test
pytest tests/test_symlinker.py::TestSymlinker::test_create_links -v
```

## License

[GPLv3](LICENSE)
