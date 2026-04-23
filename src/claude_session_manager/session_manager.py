"""Core module for discovering, parsing, and managing Claude Code sessions."""

import json
import os
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"
SESSIONS_DIR = CLAUDE_DIR / "sessions"
FILE_HISTORY_DIR = CLAUDE_DIR / "file-history"
SESSION_ENV_DIR = CLAUDE_DIR / "session-env"


@dataclass
class SessionInfo:
    session_id: str
    project_dir: str  # e.g. "-Users-john-projects-myapp"
    project_path: str  # human-readable, e.g. "/Users/john/projects/myapp"
    jsonl_path: Path
    first_message: str = ""
    started_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    user_message_count: int = 0
    assistant_message_count: int = 0
    total_messages: int = 0
    file_size: int = 0  # bytes, JSONL file only
    total_size: int = 0  # bytes, including subdirs
    git_branch: str = ""
    version: str = ""
    cwd: str = ""
    is_active: bool = False
    active_pid: Optional[int] = None
    slug: str = ""
    last_user_message: str = ""
    last_assistant_message: str = ""
    last_prompt: str = ""
    pr_links: list = field(default_factory=list)

    @property
    def duration_str(self) -> str:
        if not self.started_at or not self.last_activity:
            return "N/A"
        delta = self.last_activity - self.started_at
        total_secs = int(delta.total_seconds())
        if total_secs < 60:
            return f"{total_secs}s"
        if total_secs < 3600:
            return f"{total_secs // 60}m"
        hours = total_secs // 3600
        mins = (total_secs % 3600) // 60
        return f"{hours}h {mins}m"

    @property
    def size_str(self) -> str:
        return _format_size(self.total_size)

    @property
    def file_size_str(self) -> str:
        return _format_size(self.file_size)

    @property
    def started_str(self) -> str:
        if not self.started_at:
            return "Unknown"
        return self.started_at.strftime("%Y-%m-%d %H:%M")

    @property
    def topic(self) -> str:
        """Short topic from first user message."""
        msg = self.first_message
        if len(msg) > 80:
            return msg[:77] + "..."
        return msg or "(empty session)"


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _project_dir_to_path(project_dir: str) -> str:
    """Convert project directory name to human-readable path."""
    return "/" + project_dir.lstrip("-").replace("-", "/")


def _dir_size(path: Path) -> int:
    """Calculate total size of a directory recursively."""
    total = 0
    if path.is_dir():
        for entry in path.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
    return total


def _get_active_sessions() -> dict[str, int]:
    """Return map of session_id -> pid for active sessions."""
    active = {}
    if SESSIONS_DIR.is_dir():
        for f in SESSIONS_DIR.iterdir():
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    sid = data.get("sessionId")
                    pid = data.get("pid")
                    if sid and pid:
                        # Check if PID is actually running
                        try:
                            os.kill(pid, 0)
                            active[sid] = pid
                        except (ProcessLookupError, PermissionError):
                            pass
                except (json.JSONDecodeError, OSError):
                    pass
    return active


def _parse_session_jsonl(jsonl_path: Path, max_lines: int = 200) -> dict:
    """Parse a session JSONL file to extract metadata.

    Only reads up to max_lines from the start and scans from the end
    for efficiency with large files.
    """
    result = {
        "first_message": "",
        "started_at": None,
        "last_activity": None,
        "user_count": 0,
        "assistant_count": 0,
        "total": 0,
        "git_branch": "",
        "version": "",
        "cwd": "",
        "slug": "",
        "last_user_message": "",
        "last_assistant_message": "",
        "last_prompt": "",
        "pr_links": [],
    }

    try:
        lines = jsonl_path.read_text().splitlines()
    except OSError:
        return result

    first_user_found = False
    first_timestamp = None
    last_timestamp = None

    for line in lines:
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue

        entry_type = entry.get("type")
        timestamp_str = entry.get("timestamp")

        if timestamp_str and isinstance(timestamp_str, str):
            try:
                ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                if first_timestamp is None:
                    first_timestamp = ts
                last_timestamp = ts
            except ValueError:
                pass

        if entry_type == "user":
            result["user_count"] += 1
            result["total"] += 1

            msg = entry.get("message", {})
            content = msg.get("content", "")
            content_text = ""
            if isinstance(content, str):
                content_text = content.strip()
            elif isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        texts.append(block)
                content_text = " ".join(texts).strip()

            # Skip auto-generated messages (hooks, commands, skills) for topic
            is_auto = (
                content_text.startswith("<local-command")
                or content_text.startswith("<command-")
                or content_text.startswith("<bash-input>")
                or content_text.startswith("<bash-stdout>")
                or content_text.startswith("Base directory for this skill:")
            )

            if not first_user_found or (not result["first_message"] and not is_auto):
                first_user_found = True
                if not is_auto:
                    result["first_message"] = content_text[:200]

            # Track last real user message
            if not is_auto and content_text:
                result["last_user_message"] = content_text[:200]

            # Extract metadata from earliest user message
            if not result["cwd"]:
                result["git_branch"] = entry.get("gitBranch", "")
                result["version"] = entry.get("version", "")
                result["cwd"] = entry.get("cwd", "")

        elif entry_type in ("assistant", "message"):
            result["assistant_count"] += 1
            result["total"] += 1
            # Track last assistant text response
            content = entry.get("message", {}).get("content", [])
            if isinstance(content, list):
                texts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                if texts:
                    result["last_assistant_message"] = " ".join(texts).strip()[:300]

        elif entry_type == "system":
            result["total"] += 1
            slug = entry.get("slug")
            if slug:
                result["slug"] = slug

        elif entry_type == "last-prompt":
            result["last_prompt"] = entry.get("lastPrompt", "")[:200]

        elif entry_type == "pr-link":
            pr_url = entry.get("prUrl", "")
            if pr_url and pr_url not in result["pr_links"]:
                result["pr_links"].append(pr_url)

        else:
            result["total"] += 1

    result["started_at"] = first_timestamp
    result["last_activity"] = last_timestamp
    return result


