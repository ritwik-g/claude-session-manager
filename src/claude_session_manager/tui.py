"""Textual TUI for managing Claude Code sessions."""

from datetime import datetime, timezone

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
    Static,
    Tree,
)

from .session_manager import (
    SessionInfo,
    build_project_tree,
    discover_sessions,
    delete_session,
    get_summary_stats,
)

ALL_PROJECTS = "__all__"


def _clip(text: str, width: int) -> str:
    text = " ".join((text or "").split())
    if len(text) > width:
        return text[: width - 1] + "…"
    return text


class ConfirmDeleteScreen(ModalScreen[bool]):
    """Modal confirmation dialog for deleting a session."""

    CSS = """
    ConfirmDeleteScreen {
        align: center middle;
    }
    #confirm-dialog {
        width: 74;
        height: auto;
        max-height: 20;
        border: thick $error;
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
            yield Label(f"[bold]Session:[/] {s.display_title}")
            yield Label(f"[bold]Project:[/] {s.real_path_short}")
            yield Label(f"[bold]When:[/]    {s.when_str} ({s.started_str})")
            yield Label(f"[bold]Size:[/]    {s.size_str}")
            yield Label("")
            yield Label("[dim]Deletes transcript, tool results, and file history. Cannot be undone.[/]")
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
    #detail-title {
        text-style: bold;
        color: $accent;
    }
    #detail-meta {
        color: $text-muted;
        margin-bottom: 1;
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
        active_str = f"[bold green]● live[/] (PID {s.active_pid})" if s.is_active else "[dim]inactive[/]"
        with VerticalScroll(id="detail-dialog"):
            yield Label(s.display_title, id="detail-title")
            meta = f"{s.project_leaf} · {s.git_branch or 'no branch'} · {s.when_str} · {s.started_str}"
            if s.agent_name:
                meta += f" · agent: {s.agent_name}"
            yield Label(meta, id="detail-meta")
            yield Label(f"[bold]Status:[/]      {active_str}")
            if s.custom_title and s.custom_title != s.display_title:
                yield Label(f"[bold]Name:[/]        {s.custom_title}")
            if s.ai_title and s.ai_title != s.display_title:
                yield Label(f"[bold]Summary:[/]     {s.ai_title}")
            yield Label(f"[bold]Session ID:[/]  {s.session_id}")
            yield Label(f"[bold]Working Dir:[/] {s.cwd or s.real_path}")
            yield Label(f"[bold]Version:[/]     {s.version or 'N/A'}")
            yield Label("")
            yield Label(f"[bold]Started:[/]     {s.started_str}")
            yield Label(f"[bold]Last active:[/] {s.last_activity_str}  [dim]({s.when_str})[/]")
            yield Label(f"[bold]Active span:[/] {s.duration_str}  [dim]first → last message[/]")
            yield Label(f"[bold]Messages:[/]    {s.user_message_count} user / {s.assistant_message_count} assistant")
            yield Label(f"[bold]Disk size:[/]   {s.size_str}")
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
            yield Label("[dim]Press Esc/Enter/q to close · c copy resume · o open[/]")

    def action_close(self) -> None:
        self.dismiss()


class HelpScreen(ModalScreen):
    """Modal screen showing keybinding help."""

    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-dialog {
        width: 62;
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
            yield Label("  [bold cyan]Tab[/]        Switch between folder tree and sessions", classes="help-row")
            yield Label("  [bold cyan]Up/Down[/]    Move · [bold cyan]Left/Right[/] collapse/expand folders", classes="help-row")
            yield Label("  [bold cyan]Enter[/]      View session details", classes="help-row")
            yield Label("")
            yield Label("[bold]Actions[/]", classes="help-row")
            yield Label("  [bold cyan]c[/]          Copy resume command to clipboard", classes="help-row")
            yield Label("  [bold cyan]o[/]          Open session in a new terminal", classes="help-row")
            yield Label("  [bold cyan]d[/]          Delete selected session", classes="help-row")
            yield Label("  [bold cyan]r[/]          Refresh session list", classes="help-row")
            yield Label("  [bold cyan]s[/]          Cycle sort (recent/messages/size/title)", classes="help-row")
            yield Label("")
            yield Label("[bold]Search[/]", classes="help-row")
            yield Label("  [bold cyan]/[/]          Focus filter (title, summary, messages)", classes="help-row")
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
        background: $accent;
        color: $text;
        padding: 0 2;
    }
    #filter-bar {
        height: 3;
        padding: 0 1;
    }
    #filter-bar Input {
        width: 100%;
    }
    #main-content {
        height: 1fr;
    }
    #project-panel {
        width: 38;
        border-right: solid $accent;
    }
    #project-panel-title {
        height: 1;
        background: $panel;
        padding: 0 1;
        text-style: bold;
        color: $accent;
    }
    #project-tree {
        height: 1fr;
    }
    #session-panel {
        width: 1fr;
    }
    #sessions-table {
        height: 1fr;
    }
    #status-bar {
        height: 1;
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

    # (sort key, human label)
    SORT_MODES = [
        ("recent", "recent"),
        ("messages", "messages"),
        ("size", "size"),
        ("title", "title"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.sessions: list[SessionInfo] = []
        self.filtered_sessions: list[SessionInfo] = []
        self.filter_text: str = ""
        self.sort_key: str = "recent"
        self.sort_reverse: bool = True
        self.selected_path: str = ALL_PROJECTS
        self.selected_group: bool = True  # True = area (prefix); False = leaf working dir (exact)
        self.selected_label: str = "All projects"

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("", id="stats-bar")
        with Container(id="filter-bar"):
            yield Input(placeholder="Search title, summary, message text, project...", id="filter-input")
        with Horizontal(id="main-content"):
            with Container(id="project-panel"):
                yield Static(" Projects", id="project-panel-title")
                tree: Tree = Tree("All projects", id="project-tree")
                tree.show_root = True
                tree.guide_depth = 2
                yield tree
            with Container(id="session-panel"):
                yield DataTable(id="sessions-table", cursor_type="row")
        yield Static("", id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        self._load_sessions()
        self.query_one("#project-tree", Tree).focus()

    def _load_sessions(self) -> None:
        self.sessions = discover_sessions()
        self._rebuild_tree()
        self._apply_filter()
        self._update_stats()

    def _rebuild_tree(self) -> None:
        """Build the two-level project tree: area groups -> working-dir leaves."""
        tree = self.query_one("#project-tree", Tree)
        tree.clear()
        total = len(self.sessions)
        root = tree.root
        root.set_label(f"[bold]All projects[/]  [dim]{total}[/]")
        root.data = {"path": ALL_PROJECTS, "group": True}

        for area in build_project_tree(self.sessions):
            adot = " [green]●[/]" if area["active"] else ""
            area_node = root.add(
                f"[bold]{area['name']}[/]{adot}  [dim]{area['count']}[/]",
                data={"path": area["path"], "group": True},
            )
            for leaf in area["children"]:
                ldot = " [green]●[/]" if leaf["active"] else ""
                root_tag = " [dim]root[/]" if leaf["is_root"] else ""
                worktree = " [yellow]⑂[/]" if leaf["worktree"] else ""
                hint = f" [dim]{leaf['hint']}[/]" if leaf["hint"] else ""
                area_node.add_leaf(
                    f"{leaf['name']}{worktree}{root_tag}{hint}{ldot}  [dim]{leaf['count']}[/]",
                    data={"path": leaf["path"], "group": False},
                )
            area_node.expand()

        root.expand()

    def _apply_filter(self) -> None:
        # Filter by selected area (prefix) or exact working dir (leaf)
        if self.selected_path == ALL_PROJECTS:
            sessions = list(self.sessions)
        elif self.selected_group:
            sessions = [
                s for s in self.sessions
                if s.real_path == self.selected_path
                or s.real_path.startswith(self.selected_path + "/")
            ]
        else:
            sessions = [s for s in self.sessions if s.real_path == self.selected_path]

        # Filter by search text across meaningful fields
        if self.filter_text:
            ft = self.filter_text.lower()
            sessions = [
                s for s in sessions
                if ft in s.display_title.lower()
                or ft in (s.subtitle or "").lower()
                or ft in (s.ai_title or "").lower()
                or ft in (s.custom_title or "").lower()
                or ft in s.first_message.lower()
                or ft in s.last_user_message.lower()
                or ft in s.last_assistant_message.lower()
                or ft in s.git_branch.lower()
                or ft in s.session_id.lower()
                or ft in s.real_path.lower()
            ]

        self.filtered_sessions = sessions
        self._sort_sessions()
        self._populate_table()

    def _sort_sessions(self) -> None:
        min_dt = datetime.min.replace(tzinfo=timezone.utc)
        if self.sort_key == "recent":
            self.filtered_sessions.sort(
                key=lambda s: s.last_activity or s.started_at or min_dt,
                reverse=self.sort_reverse,
            )
        elif self.sort_key == "messages":
            self.filtered_sessions.sort(key=lambda s: s.total_messages, reverse=self.sort_reverse)
        elif self.sort_key == "size":
            self.filtered_sessions.sort(key=lambda s: s.total_size, reverse=self.sort_reverse)
        elif self.sort_key == "title":
            self.filtered_sessions.sort(key=lambda s: s.display_title.lower(), reverse=self.sort_reverse)

    def _populate_table(self) -> None:
        table = self.query_one("#sessions-table", DataTable)
        table.clear(columns=True)

        arrow = "▾" if self.sort_reverse else "▴"
        when_h = f"When {arrow}" if self.sort_key == "recent" else "When"
        session_h = f"Session {arrow}" if self.sort_key == "title" else "Session"
        msgs_h = f"Msgs {arrow}" if self.sort_key == "messages" else "Msgs"

        show_project = self.selected_path == ALL_PROJECTS or len(
            {s.real_path for s in self.filtered_sessions}
        ) > 1

        table.add_column(" ", width=1)
        table.add_column(when_h, width=9)
        table.add_column(session_h, width=64)
        if show_project:
            table.add_column("Project", width=22)
        table.add_column("Br", width=8)
        table.add_column(msgs_h, width=6)

        prev_path = None
        for s in self.filtered_sessions:
            status = "[green]●[/]" if s.is_active else " "
            title = _clip(s.display_title, 62)
            if s.custom_title and s.custom_title != s.display_title:
                title = f"[magenta]{_clip(s.custom_title, 18)}[/][dim] · [/]{_clip(s.display_title, 40)}"
            row = [status, s.when_str, title]
            if show_project:
                if s.real_path == prev_path:
                    row.append("[dim]  ↳[/]")
                else:
                    row.append(f"[blue]{_clip(s.project_leaf, 20)}[/]")
            row.append(s.git_branch or "-")
            row.append(str(s.total_messages))
            prev_path = s.real_path
            # jsonl_path is unique per session file; session_id can collide when
            # the same session exists under multiple project dirs.
            table.add_row(*row, key=str(s.jsonl_path))

    def _update_stats(self) -> None:
        stats = get_summary_stats(self.sessions)
        sort_label = dict(self.SORT_MODES)[self.sort_key]
        arrow = "▾" if self.sort_reverse else "▴"
        stats_bar = self.query_one("#stats-bar", Static)
        stats_bar.update(
            f" {stats['total_sessions']} sessions | "
            f"{stats['total_projects']} projects | "
            f"[green]{stats['active_sessions']} active[/] | "
            f"[dim]{stats['total_size']}[/] | "
            f"View: {_clip(self.selected_label, 24)} ({len(self.filtered_sessions)}) | "
            f"Sort: {sort_label} {arrow}"
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

    @on(Tree.NodeHighlighted, "#project-tree")
    def on_tree_highlight(self, event: Tree.NodeHighlighted) -> None:
        data = event.node.data or {"path": ALL_PROJECTS, "group": True}
        self.selected_path = data["path"]
        self.selected_group = data["group"]
        if self.selected_path == ALL_PROJECTS:
            self.selected_label = "All projects"
        else:
            self.selected_label = self.selected_path.rstrip("/").rsplit("/", 1)[-1]
        self._apply_filter()
        self._update_stats()

    @on(Input.Changed, "#filter-input")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self.filter_text = event.value
        self._apply_filter()
        self._update_stats()

    def action_show_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_switch_panel(self) -> None:
        tree = self.query_one("#project-tree", Tree)
        table = self.query_one("#sessions-table", DataTable)
        if tree.has_focus:
            table.focus()
        else:
            tree.focus()

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
        keys = [k for k, _ in self.SORT_MODES]
        idx = keys.index(self.sort_key)
        self.sort_key = keys[(idx + 1) % len(keys)]
        # Title reads best A→Z; the rest read best newest/biggest first.
        self.sort_reverse = self.sort_key != "title"
        self._apply_filter()
        self._update_stats()
        self._set_status(f"Sorted by {dict(self.SORT_MODES)[self.sort_key]}")

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
        cwd = session.cwd or session.real_path
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
