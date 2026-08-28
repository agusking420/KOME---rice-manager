<div align="center">

# KOME 🍚

```
 _  ___  __  __ ___
| |/ / \|  \/  | __|
|   <| () | |\/| | _|
|_|\_\\__/|_|  |_|___|
```

**🍚 Rice manager for Linux**

*Switch desktop themes with symlinks — fast, safe, reversible.*

[![License: GPLv3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/downloads/)

</div>

---

## What is KOME?

**KOME** (米) is a lightweight CLI tool that lets you switch between Linux desktop customizations (*rices*) instantly using symbolic links.

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

# Create a venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Verify installation
kome --version
```

## Guide: Your First Rice

This walkthrough takes you from zero to a working rice in 5 minutes.

### Step 1: Get a rice

Download a rice from GitHub, r/unixporn, or create your own. For example:

```bash
git clone https://github.com/someone/hyprland-catppuccin.git ~/Downloads/hyprland-catppuccin
```

### Step 2: Make sure it has the right structure

KOME expects a `.config/` directory inside the rice that mirrors your `~/.config/`. If the repo you downloaded doesn't have this structure, reorganize it:

```bash
cd ~/Downloads/hyprland-catppuccin

# Create the .config/ mirror structure
mkdir -p .config
mv hyprland/ .config/hyprland/
mv waybar/   .config/waybar/
mv kitty/    .config/kitty/
```

The final structure should look like this:

```
hyprland-catppuccin/
├── .config/
│   ├── hyprland/
│   │   └── hyprland.conf
│   ├── waybar/
│   │   ├── config.jsonc
│   │   └── style.css
│   └── kitty/
│       └── kitty.conf
├── reload.sh          ← optional but recommended
└── deps.txt           ← optional but recommended
```

### Step 3: Add a reload script (optional)

Create a `reload.sh` so KOME can restart your processes automatically:

```bash
#!/bin/bash
killall -q waybar dunst
sleep 0.5
waybar &
dunst &
hyprctl reload
```

### Step 4: Add a deps file (optional)

Create `deps.txt` listing the programs your rice needs:

```
hyprland
waybar
kitty
dunst
```

KOME will warn you if any of these are missing before applying.

### Step 5: Import it into KOME

```bash
kome add ~/Downloads/hyprland-catppuccin
```

This copies the rice into `~/.local/share/kome/rices/`.

### Step 6: Apply it

```bash
kome apply hyprland-catppuccin
```

That's it. KOME will:
1. Back up your current `~/.config/` (first time only)
2. Check your dependencies
3. Create symlinks from `~/.config/` → the rice
4. Run `reload.sh`

### Switching and going back

```bash
# See what rices you have
kome list

# Switch to a different rice
kome apply another-rice

# Go back to your original config
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

killall -q waybar dunst
sleep 0.5

waybar &
dunst &

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
# Create venv and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Run tests
pytest -v

# Run a specific test
pytest tests/test_symlinker.py::TestSymlinker::test_create_links -v
```

## License

[GPLv3](LICENSE)
