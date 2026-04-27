# CLI Output

For when you just want a list — no UI, no interactivity.

## `clsm --list`

Tabular list of all sessions, sorted by most recent activity. Useful for piping into other tools.

```bash
clsm --list
```

## `clsm --stats`

Per-project aggregates: session count, message count, total on-disk size.

```bash
clsm --stats
```

Both commands are read-only and exit immediately — handy for a quick "what's piling up?" check.

## `clsm --version`

Prints the installed version.

```bash
clsm --version
```
