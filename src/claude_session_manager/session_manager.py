"""Core module for discovering, parsing, and managing Claude Code sessions."""

import json
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_IMAGE_MARKER_RE = re.compile(r"\[Image #\d+\]\s*")


def humanize_snippet(text: str) -> str:
    """Collapse whitespace and strip attachment markers for display as a label."""
    text = _IMAGE_MARKER_RE.sub("", text or "")
    return " ".join(text.split())


def relative_time(dt: Optional[datetime]) -> str:
    """Human 'time ago' string, falling back to an absolute date for old items."""
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    secs = int((datetime.now(timezone.utc) - dt).total_seconds())
    if secs < 0:
        secs = 0
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m ago"
    if secs < 86400:
        return f"{secs // 3600}h ago"
    days = secs // 86400
    if days < 7:
        return f"{days}d ago"
    if days < 28:
        return f"{days // 7}w ago"
    return dt.astimezone().strftime("%b %d")


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
    ai_title: str = ""  # AI-generated one-line summary of the session
    custom_title: str = ""  # user-assigned name for the session
    agent_name: str = ""  # name of the agent, when run as a named agent
    last_user_message: str = ""
    last_assistant_message: str = ""
    last_prompt: str = ""
    pr_links: list = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_cache_read_tokens: int = 0
    models_used: list = field(default_factory=list)
    web_search_count: int = 0
    web_fetch_count: int = 0
    service_tier: str = ""

    @property
    def total_tokens(self) -> int:
        return (
            self.total_input_tokens
            + self.total_output_tokens
            + self.total_cache_creation_tokens
            + self.total_cache_read_tokens
        )

    @property
    def cache_hit_ratio_str(self) -> str:
        denom = (
            self.total_input_tokens
            + self.total_cache_read_tokens
            + self.total_cache_creation_tokens
        )
        if denom == 0:
            return "N/A"
        return f"{(self.total_cache_read_tokens / denom) * 100:.1f}%"

    @property
    def tokens_total_str(self) -> str:
        return _format_tokens(self.total_tokens)

    @property
    def tokens_in_str(self) -> str:
        return _format_tokens(self.total_input_tokens)

    @property
    def tokens_out_str(self) -> str:
        return _format_tokens(self.total_output_tokens)

    @property
    def tokens_cache_read_str(self) -> str:
        return _format_tokens(self.total_cache_read_tokens)

    @property
    def tokens_cache_creation_str(self) -> str:
        return _format_tokens(self.total_cache_creation_tokens)

    @property
    def models_str(self) -> str:
        return ", ".join(self.models_used) if self.models_used else "N/A"

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

    def _clean_first_message(self) -> str:
        """First user message collapsed to a single line, for use as a fallback label."""
        return humanize_snippet(self.first_message)

    @property
    def real_path(self) -> str:
        """Authoritative project path.

        ``project_path`` is derived from the encoded project-dir name, which
        replaces every '/' with '-' and is therefore lossy for folders that
        contain hyphens (e.g. 'unstract-repos' becomes 'unstract/repos'). The
        session's recorded ``cwd`` is the real on-disk path, so prefer it.
        """
        return self.cwd or self.project_path

    @property
    def real_path_short(self) -> str:
        """Real path with the home directory collapsed to '~'."""
        home = str(Path.home())
        path = self.real_path
        if path.startswith(home):
            return "~" + path[len(home):]
        return path

    @property
    def project_leaf(self) -> str:
        """The final folder name of the real path (e.g. 'unstract-repos')."""
        return self.real_path.rstrip("/").rsplit("/", 1)[-1] or self.real_path

    @property
    def when_str(self) -> str:
        """Relative 'time ago' for the most recent activity."""
        return relative_time(self.last_activity or self.started_at)

    @property
    def last_activity_str(self) -> str:
        if not self.last_activity:
            return "Unknown"
        return self.last_activity.strftime("%Y-%m-%d %H:%M")

    @property
    def display_title(self) -> str:
        """Best human-readable line for this session.

        Prefers the AI-generated summary (the most descriptive single line),
        then a user-assigned name, then the first user message, so lists show
        something meaningful instead of a pasted URL or a bare UUID. The
        user-assigned name is surfaced separately as a short tag / "Name" field.
        """
        if self.ai_title:
            return self.ai_title
        if self.custom_title:
            return self.custom_title
        return self._clean_first_message() or "(untitled session)"

    @property
    def has_title(self) -> bool:
        """True when a real name/summary exists (not just the raw first message)."""
        return bool(self.custom_title or self.ai_title)

    @property
    def subtitle(self) -> str:
        """Secondary context line: the raw first prompt, for extra context.

        Suppressed when it would merely echo the title (the AI summary is usually
        derived from the first message, so the two are frequently near-duplicates).
        """
        candidate = self._clean_first_message()
        if not candidate:
            return ""
        a = " ".join(candidate.lower().split())
        b = " ".join(self.display_title.lower().split())
        if a == b or a.startswith(b) or b.startswith(a):
            return ""
        return candidate


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _format_tokens(n: int) -> str:
    if n < 1000:
        return str(n)
    if n < 1_000_000:
        return f"{n / 1000:.1f}K"
    return f"{n / 1_000_000:.1f}M"


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
        "ai_title": "",
        "custom_title": "",
        "agent_name": "",
        "last_user_message": "",
        "last_assistant_message": "",
        "last_prompt": "",
        "pr_links": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cache_creation_tokens": 0,
        "total_cache_read_tokens": 0,
        "models_used": [],
        "web_search_count": 0,
        "web_fetch_count": 0,
        "service_tier": "",
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
            msg = entry.get("message", {})
            if not isinstance(msg, dict):
                msg = {}

            # Track last assistant text response
            content = msg.get("content", [])
            if isinstance(content, list):
                texts = [
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and b.get("type") == "text"
                ]
                if texts:
                    result["last_assistant_message"] = " ".join(texts).strip()[:300]

            # Aggregate token usage
            usage = msg.get("usage")
            if isinstance(usage, dict):
                result["total_input_tokens"] += usage.get("input_tokens", 0) or 0
                result["total_output_tokens"] += usage.get("output_tokens", 0) or 0
                result["total_cache_creation_tokens"] += (
                    usage.get("cache_creation_input_tokens", 0) or 0
                )
                result["total_cache_read_tokens"] += (
                    usage.get("cache_read_input_tokens", 0) or 0
                )
                tier = usage.get("service_tier")
                if isinstance(tier, str) and tier:
                    result["service_tier"] = tier
                stu = usage.get("server_tool_use")
                if isinstance(stu, dict):
                    result["web_search_count"] += stu.get("web_search_requests", 0) or 0
                    result["web_fetch_count"] += stu.get("web_fetch_requests", 0) or 0

            # Track models seen, in first-seen order
            model = msg.get("model")
            if isinstance(model, str) and model and model not in result["models_used"]:
                result["models_used"].append(model)

        elif entry_type == "system":
            result["total"] += 1
            slug = entry.get("slug")
            if slug:
                result["slug"] = slug

        elif entry_type == "ai-title":
            # Metadata entries were previously counted via the catch-all below;
            # keep counting them so message totals are unchanged.
            result["total"] += 1
            # Session may carry several as it evolves; the latest wins.
            title = entry.get("aiTitle")
            if isinstance(title, str) and title.strip():
                result["ai_title"] = title.strip()

        elif entry_type == "custom-title":
            result["total"] += 1
            title = entry.get("customTitle")
            if isinstance(title, str) and title.strip():
                result["custom_title"] = title.strip()

        elif entry_type == "agent-name":
            result["total"] += 1
            name = entry.get("agentName")
            if isinstance(name, str) and name.strip():
                result["agent_name"] = name.strip()

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
                ai_title=metadata["ai_title"],
                custom_title=metadata["custom_title"],
                agent_name=metadata["agent_name"],
                last_user_message=metadata["last_user_message"],
                last_assistant_message=metadata["last_assistant_message"],
                last_prompt=metadata["last_prompt"],
                pr_links=metadata["pr_links"],
                total_input_tokens=metadata["total_input_tokens"],
                total_output_tokens=metadata["total_output_tokens"],
                total_cache_creation_tokens=metadata["total_cache_creation_tokens"],
                total_cache_read_tokens=metadata["total_cache_read_tokens"],
                models_used=metadata["models_used"],
                web_search_count=metadata["web_search_count"],
                web_fetch_count=metadata["web_fetch_count"],
                service_tier=metadata["service_tier"],
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


