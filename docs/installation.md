# Installation

## Pre-built binaries (recommended)

Grab the binary for your platform from [GitHub Releases](https://github.com/ritwik-g/claude-session-manager/releases). No Python required.

=== "macOS (Apple Silicon)"

    ```bash
    curl -L -o clsm https://github.com/ritwik-g/claude-session-manager/releases/latest/download/claude-session-manager-macos-arm64
    chmod +x clsm
    xattr -cr clsm                    # clear macOS quarantine
    sudo mv clsm /usr/local/bin/
    ```

=== "Linux"

    ```bash
    curl -L -o clsm https://github.com/ritwik-g/claude-session-manager/releases/latest/download/claude-session-manager-linux-x86_64
    chmod +x clsm
    sudo mv clsm /usr/local/bin/
    ```

=== "Windows"

    Download `claude-session-manager-windows-x86_64.exe` from [Releases](https://github.com/ritwik-g/claude-session-manager/releases) and place it on your `PATH`.

!!! note "macOS quarantine"
    The first time you download an unsigned binary on macOS, Gatekeeper marks it with a quarantine attribute. `xattr -cr clsm` strips that attribute so the binary can run.

## From source

```bash
git clone https://github.com/ritwik-g/claude-session-manager.git
cd claude-session-manager
pip install .
```

This installs both the `claude-session-manager` and `clsm` commands.

!!! note "Not on PyPI yet"
    This package is not yet published to PyPI, so `pip install claude-session-manager` / `pipx install claude-session-manager` won't work. Use a pre-built binary or install from source as shown above.

## Requirements

- Claude Code sessions on disk under `~/.claude/`
- Python 3.10+ (only if installing from source / pip — pre-built binaries have no Python requirement)
