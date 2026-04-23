"""Textual TUI for managing Claude Code sessions."""

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    Static,
)

from .session_manager import (
    SessionInfo,
    delete_session,
    discover_sessions,
    get_summary_stats,
)


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Modal confirmation dialog for deleting a session."""

    CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    #confirm-dialog {
        width: 70;
        height: auto;
        max-height: 20;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #confirm-dialog Label {
        width: 100%;
        margin-bottom: 1;
    }
    #confirm-dialog .detail {
        color: $text-muted;
    }
    #confirm-buttons {
        width: 100%;
        height: 3;
        align: center middle;
    }
    #confirm-buttons Static {
        width: auto;
        margin: 0 2;
    }
    .btn-danger {
        color: $error;
    }
    .btn-cancel {
        color: $text-muted;
    }
    """

    BINDINGS = [
        Binding("y", "confirm", "Yes, delete"),
        Binding("n,escape", "cancel", "Cancel"),
    ]

    def __init__(self, session: SessionInfo) -> None:
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        s = self.session
        with Container(id="confirm-dialog"):
            yield Label("[bold red]Delete this session?[/]")
            yield Label(f"[bold]Project:[/] {s.project_path}")
            yield Label(f"[bold]Topic:[/] {s.topic}")
            yield Label(f"[bold]Date:[/] {s.started_str}")
            yield Label(f"[bold]Size:[/] {s.size_str}")
            yield Label(f"[bold]Messages:[/] {s.total_messages}")
            yield Label("")
            with Horizontal(id="confirm-buttons"):
                yield Static("[bold red](y)[/] Yes, delete", classes="btn-danger")
                yield Static("[dim](n/Esc)[/] Cancel", classes="btn-cancel")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class SessionDetailScreen(ModalScreen):
    """Modal screen showing session details."""

    CSS = """
    SessionDetailScreen {
        align: center middle;
    }
    #detail-dialog {
        width: 100;
        height: auto;
        max-height: 40;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #detail-dialog Label {
        width: 100%;
    }
    .detail-header {
        text-style: bold;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape,q,enter", "close", "Close"),
    ]

    def __init__(self, session: SessionInfo) -> None:
        super().__init__()
        self.session = session

    def compose(self) -> ComposeResult:
        s = self.session
        active_str = f"[bold green]ACTIVE[/] (PID {s.active_pid})" if s.is_active else "[dim]Inactive[/]"
        with VerticalScroll(id="detail-dialog"):
            yield Label("[bold underline]Session Details[/]")
            yield Label("")
            yield Label(f"[bold]Session ID:[/]  {s.session_id}")
            yield Label(f"[bold]Status:[/]      {active_str}")
            yield Label(f"[bold]Project:[/]     {s.project_path}")
            yield Label(f"[bold]Working Dir:[/] {s.cwd}")
            yield Label(f"[bold]Git Branch:[/]  {s.git_branch or 'N/A'}")
            yield Label(f"[bold]Version:[/]     {s.version or 'N/A'}")
            yield Label("")
            yield Label(f"[bold]Started:[/]     {s.started_str}")
            yield Label(f"[bold]Duration:[/]    {s.duration_str}")
            yield Label(f"[bold]Messages:[/]    {s.user_message_count} user / {s.assistant_message_count} assistant / {s.total_messages} total")
            yield Label(f"[bold]JSONL Size:[/]  {s.file_size_str}")
            yield Label(f"[bold]Total Size:[/]  {s.size_str}")
            if s.slug:
                yield Label(f"[bold]Slug:[/]        {s.slug}")
            if s.pr_links:
                yield Label("")
                yield Label("[bold]PRs Created:[/]")
                for pr in s.pr_links:
                    yield Label(f"  {pr}")
            yield Label("")
            yield Label("[bold]First Message:[/]")
            yield Label(s.first_message or "(empty)")
            if s.last_user_message and s.last_user_message != s.first_message:
                yield Label("")
                yield Label("[bold]Last User Message:[/]")
                yield Label(s.last_user_message)
            if s.last_assistant_message:
                yield Label("")
                yield Label("[bold]Last Assistant Response:[/]")
                yield Label(s.last_assistant_message)
            yield Label("")
            yield Label("[dim]Press Esc/Enter/q to close[/]")

    def action_close(self) -> None:
        self.dismiss()


class SessionManagerApp(App):
    """TUI for managing Claude Code sessions."""

    TITLE = "Claude Sessions Manager"
    CSS = """
    Screen {
        layout: vertical;
    }
    #stats-bar {
        height: 1;
        dock: top;
        background: $accent;
        color: $text;
        padding: 0 2;
    }
    #filter-bar {
        height: 3;
        dock: top;
        padding: 0 1;
    }
    #filter-bar Input {
        width: 100%;
    }
    #sessions-table {
        height: 1fr;
    }
    #status-bar {
        height: 1;
        dock: bottom;
        background: $panel;
        color: $text-muted;
        padding: 0 2;
    }
    DataTable {
        height: 1fr;
    }
    DataTable > .datatable--cursor {
        background: $accent 30%;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("d", "delete_session", "Delete"),
        Binding("enter", "view_details", "Details"),
        Binding("r", "refresh", "Refresh"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("escape", "clear_filter", "Clear filter"),
        Binding("s", "cycle_sort", "Sort"),
    ]

    SORT_COLUMNS = ["date", "project", "messages", "size"]

    def __init__(self) -> None:
        super().__init__()
        self.sessions: list[SessionInfo] = []
        self.filtered_sessions: list[SessionInfo] = []
        self.filter_text: str = ""
        self.sort_key: str = "date"
        self.sort_reverse: bool = True
        self.status_message: str = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="stats-bar")
        with Container(id="filter-bar"):
            yield Input(placeholder="Type to filter sessions (project, topic, branch)...", id="filter-input")
        yield DataTable(id="sessions-table")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._load_sessions()

    def _load_sessions(self) -> None:
        self.sessions = discover_sessions()
        self._apply_filter()
        self._update_stats()

    def _apply_filter(self) -> None:
        if self.filter_text:
            ft = self.filter_text.lower()
            self.filtered_sessions = [
                s for s in self.sessions
                if ft in s.project_path.lower()
                or ft in s.first_message.lower()
                or ft in s.last_user_message.lower()
                or ft in s.last_assistant_message.lower()
                or ft in s.git_branch.lower()
                or ft in s.session_id.lower()
                or ft in s.cwd.lower()
            ]
        else:
            self.filtered_sessions = list(self.sessions)

        self._sort_sessions()
        self._populate_table()

    def _sort_sessions(self) -> None:
        from datetime import datetime, timezone

        if self.sort_key == "date":
            self.filtered_sessions.sort(
                key=lambda s: s.started_at or datetime.min.replace(tzinfo=timezone.utc),
                reverse=self.sort_reverse,
            )
        elif self.sort_key == "project":
            self.filtered_sessions.sort(
                key=lambda s: s.project_path.lower(),
                reverse=self.sort_reverse,
            )
        elif self.sort_key == "messages":
            self.filtered_sessions.sort(
                key=lambda s: s.total_messages,
                reverse=self.sort_reverse,
            )
        elif self.sort_key == "size":
            self.filtered_sessions.sort(
                key=lambda s: s.total_size,
                reverse=self.sort_reverse,
            )

    def _populate_table(self) -> None:
        table = self.query_one("#sessions-table", DataTable)
        table.clear(columns=True)

        sort_indicators = {k: "" for k in self.SORT_COLUMNS}
        arrow = " v" if self.sort_reverse else " ^"
        sort_indicators[self.sort_key] = arrow

        table.add_columns(
            " ",
            f"Date{sort_indicators['date']}",
            f"Project{sort_indicators['project']}",
            "Branch",
            "Topic",
            "Last Response",
            f"Msgs{sort_indicators['messages']}",
            f"Size{sort_indicators['size']}",
        )

        for s in self.filtered_sessions:
            status = "[green]>[/]" if s.is_active else " "
            last_resp = s.last_assistant_message[:60] + "..." if len(s.last_assistant_message) > 60 else s.last_assistant_message
            table.add_row(
                status,
                s.started_str,
                self._short_project(s.project_path),
                s.git_branch or "-",
                s.topic,
                last_resp or "-",
                str(s.total_messages),
                s.size_str,
                key=s.session_id,
            )

    def _short_project(self, path: str) -> str:
        """Shorten project path for display."""
        home = str(Path.home())
        if path.startswith(home):
            path = "~" + path[len(home):]
        parts = path.split("/")
        if len(parts) > 4:
            return "/".join(parts[:2]) + "/.../" + "/".join(parts[-2:])
        return path

    def _update_stats(self) -> None:
        stats = get_summary_stats(self.sessions)
        stats_bar = self.query_one("#stats-bar", Static)
        stats_bar.update(
            f" {stats['total_sessions']} sessions | "
            f"{stats['total_projects']} projects | "
            f"{stats['total_size']} total | "
            f"{stats['active_sessions']} active | "
            f"Showing {len(self.filtered_sessions)}"
        )

    def _set_status(self, message: str) -> None:
        status_bar = self.query_one("#status-bar", Static)
        status_bar.update(f" {message}")

    def _get_selected_session(self) -> SessionInfo | None:
        table = self.query_one("#sessions-table", DataTable)
        if table.cursor_row is None or not self.filtered_sessions:
            return None
        try:
            row_key = table.get_row_at(table.cursor_row)
        except Exception:
            return None
        # Find session by matching cursor position
        if table.cursor_row < len(self.filtered_sessions):
            return self.filtered_sessions[table.cursor_row]
        return None

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self.filter_text = event.value
        self._apply_filter()
        self._update_stats()

    def action_focus_filter(self) -> None:
        self.query_one("#filter-input", Input).focus()

    def action_clear_filter(self) -> None:
        inp = self.query_one("#filter-input", Input)
        inp.value = ""
        self.filter_text = ""
        self._apply_filter()
        self._update_stats()
        self.query_one("#sessions-table", DataTable).focus()

    def action_refresh(self) -> None:
        self._set_status("Refreshing...")
        self._load_sessions()
        self._set_status(f"Refreshed. Found {len(self.sessions)} sessions.")

    def action_cycle_sort(self) -> None:
        idx = self.SORT_COLUMNS.index(self.sort_key)
        next_idx = (idx + 1) % len(self.SORT_COLUMNS)
        self.sort_key = self.SORT_COLUMNS[next_idx]
        self.sort_reverse = self.sort_key in ("date", "messages", "size")
        self._apply_filter()
        self._set_status(f"Sorted by {self.sort_key}")

    def action_view_details(self) -> None:
        session = self._get_selected_session()
        if session:
            self.push_screen(SessionDetailScreen(session))

    def action_delete_session(self) -> None:
        session = self._get_selected_session()
        if not session:
            self._set_status("No session selected")
            return
        if session.is_active:
            self._set_status(f"Cannot delete active session (PID {session.active_pid})")
            return
        self.push_screen(ConfirmDeleteScreen(session), callback=self._on_delete_confirm)

    def _on_delete_confirm(self, confirmed: bool) -> None:
        if not confirmed:
            self._set_status("Delete cancelled")
            return
        session = self._get_selected_session()
        if not session:
            return
        try:
            results = delete_session(session)
            deleted = [k for k, v in results.items() if v]
            self._set_status(f"Deleted session: {', '.join(deleted)}")
            self._load_sessions()
        except ValueError as e:
            self._set_status(f"Error: {e}")
        except Exception as e:
            self._set_status(f"Error deleting: {e}")


def run_tui():
    app = SessionManagerApp()
    app.run()