_WORKTREE_MARKER = "/.claude/worktrees/"


def _area_and_leaf(real_path: str, home: str) -> dict:
    """Classify a working directory into a top-level "area" group and a leaf label.

    The area is the first folder under the user's home (e.g. 'zipstack',
    'unstract-repos', 'personal'), or the parent directory for paths outside
    home. The leaf is the working directory itself, labelled by its basename
    with a short parent hint when it is nested below the area. This keeps the
    sidebar to two shallow levels keyed on the real working dir, instead of a
    deep mirror of the filesystem.
    """
    p = real_path.rstrip("/") or "/"
    is_worktree = _WORKTREE_MARKER in p

    if p == home:
        return {"area_path": home, "area_label": "~", "leaf_label": "(home)",
                "hint": "", "is_root": True, "worktree": False}

    if p.startswith(home + "/"):
        rel_segs = p[len(home) + 1:].split("/")
        area_path = f"{home}/{rel_segs[0]}"
        area_label = rel_segs[0]
    else:
        segs_all = [s for s in p.split("/") if s]
        if len(segs_all) <= 1:
            area_path, area_label = "/", "/"
        else:
            area_path = "/" + "/".join(segs_all[:-1])
            area_label = "/".join(segs_all[:-1])

    is_root = p == area_path
    within = p[len(area_path):].strip("/")
    within_segs = within.split("/") if within else []
    leaf_label = within_segs[-1] if within_segs else (area_label.rsplit("/", 1)[-1] or area_label)

    hint = ""
    if is_worktree:
        # Belongs to the repo/checkout sitting just before the worktrees dir.
        repo = p.split(_WORKTREE_MARKER)[0].rstrip("/").rsplit("/", 1)[-1]
        hint = f"…/{repo}"
    elif len(within_segs) > 1:
        hint = f"…/{within_segs[-2]}"

    return {"area_path": area_path, "area_label": area_label, "leaf_label": leaf_label,
            "hint": hint, "is_root": is_root, "worktree": is_worktree}


