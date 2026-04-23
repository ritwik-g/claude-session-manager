"""Claude Sessions Manager - TUI and Web UI for managing Claude Code sessions.

Usage:
    claude-session-manager          # Launch TUI (default)
    claude-session-manager --web    # Launch Web UI in browser
    claude-session-manager --web --port 9000  # Custom port
    claude-session-manager --list   # Quick list in terminal
    claude-session-manager --stats  # Show stats only
    clsm                           # Short alias for all above
"""

import argparse
import sys


def list_sessions():
    """Print a quick session list to stdout."""
    from rich.console import Console
    from rich.table import Table

    from .session_manager import discover_sessions, get_summary_stats

    console = Console()
    sessions = discover_sessions()
    stats = get_summary_stats(sessions)

    console.print(f"\n[bold blue]Claude Sessions Manager[/]")
    console.print(
        f"  {stats['total_sessions']} sessions | "
        f"{stats['total_projects']} projects | "
        f"{stats['total_size']} total | "
        f"{stats['active_sessions']} active\n"
    )

    table = Table(show_header=True, header_style="bold cyan", show_lines=False)
    table.add_column(" ", width=1, no_wrap=True)
    table.add_column("Date", style="dim", no_wrap=True)
    table.add_column("Project", style="blue", no_wrap=True, max_width=30)
    table.add_column("Branch", style="yellow", no_wrap=True, max_width=15)
    table.add_column("Topic", no_wrap=True, max_width=50, overflow="ellipsis")
    table.add_column("Msgs", justify="right", no_wrap=True)
    table.add_column("Size", justify="right", style="dim", no_wrap=True)

    for s in sessions:
        status = "[green]>[/]" if s.is_active else " "
        table.add_row(
            status,
            s.started_str,
            _short_project(s.project_path),
            s.git_branch or "-",
            s.topic,
            str(s.total_messages),
            s.size_str,
        )

    console.print(table)
    console.print()


def show_stats():
    """Print aggregate stats."""
    from collections import defaultdict

    from rich.console import Console
    from rich.panel import Panel

    from .session_manager import _format_size, discover_sessions, get_summary_stats

    console = Console()
    sessions = discover_sessions()
    stats = get_summary_stats(sessions)

    project_stats = defaultdict(lambda: {"count": 0, "size": 0})
    for s in sessions:
        project_stats[s.project_path]["count"] += 1
        project_stats[s.project_path]["size"] += s.total_size

    lines = [
        f"[bold]Total Sessions:[/]  {stats['total_sessions']}",
        f"[bold]Total Size:[/]      {stats['total_size']}",
        f"[bold]Total Messages:[/]  {stats['total_messages']}",
        f"[bold]Projects:[/]        {stats['total_projects']}",
        f"[bold]Active:[/]          {stats['active_sessions']}",
        "",
        "[bold underline]Per Project:[/]",
    ]

    sorted_projects = sorted(project_stats.items(), key=lambda x: x[1]["size"], reverse=True)
    for proj, ps in sorted_projects:
        lines.append(f"  {_short_project(proj)}: {ps['count']} sessions, {_format_size(ps['size'])}")

    console.print(Panel("\n".join(lines), title="[bold blue]Claude Sessions Stats[/]", border_style="blue"))


def _short_project(path: str) -> str:
    from pathlib import Path
    home = str(Path.home())
    if path.startswith(home):
        path = "~" + path[len(home):]
    parts = path.split("/")
    if len(parts) > 4:
        return "/".join(parts[:2]) + "/.../" + "/".join(parts[-2:])
    return path


def main():
    from claude_session_manager import __version__

    parser = argparse.ArgumentParser(
        description="Claude Sessions Manager - TUI and Web UI for managing Claude Code sessions",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--web", action="store_true", help="Launch web UI instead of TUI")
    parser.add_argument("--port", type=int, default=8420, help="Port for web UI (default: 8420)")
    parser.add_argument("--no-browser", action="store_true", help="Don't auto-open browser (web mode)")
    parser.add_argument("--list", action="store_true", help="Quick list sessions in terminal")
    parser.add_argument("--stats", action="store_true", help="Show aggregate stats")

    args = parser.parse_args()

    if args.list:
        list_sessions()
    elif args.stats:
        show_stats()
    elif args.web:
        from .web_ui import run_web
        run_web(port=args.port, open_browser=not args.no_browser)
    else:
        from .tui import run_tui
        run_tui()