def discover_sessions() -> list[SessionInfo]:
    """Discover all Claude Code sessions across all projects."""
    sessions = []
    active_map = _get_active_sessions()

    if not PROJECTS_DIR.is_dir():
        return sessions

    for project_dir in sorted(PROJECTS_DIR.iterdir()):
        if not project_dir.is_dir():
            continue

        project_name = project_dir.name
        project_path = _project_dir_to_path(project_name)

        for jsonl_file in sorted(project_dir.glob("*.jsonl")):
            session_id = jsonl_file.stem
            # Skip backup files
            if session_id.endswith(".backup"):
                continue

            try:
                file_size = jsonl_file.stat().st_size
            except OSError:
                file_size = 0

            # Calculate total size including session subdirectory
            session_subdir = project_dir / session_id
            total_size = file_size + _dir_size(session_subdir)

            # Parse the JSONL
            metadata = _parse_session_jsonl(jsonl_file)

            is_active = session_id in active_map
            active_pid = active_map.get(session_id)

            session = SessionInfo(
                session_id=session_id,
                project_dir=project_name,
                project_path=project_path,
                jsonl_path=jsonl_file,
                first_message=metadata["first_message"],
                started_at=metadata["started_at"],
                last_activity=metadata["last_activity"],
                user_message_count=metadata["user_count"],
                assistant_message_count=metadata["assistant_count"],
                total_messages=metadata["total"],
                file_size=file_size,
                total_size=total_size,
                git_branch=metadata["git_branch"],
                version=metadata["version"],
                cwd=metadata["cwd"],
                is_active=is_active,
                active_pid=active_pid,
                slug=metadata["slug"],
                last_user_message=metadata["last_user_message"],
                last_assistant_message=metadata["last_assistant_message"],
                last_prompt=metadata["last_prompt"],
                pr_links=metadata["pr_links"],
            )
            sessions.append(session)

    # Sort by most recent first
    sessions.sort(key=lambda s: s.started_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return sessions


def delete_session(session: SessionInfo) -> dict[str, bool]:
    """Delete a session and all its associated data.

    Returns a dict of what was deleted successfully.
    """
    if session.is_active:
        raise ValueError(
            f"Cannot delete active session {session.session_id} "
            f"(PID {session.active_pid}). Stop it first."
        )

    results = {}

    # 1. Delete the JSONL file
    try:
        session.jsonl_path.unlink()
        results["jsonl"] = True
    except OSError:
        results["jsonl"] = False

    # 2. Delete session subdirectory (tool-results, subagents)
    session_subdir = session.jsonl_path.parent / session.session_id
    if session_subdir.is_dir():
        try:
            shutil.rmtree(session_subdir)
            results["session_dir"] = True
        except OSError:
            results["session_dir"] = False

    # 3. Delete file history
    file_history = FILE_HISTORY_DIR / session.session_id
    if file_history.is_dir():
        try:
            shutil.rmtree(file_history)
            results["file_history"] = True
        except OSError:
            results["file_history"] = False

    # 4. Delete session env
    session_env = SESSION_ENV_DIR / session.session_id
    if session_env.is_dir():
        try:
            shutil.rmtree(session_env)
            results["session_env"] = True
        except OSError:
            results["session_env"] = False

    # 5. Clean up stale PID files in sessions dir
    if SESSIONS_DIR.is_dir():
        for f in SESSIONS_DIR.iterdir():
            if f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    if data.get("sessionId") == session.session_id:
                        f.unlink()
                        results["pid_file"] = True
                except (json.JSONDecodeError, OSError):
                    pass

    return results


def get_summary_stats(sessions: list[SessionInfo]) -> dict:
    """Get aggregate statistics across all sessions."""
    total_size = sum(s.total_size for s in sessions)
    total_messages = sum(s.total_messages for s in sessions)
    projects = set(s.project_dir for s in sessions)
    active_count = sum(1 for s in sessions if s.is_active)

    return {
        "total_sessions": len(sessions),
        "total_size": _format_size(total_size),
        "total_size_bytes": total_size,
        "total_messages": total_messages,
        "total_projects": len(projects),
        "active_sessions": active_count,
    }