def build_project_tree(sessions: list[SessionInfo]) -> list[dict]:
    """Build a two-level project sidebar: area groups → working-dir leaves.

    Each leaf is a real working directory (the folder you ``cd`` into), labelled
    by its basename. Selecting an area filters to every session beneath it
    (prefix match); selecting a leaf filters to that exact working dir. Sorted by
    most-recent activity throughout.
    """
    from collections import OrderedDict

    home = str(Path.home())
    min_dt = datetime.min.replace(tzinfo=timezone.utc)

    # Aggregate per real working directory (the leaf).
    leaves: "OrderedDict[str, dict]" = OrderedDict()
    for s in sessions:
        rp = s.real_path.rstrip("/") or "/"
        leaf = leaves.get(rp)
        if leaf is None:
            meta = _area_and_leaf(rp, home)
            leaf = leaves[rp] = {
                "path": rp, "is_group": False, "children": [],
                "name": meta["leaf_label"], "hint": meta["hint"],
                "is_root": meta["is_root"], "worktree": meta["worktree"],
                "area_path": meta["area_path"], "area_label": meta["area_label"],
                "count": 0, "size": 0, "active": 0, "_last": None,
            }
        leaf["count"] += 1
        leaf["size"] += s.total_size
        if s.is_active:
            leaf["active"] += 1
        la = s.last_activity or s.started_at
        if la and (leaf["_last"] is None or la > leaf["_last"]):
            leaf["_last"] = la

    # Group leaves into areas.
    areas: "OrderedDict[str, dict]" = OrderedDict()
    for leaf in leaves.values():
        area = areas.get(leaf["area_path"])
        if area is None:
            area = areas[leaf["area_path"]] = {
                "path": leaf["area_path"], "name": leaf["area_label"], "is_group": True,
                "hint": "", "worktree": False, "is_root": False,
                "count": 0, "size": 0, "active": 0, "_last": None, "children": [],
            }
        area["children"].append(leaf)
        area["count"] += leaf["count"]
        area["size"] += leaf["size"]
        area["active"] += leaf["active"]
        if leaf["_last"] and (area["_last"] is None or leaf["_last"] > area["_last"]):
            area["_last"] = leaf["_last"]

    def _finalize(node: dict) -> dict:
        # Sort children by recency while their sort key is still present.
        node["children"].sort(key=lambda c: c["_last"] or min_dt, reverse=True)
        node["size_str"] = _format_size(node["size"])
        node["last_activity"] = node["_last"].isoformat() if node["_last"] else None
        for key in ("_last", "area_path", "area_label"):
            node.pop(key, None)
        for child in node["children"]:
            _finalize(child)
        return node

    result = sorted(areas.values(), key=lambda a: a["_last"] or min_dt, reverse=True)
    return [_finalize(a) for a in result]


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
