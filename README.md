# Claude Session Manager

A TUI and Web UI for viewing, searching, and managing your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) sessions.

## Features

- **TUI** - Interactive terminal UI with sorting, filtering, and session details (built with [Textual](https://textual.textualize.io/))
- **Web UI** - Browser-based interface with bulk selection and deletion
- **Quick list** - Fast terminal table output
- **Stats** - Aggregate session statistics per project
- **Session deletion** - Clean up old sessions (JSONL, tool results, file history)
- **Search** - Filter by project, topic, branch, or message content

## Installation

### Via pip / pipx (recommended)

```bash
pip install claude-session-manager
# or
pipx install claude-session-manager
```

### Pre-built binaries

Download the binary for your platform from [GitHub Releases](https://github.com/ritwik-g/claude-session-manager/releases).

On macOS, you may need to clear the quarantine flag:

```bash
xattr -cr claude-session-manager-macos-arm64
chmod +x claude-session-manager-macos-arm64
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
| `/` | Filter/search |
| `Enter` | Session details |
| `d` | Delete session |
| `s` | Cycle sort (date/project/messages/size) |
| `r` | Refresh |
| `q` | Quit |

## Requirements

- Python 3.10+ (not needed for pre-built binaries)
- Claude Code sessions at `~/.claude/`

## License

MIT
