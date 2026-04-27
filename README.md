# Claude Session Manager

A TUI and Web UI for viewing, searching, and managing your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) sessions.

📖 **[Documentation](https://ritwik-g.github.io/claude-session-manager/)**

https://github.com/user-attachments/assets/2cc5c650-0719-482d-ae73-da97af236cdf

## Features

- **TUI** - Interactive terminal UI with project navigation, sorting, filtering, and session details (built with [Textual](https://textual.textualize.io/))
- **Web UI** - Browser-based interface with project sidebar, bulk selection, and deletion
- **Quick list** - Fast terminal table output
- **Stats** - Aggregate session statistics per project
- **Usage breakdown** - Per-session token totals (input / output / cache read / cache write), cache hit ratio, model(s), and web tool counts in the detail view
- **Session deletion** - Clean up old sessions (JSONL, tool results, file history)
- **Search** - Filter by project, topic, branch, or message content
- **Resume** - Copy resume commands or open sessions directly in a new terminal

## Installation

### Pre-built binaries

Download the binary for your platform from [GitHub Releases](https://github.com/ritwik-g/claude-session-manager/releases).

**macOS (Apple Silicon):**

```bash
# Download
curl -L -o clsm https://github.com/ritwik-g/claude-session-manager/releases/latest/download/claude-session-manager-macos-arm64

# Make executable and clear quarantine
chmod +x clsm
xattr -cr clsm

# Move to PATH (optional)
sudo mv clsm /usr/local/bin/
```

**Linux:**

```bash
curl -L -o clsm https://github.com/ritwik-g/claude-session-manager/releases/latest/download/claude-session-manager-linux-x86_64
chmod +x clsm
sudo mv clsm /usr/local/bin/
```

**Windows:**

Download `claude-session-manager-windows-x86_64.exe` from [Releases](https://github.com/ritwik-g/claude-session-manager/releases).

### Via pip / pipx

```bash
pip install claude-session-manager
# or
pipx install claude-session-manager
```

### From source

```bash
git clone https://github.com/ritwik-g/claude-session-manager.git
cd claude-session-manager
pip install .
```

## Usage

```bash
claude-session-manager          # TUI (default)
claude-session-manager --web    # Web UI (opens browser)
claude-session-manager --list   # Quick terminal list
claude-session-manager --stats  # Aggregate stats

clsm                           # Short alias for all above
clsm --web --port 9000         # Custom port for web UI
```

### TUI Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Switch between project list and session table |
| `Enter` | Select project (left panel) / View session details (right panel) |
| `c` | Copy resume command to clipboard |
| `o` | Open session in a new terminal tab |
| `d` | Delete session |
| `/` | Filter/search |
| `s` | Cycle sort (date/messages/size) |
| `r` | Refresh |
| `?` | Show help |
| `q` | Quit |

## Requirements

- Python 3.10+ (not needed for pre-built binaries)
- Claude Code sessions at `~/.claude/`

## License

MIT
