# TUI

If you prefer the terminal, just run:

```bash
clsm
```

You get the same data in a Textual-powered TUI: project list on the left, sessions on the right, full keyboard navigation.

## Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Switch focus between project list and session table |
| `Enter` | Select project (left) / open session details (right) |
| `c` | Copy `claude --resume` command for the selected session |
| `o` | Open the session in a new terminal tab |
| `d` | Delete the selected session |
| `/` | Filter / search |
| `s` | Cycle sort order (date / messages / size) |
| `r` | Refresh from disk |
| `?` | Show help overlay |
| `q` | Quit |

## Session details

Press `Enter` on a session row to open the details modal. Alongside project, branch, version, message counts, and on-disk size, you also get a **Usage / Context** section: model(s) used, total tokens, the input/output/cache-read/cache-write breakdown, cache hit ratio, service tier, and any web search / web fetch counts. These are aggregated from every assistant message in the session.

## Tips

- Hit `?` at any time for an in-app cheat sheet of these bindings.
- The `c` action falls back through several clipboard mechanisms (OSC 52, `pbcopy`, `xclip`), so it works over SSH and on bare Linux installs.
- The `o` action opens a new terminal tab and runs `claude --resume <id>` for you. On macOS it uses `osascript`; on Linux it tries `gnome-terminal`, `xterm`, then `konsole`.
