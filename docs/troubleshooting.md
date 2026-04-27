# Troubleshooting

## `clsm: command not found`

The binary isn't on your `PATH`. Either move it into `/usr/local/bin/` or invoke it with its full path.

## macOS: "cannot be opened because the developer cannot be verified"

Run `xattr -cr clsm` to clear the quarantine attribute. macOS marks downloaded unsigned binaries as quarantined; this strips that flag.

## Web UI port already in use

Pass `--port <n>` to bind somewhere else:

```bash
clsm --web --port 9000
```

## Empty session list

`clsm` reads from `~/.claude/`. If you've never run Claude Code, or your sessions live elsewhere, there's nothing to show.

## Clipboard copy doesn't work

The TUI's `c` action tries OSC 52, `pbcopy`, and `xclip` in order. If all three are unavailable (e.g. headless Linux without `xclip` and no OSC-52-aware terminal), the copy will silently no-op. Install `xclip` or use a terminal that supports OSC 52 (iTerm2, kitty, WezTerm, modern xterm, etc.).

## Still stuck?

Open an issue at [github.com/ritwik-g/claude-session-manager/issues](https://github.com/ritwik-g/claude-session-manager/issues) with your platform, install method, and what you tried.
