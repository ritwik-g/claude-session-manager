# TUI

If you prefer the terminal, just run:

```bash
clsm
```

You get the same data in a Textual-powered TUI: a project **folder tree** on the left, sessions on the right, full keyboard navigation. Each session row leads with its title (with a name chip for named sessions), and the status column flags live (`●`) and recap (`⟳`) sessions.

## Keybindings

| Key | Action |
|-----|--------|
| `Tab` | Switch focus between the folder tree and the session table |
| `Up` / `Down` | Move within the tree or table |
| `Left` / `Right` | Collapse / expand folders in the tree |
| `Enter` | Open session details |
| `c` | Copy `claude --resume` command for the selected session |
| `o` | Open the session in a new terminal tab |
| `d` | Delete the selected session |
| `/` | Filter / search (title, summary, recap, message content) |
| `s` | Cycle sort order (recent / messages / size / title) |
| `r` | Refresh from disk |
| `?` | Show help overlay (includes a legend) |
| `q` | Quit |

The top bar always shows the current view and sort order, so you're never guessing how the list is ordered.

### Legend

| Marker | Meaning |
|--------|---------|
| `●` | Session is live |
| `⟳` | Session has a running recap |
| name | A user-given custom name (shown before the summary) |
| `⑂` | Git worktree |

## Folder navigation

The tree groups your projects into top-level areas with each real working directory as a leaf beneath — keyed on the session's `cwd`, so worktrees and sibling repos land where they actually live. Highlighting an area scopes the table to everything under it; highlighting a leaf scopes to that exact folder.

## Session details

Press `Enter` on a session row to open the details modal. It leads with the session's **recap** (what was done and what's next), then project, branch, version, message counts, on-disk size, and a **Usage / Context** section (model(s), total tokens, the input/output/cache-read/cache-write breakdown, cache hit ratio, service tier, and any web search / fetch counts). If the session was continued after running out of context, a **Continued-conversation summary** section shows the longer compaction summary.

## Scoping to one folder

```bash
clsm --path ~/work/my-repo
```

Restricts the TUI to sessions whose working directory is under that path.

## Tips

- Hit `?` at any time for an in-app cheat sheet and the legend.
- The `c` action falls back through several clipboard mechanisms (OSC 52, `pbcopy`, `xclip`), so it works over SSH and on bare Linux installs.
- The `o` action opens a new terminal tab and runs `claude --resume <id>` for you. On macOS it uses `osascript`; on Linux it tries `gnome-terminal`, `xterm`, then `konsole`.
