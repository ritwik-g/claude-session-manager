"""Textual TUI for managing Claude Code sessions."""

from collections import defaultdict
from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import (
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from .session_manager import (
    SessionInfo,
    _format_size,
    delete_session,
    discover_sessions,
    get_summary_stats,
)

ALL_PROJECTS = "__all__"


def _short_project(path: str) -> str:
    """Shorten project path for display."""
    home = str(Path.home())
    if path.startswith(home):
        path = "~" + path[len(home):]
    parts = path.split("/")
    if len(parts) > 4:
        return "/".join(parts[:2]) + "/.../" + "/".join(parts[-2:])
    return path


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
        max-height: 48;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #detail-dialog Label {
        width: 100%;
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
            yield Label("")
            yield Label("[bold underline]Usage / Context[/]")
            yield Label(f"[bold]Model(s):[/]      {s.models_str}")
            yield Label(f"[bold]Total Tokens:[/]  {s.tokens_total_str}")
            if s.total_input_tokens:
                yield Label(f"[bold]  Input:[/]       {s.tokens_in_str}")
            if s.total_output_tokens:
                yield Label(f"[bold]  Output:[/]      {s.tokens_out_str}")
            if s.total_cache_read_tokens:
                yield Label(
                    f"[bold]  Cache Read:[/]  {s.tokens_cache_read_str}  "
                    f"({s.cache_hit_ratio_str} hit ratio)"
                )
            if s.total_cache_creation_tokens:
                yield Label(f"[bold]  Cache Write:[/] {s.tokens_cache_creation_str}")
            if s.service_tier:
                yield Label(f"[bold]Service Tier:[/]  {s.service_tier}")
            if s.web_search_count:
                yield Label(f"[bold]Web Search:[/]    {s.web_search_count}")
            if s.web_fetch_count:
                yield Label(f"[bold]Web Fetch:[/]     {s.web_fetch_count}")
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


class HelpScreen(ModalScreen):
    """Modal screen showing keybinding help."""

    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-dialog {
        width: 60;
        height: auto;
        max-height: 30;
        border: thick $accent;
        background: $surface;
        padding: 1 2;
    }
    #help-dialog Label {
        width: 100%;
    }
    .help-row {
        margin: 0;
    }
    """

    BINDINGS = [
        Binding("escape,q,question_mark", "close", "Close"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="help-dialog"):
            yield Label("[bold underline]Keybindings[/]")
            yield Label("")
            yield Label("[bold]Navigation[/]", classes="help-row")
            yield Label("  [bold cyan]Tab[/]        Switch between projects and sessions", classes="help-row")
            yield Label("  [bold cyan]Up/Down[/]    Navigate lists", classes="help-row")
            yield Label("  [bold cyan]Enter[/]      Select project (left) / View details (right)", classes="help-row")
            yield Label("  [bold cyan]Escape[/]     Clear filter / Close dialog", classes="help-row")
            yield Label("")
            yield Label("[bold]Actions[/]", classes="help-row")
            yield Label("  [bold cyan]c[/]          Copy resume command to clipboard", classes="help-row")
            yield Label("  [bold cyan]o[/]          Open session in a new terminal", classes="help-row")
            yield Label("  [bold cyan]d[/]          Delete selected session", classes="help-row")
            yield Label("  [bold cyan]r[/]          Refresh session list", classes="help-row")
            yield Label("  [bold cyan]s[/]          Cycle sort (date/messages/size)", classes="help-row")
            yield Label("")
            yield Label("[bold]Search[/]", classes="help-row")
            yield Label("  [bold cyan]/[/]          Focus filter input", classes="help-row")
            yield Label("  [bold cyan]Escape[/]     Clear filter and return to table", classes="help-row")
            yield Label("")
            yield Label("[bold]Other[/]", classes="help-row")
            yield Label("  [bold cyan]?[/]          Show this help", classes="help-row")
            yield Label("  [bold cyan]q[/]          Quit", classes="help-row")
            yield Label("")
            yield Label("[dim]Press Esc/q/? to close[/]")

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
    #main-content {
        height: 1fr;
    }
    #project-panel {
        width: 30;
        border-right: solid $accent;
    }
    #project-panel-title {
        height: 1;
        background: $panel;
        padding: 0 1;
        text-style: bold;
        color: $accent;
    }
    #project-list {
        height: 1fr;
    }
    #project-list > ListItem {
        padding: 0 1;
    }
    #session-panel {
        width: 1fr;
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
        Binding("question_mark", "show_help", "Help", show=True),
        Binding("tab", "switch_panel", "Tab=Panel", show=True),
        Binding("c", "copy_resume", "Copy"),
        Binding("o", "open_session", "Open"),
        Binding("d", "delete_session", "Delete"),
        Binding("s", "cycle_sort", "Sort"),
        Binding("slash", "focus_filter", "Filter"),
        Binding("r", "refresh", "Refresh"),
        Binding("escape", "clear_filter", "Clear"),
        Binding("q", "quit", "Quit"),
    ]

    SORT_COLUMNS = ["date", "messages", "size"]

    def __init__(self) -> None:
        super().__init__()
        self.sessions: list[SessionInfo] = []
        self.filtered_sessions: list[SessionInfo] = []
        self.filter_text: str = ""
        self.sort_key: str = "date"
        self.sort_reverse: bool = True
        self.selected_project: str = ALL_PROJECTS
        self.project_keys: list[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="stats-bar")
        with Container(id="filter-bar"):
            yield Input(placeholder="Type to filter sessions...", id="filter-input")
        with Horizontal(id="main-content"):
            with Container(id="project-panel"):
                yield Static(" Projects", id="project-panel-title")
                yield ListView(id="project-list")
            with Container(id="session-panel"):
                yield DataTable(id="sessions-table", cursor_type="row")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._load_sessions()
        self.query_one("#project-list", ListView).focus()

    def _load_sessions(self) -> None:
        self.sessions = discover_sessions()
        self._rebuild_project_list()
        self._apply_filter()
        self._update_stats()

    def _rebuild_project_list(self) -> None:
        """Build the project list from current sessions."""
        project_data: dict[str, dict] = defaultdict(lambda: {"count": 0, "size": 0, "active": 0})
        for s in self.sessions:
            project_data[s.project_path]["count"] += 1
            project_data[s.project_path]["size"] += s.total_size
            if s.is_active:
                project_data[s.project_path]["active"] += 1

        sorted_projects = sorted(project_data.items(), key=lambda x: x[1]["size"], reverse=True)

        lv = self.query_one("#project-list", ListView)
        lv.clear()

        total = len(self.sessions)
        total_size = _format_size(sum(s.total_size for s in self.sessions))
        lv.append(ListItem(Label(f"[bold]All Projects[/] ({total}, {total_size})"), name=ALL_PROJECTS))
        self.project_keys = [ALL_PROJECTS]

        for proj_path, info in sorted_projects:
            short = _short_project(proj_path)
            active_marker = " [green]*[/]" if info["active"] > 0 else ""
            lv.append(ListItem(
                Label(f"{short} ({info['count']}, {_format_size(info['size'])}){active_marker}"),
                name=proj_path,
            ))
            self.project_keys.append(proj_path)

    def _apply_filter(self) -> None:
        # Filter by selected project
        if self.selected_project == ALL_PROJECTS:
            sessions = list(self.sessions)
        else:
            sessions = [s for s in self.sessions if s.project_path == self.selected_project]

        # Filter by search text
        if self.filter_text:
            ft = self.filter_text.lower()
            sessions = [
                s for s in sessions
                if ft in s.first_message.lower()
                or ft in s.last_user_message.lower()
                or ft in s.last_assistant_message.lower()
                or ft in s.git_branch.lower()
                or ft in s.session_id.lower()
                or ft in s.cwd.lower()
                or ft in s.project_path.lower()
            ]

        self.filtered_sessions = sessions
        self._sort_sessions()
        self._populate_table()

    def _sort_sessions(self) -> None:
        from datetime import datetime, timezone

        if self.sort_key == "date":
            self.filtered_sessions.sort(
                key=lambda s: s.started_at or datetime.min.replace(tzinfo=timezone.utc),
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

        show_project = self.selected_project == ALL_PROJECTS
        cols = [" ", f"Date{sort_indicators['date']}", "Branch", "Topic", "Last Response",
                f"Msgs{sort_indicators['messages']}", f"Size{sort_indicators['size']}"]
        if show_project:
            cols.insert(2, "Project")
        table.add_columns(*cols)

        for s in self.filtered_sessions:
            status = "[green]>[/]" if s.is_active else " "
            last_resp = s.last_assistant_message[:60] + "..." if len(s.last_assistant_message) > 60 else s.last_assistant_message
            row = [
                status,
                s.started_str,
                s.git_branch or "-",
                s.topic,
                last_resp or "-",
                str(s.total_messages),
                s.size_str,
            ]
            if show_project:
                row.insert(2, _short_project(s.project_path))
            table.add_row(*row, key=s.session_id)

    def _update_stats(self) -> None:
        stats = get_summary_stats(self.sessions)
        proj_label = _short_project(self.selected_project) if self.selected_project != ALL_PROJECTS else "All"
        stats_bar = self.query_one("#stats-bar", Static)
        stats_bar.update(
            f" {stats['total_sessions']} sessions | "
            f"{stats['total_projects']} projects | "
            f"{stats['total_size']} total | "
            f"{stats['active_sessions']} active | "
            f"Viewing: {proj_label} ({len(self.filtered_sessions)})"
        )

    def _set_status(self, message: str) -> None:
        status_bar = self.query_one("#status-bar", Static)
        status_bar.update(f" {message}")

    def _get_selected_session(self) -> SessionInfo | None:
        table = self.query_one("#sessions-table", DataTable)
        if table.cursor_row is None or not self.filtered_sessions:
            return None
        if table.cursor_row < len(self.filtered_sessions):
            return self.filtered_sessions[table.cursor_row]
        return None

    @on(ListView.Selected, "#project-list")
    def on_project_selected(self, event: ListView.Selected) -> None:
        name = event.item.name or ALL_PROJECTS
        self.selected_project = name
        self._apply_filter()
        self._update_stats()
        self.query_one("#sessions-table", DataTable).focus()

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self.filter_text = event.value
        self._apply_filter()
        self._update_stats()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_switch_panel(self) -> None:
        lv = self.query_one("#project-list", ListView)
        table = self.query_one("#sessions-table", DataTable)
        if lv.has_focus:
            table.focus()
        else:
            lv.focus()

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
        self.sort_reverse = True
        self._apply_filter()
        self._set_status(f"Sorted by {self.sort_key}")

    @on(DataTable.RowSelected, "#sessions-table")
    def on_session_row_selected(self, event: DataTable.RowSelected) -> None:
        """Enter on session table shows details."""
        session = self._get_selected_session()
        if session:
            self.push_screen(SessionDetailScreen(session))

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard with pbcopy fallback for macOS."""
        import platform
        import subprocess

        self.copy_to_clipboard(text)
        # Also try pbcopy/xclip as fallback
        try:
            if platform.system() == "Darwin":
                subprocess.run(["pbcopy"], input=text.encode(), check=True)
            elif platform.system() == "Linux":
                subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode(), check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

    def action_copy_resume(self) -> None:
        session = self._get_selected_session()
        if not session:
            self._set_status("No session selected")
            return
        cmd = f"claude --resume {session.session_id}"
        self._copy_to_clipboard(cmd)
        self._set_status(f"Copied: {cmd}")

    def action_open_session(self) -> None:
        """Open the selected session in a new terminal."""
        import platform
        import subprocess

        session = self._get_selected_session()
        if not session:
            self._set_status("No session selected")
            return
        cmd = f"claude --resume {session.session_id}"
        cwd = session.cwd or str(Path.home())
        try:
            if platform.system() == "Darwin":
                # Open a new Terminal.app tab and run the command
                apple_script = (
                    'tell application "Terminal"\n'
                    "  activate\n"
                    f'  do script "cd {cwd} && {cmd}"\n'
                    "end tell"
                )
                subprocess.Popen(["osascript", "-e", apple_script])
            else:
                # Linux: try common terminal emulators
                for term in ["gnome-terminal", "xterm", "konsole"]:
                    try:
                        subprocess.Popen([term, "--", "bash", "-c", f"cd {cwd} && {cmd}; exec bash"])
                        break
                    except FileNotFoundError:
                        continue
            self._set_status(f"Opened session in new terminal")
        except Exception as e:
            self._set_status(f"Error opening terminal: {e}")

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
