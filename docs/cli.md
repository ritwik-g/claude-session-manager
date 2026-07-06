# CLI Output

For when you just want a list — no UI, no interactivity.

## `clsm --list`

Tabular list of all sessions, sorted by most recent activity, identified by title (with a name chip for named sessions) rather than the raw first prompt. A `⟳` in the leftmost column marks sessions with a recap; `>` marks live sessions. Useful for piping into other tools.

```bash
clsm --list
```

## `clsm --stats`

Per-project aggregates: session count, message count, total on-disk size.

```bash
clsm --stats
```

Both commands are read-only and exit immediately — handy for a quick "what's piling up?" check.

## `clsm --path <dir>`

Scope any command to sessions whose working directory is under `<dir>`. Works with `--list`, `--stats`, `--web`, and the TUI.

```bash
clsm --list --path ~/work/my-repo
clsm --stats --path ~/personal
```

## `clsm --version`

Prints the installed version.

```bash
clsm --version
```
