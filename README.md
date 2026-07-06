# Claude Session Manager

A TUI and Web UI for viewing, searching, and managing your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) sessions.

📖 **[Documentation](https://ritwik-g.github.io/claude-session-manager/)**

https://github.com/user-attachments/assets/2cc5c650-0719-482d-ae73-da97af236cdf

## Features

- **Session titles & summaries** - Every session is identified by its name and AI-generated summary instead of a raw first message, so you can recognize sessions at a glance
- **Folder-tree navigation** - Projects are shown as the real on-disk folder hierarchy (worktrees and sub-repos nest where they actually live), not a flat list
- **TUI** - Interactive terminal UI with folder navigation, recency/title/size sorting, full-text filtering, and session details (built with [Textual](https://textual.textualize.io/))
- **Web UI** - Browser-based interface with a collapsible folder tree, bulk selection, and deletion
- **Quick list** - Fast terminal table output
- **Stats** - Aggregate session statistics per project
- **Usage breakdown** - Per-session token totals (input / output / cache read / cache write), cache hit ratio, model(s), and web tool counts in the detail view
- **Session deletion** - Clean up old sessions (JSONL, tool results, file history)
- **Search** - Filter by title, summary, message content, project, or branch
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

### From source

```bash
git clone https://github.com/ritwik-g/claude-session-manager.git
cd claude-session-manager
pip install .
```

> **Note:** This package is not yet published to PyPI, so `pip install claude-session-manager` / `pipx install claude-session-manager` won't work. Use a pre-built binary or install from source as shown above.

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
