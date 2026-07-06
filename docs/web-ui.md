# Web UI

Launch with:

```bash
clsm --web
```

## Main view

The default view shows every session you've ever run, with your projects as a folder tree on the left.

![Main view](screenshots/01-main-view.png)

What you're looking at:

- **Header** — totals across all sessions (count, projects, currently active, on-disk size).
- **Folder tree** — your projects as they actually live on disk. Sessions are grouped into top-level areas (the first folder under your home), and each real working directory appears as a leaf beneath it. Worktrees are marked `⑂`, and a green dot means at least one session there is live.
- **Sessions table** — each row leads with the session's **title** (a user-given name shown as a chip, plus the AI-generated summary), a **recap** line underneath (what was done and what's next), when it was last active, its project and branch, message count, and per-row actions.
- **`● live` badge / `⟳ recap` chip** — `live` marks sessions still being written to (their delete is disabled); `⟳ recap` marks sessions that carry a running recap.

Instead of the raw first prompt, every session is identified by its name and summary, so you can recognize sessions at a glance instead of squinting at a pasted URL.

## Folder navigation

The tree keys on the real working directory (from each session's `cwd`), so sibling repos and worktrees appear where they actually are on disk — not scattered.

![Project-filtered view](screenshots/02-project-filter.png)

- Click an **area** (bold group) to scope the table to everything beneath it.
- Click a **leaf** to scope to that exact working directory. The project column drops out since it's redundant.
- Use **Jump to folder…** to filter the tree by name.
- Click **All projects** at the top to clear the scope.

## Searching

The search box filters by title, summary, **recap**, message content, project, and branch — and shows a live `N of M` result count, so an empty match is obvious.

![Search filter](screenshots/04-search-filter.png)

Use the **Sort** dropdown (or click a column header) to order by most-recent, title, project, message count, or disk size. Recent is the default.

## Session details

Click any row to open the details panel.

![Session details](screenshots/03-session-details.png)

The panel is headed by the session's title and leads with its **recap** — the running summary of what was done and what's next. Below that:

- **Name / summary**, session ID, working directory, Claude version.
- **Started, last active, and active span** (first → last message — this is wall-clock across resumes, not time actively spent).
- **Message counts** and on-disk size.
- **Usage / context** — model(s), total tokens (input, output, cache read with hit ratio, cache write), service tier, and any web search / fetch counts.
- **Continued-conversation summary** — the longer compaction summary, when a session ran out of context and was continued.
- **First / last user message, last response**.

Use **Copy resume command** to put `cd <dir> && claude --resume <id>` on your clipboard.

## Per-row actions

| Button | Action |
|--------|--------|
| **Resume** | Copies the `cd … && claude --resume <session-id>` command to your clipboard. |
| **Del** | Deletes the session — JSONL transcript, tool results, file history. Disabled for active sessions. |

## Bulk delete

Use the checkboxes in the leftmost column to select multiple sessions, then trigger the bulk-delete action. Active sessions are excluded automatically — their checkboxes are disabled.

## Scoping to one folder

Restrict the whole UI to a subtree with `--path`:

```bash
clsm --web --path ~/work/my-repo
```

Only sessions whose working directory is under that path are shown. It's a read-only filter.
