# Quick Start

Once installed, four entry points cover everything:

```bash
clsm              # interactive TUI (default)
clsm --web        # browser-based UI
clsm --list       # one-shot terminal table
clsm --stats      # aggregate stats per project
```

By default the web UI binds to `http://localhost:8420`. Use `--port` to change it, and `--no-browser` if you don't want it auto-opened.

## Common flags

| Flag | Description |
|------|-------------|
| `--web` | Launch the browser UI instead of the TUI |
| `--port <n>` | Bind the web UI to a specific port |
| `--no-browser` | Don't auto-open the browser |
| `--list` | Print a tabular list of sessions and exit |
| `--stats` | Print per-project totals and exit |
| `--version` | Show version |

## What gets read

`clsm` reads from `~/.claude/projects/`. Each session is one JSONL transcript plus an associated tool-result and file-history directory. Nothing is written to disk unless you explicitly delete a session.

## What gets deleted

When you delete a session, `clsm` removes:

- the JSONL transcript at `~/.claude/projects/<project>/<session-id>.jsonl`
- the matching tool-result directory
- the matching file-history directory

Active sessions are never deletable from the UI — the delete button is disabled and bulk-select skips them.
