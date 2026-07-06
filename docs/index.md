# Claude Session Manager

A TUI and Web UI for viewing, searching, and managing your [Claude Code](https://docs.anthropic.com/en/docs/claude-code) sessions.

If you've used Claude Code for any length of time, you already know the problem: dozens of sessions pile up under `~/.claude/`, each with its own JSONL transcript, tool results, and file history. Finding the right one to resume — or cleaning up the ones you don't need — is painful.

`clsm` makes that easy.

![Main view](screenshots/01-main-view.png)

## Features

- **Session titles & recaps** — every session is identified by its name and AI summary, with a running recap (what was done, what's next) shown inline — no more squinting at a pasted URL
- **Folder-tree navigation** — projects shown as the real on-disk folder hierarchy (worktrees and sub-repos nest where they live), not a flat list
- **TUI** — interactive terminal UI with folder navigation, sorting, full-text filtering, and session details (built with [Textual](https://textual.textualize.io/))
- **Web UI** — browser-based interface with a collapsible folder tree, bulk selection, and deletion
- **Quick list & stats** — fast terminal table output and per-project aggregates
- **Usage breakdown** — per-session token totals (input / output / cache read / cache write), cache hit ratio, model(s), and web tool counts in the detail view
- **Scope** — restrict any view to one folder with `--path`
- **Session deletion** — clean up old sessions (JSONL, tool results, file history)
- **Search** — filter by title, summary, recap, message content, project, or branch
- **Resume** — copy resume commands or open sessions directly in a new terminal

## Where to start

- New here? Head to [Installation](installation.md), then [Quick Start](quickstart.md).
- Prefer the browser? See the [Web UI](web-ui.md) walkthrough.
- Live in the terminal? Jump to the [TUI](tui.md) reference.

## Links

- **Repo:** [github.com/ritwik-g/claude-session-manager](https://github.com/ritwik-g/claude-session-manager)
- **Releases:** [github.com/ritwik-g/claude-session-manager/releases](https://github.com/ritwik-g/claude-session-manager/releases)
- **Issues:** [github.com/ritwik-g/claude-session-manager/issues](https://github.com/ritwik-g/claude-session-manager/issues)
- **License:** MIT
