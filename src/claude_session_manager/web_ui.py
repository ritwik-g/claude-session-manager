"""Web UI for managing Claude Code sessions.

Uses Python's built-in http.server with embedded HTML/CSS/JS.
No external web framework dependencies.
"""

import json
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from .session_manager import (
    delete_session,
    discover_sessions,
    get_summary_stats,
)

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Claude Sessions Manager</title>
<style>
:root {
    --bg: #1a1b26;
    --bg-surface: #24283b;
    --bg-highlight: #292e42;
    --border: #3b4261;
    --text: #c0caf5;
    --text-muted: #565f89;
    --accent: #7aa2f7;
    --green: #9ece6a;
    --red: #f7768e;
    --orange: #ff9e64;
    --yellow: #e0af68;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
    font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}
.app-body {
    display: flex;
    flex: 1;
    overflow: hidden;
}
#sidebar {
    width: 260px;
    min-width: 260px;
    background: var(--bg-surface);
    border-right: 1px solid var(--border);
    overflow-y: auto;
    padding: 0;
}
#sidebar h3 {
    padding: 12px 16px 8px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
}
.project-item {
    padding: 8px 16px;
    cursor: pointer;
    font-size: 13px;
    border-left: 3px solid transparent;
    transition: all 0.1s;
}
.project-item:hover { background: var(--bg-highlight); }
.project-item.active { background: var(--bg-highlight); border-left-color: var(--accent); color: var(--accent); }
.project-item .proj-name { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.project-item .proj-meta { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.main-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
header {
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
    padding: 16px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky;
    top: 0;
    z-index: 100;
}
header h1 {
    font-size: 18px;
    font-weight: 600;
    color: var(--accent);
}
.stats {
    display: flex;
    gap: 20px;
    font-size: 13px;
    color: var(--text-muted);
}
.stats .stat-value { color: var(--text); font-weight: 600; }
.controls {
    padding: 12px 24px;
    display: flex;
    gap: 12px;
    align-items: center;
    border-bottom: 1px solid var(--border);
    background: var(--bg-surface);
}
#filter {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px 12px;
    border-radius: 6px;
    font-family: inherit;
    font-size: 13px;
    outline: none;
}
#filter:focus { border-color: var(--accent); }
#filter::placeholder { color: var(--text-muted); }
.btn {
    padding: 8px 16px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text);
    border-radius: 6px;
    cursor: pointer;
    font-family: inherit;
    font-size: 13px;
    transition: all 0.15s;
}
.btn:hover { background: var(--bg-highlight); border-color: var(--accent); }
.btn-danger { border-color: var(--red); color: var(--red); }
.btn-danger:hover { background: rgba(247, 118, 142, 0.15); }
.btn-sm { padding: 4px 10px; font-size: 12px; }
table {
    width: 100%;
    border-collapse: collapse;
}
thead { position: sticky; top: 72px; z-index: 10; }
th {
    background: var(--bg-surface);
    padding: 10px 12px;
    text-align: left;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--text-muted);
    border-bottom: 1px solid var(--border);
    cursor: pointer;
    user-select: none;
    white-space: nowrap;
}
th:hover { color: var(--accent); }
th.sorted { color: var(--accent); }
th .arrow { font-size: 10px; margin-left: 4px; }
td {
    padding: 10px 12px;
    border-bottom: 1px solid var(--border);
    font-size: 13px;
    vertical-align: top;
}
tr:hover td { background: var(--bg-highlight); }
tr.active td { border-left: 3px solid var(--green); }
.project { color: var(--accent); font-weight: 500; }
.branch { color: var(--orange); }
.topic {
    max-width: 350px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}
.size { color: var(--text-muted); text-align: right; }
.msgs { text-align: right; }
.date { white-space: nowrap; color: var(--text-muted); }
.active-badge {
    display: inline-block;
    background: rgba(158, 206, 106, 0.2);
    color: var(--green);
    font-size: 11px;
    padding: 2px 6px;
    border-radius: 3px;
    font-weight: 600;
}
.session-id {
    font-size: 11px;
    color: var(--text-muted);
    font-family: inherit;
}
/* Modal */
.modal-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.6);
    z-index: 1000;
    align-items: center;
    justify-content: center;
}
.modal-overlay.active { display: flex; }
.modal {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px;
    width: 550px;
    max-width: 90vw;
    max-height: 80vh;
    overflow-y: auto;
}
.modal h2 { font-size: 16px; margin-bottom: 16px; }
.modal-detail { margin: 8px 0; font-size: 13px; }
.modal-detail .label { color: var(--text-muted); display: inline-block; width: 120px; }
.modal-actions { margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end; }
.toast {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    padding: 12px 20px;
    border-radius: 6px;
    font-size: 13px;
    z-index: 2000;
    animation: fadeIn 0.2s, fadeOut 0.3s 2.7s;
    opacity: 0;
}
.toast.show { opacity: 1; }
.toast.success { border-color: var(--green); color: var(--green); }
.toast.error { border-color: var(--red); color: var(--red); }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
@keyframes fadeOut { from { opacity: 1; } to { opacity: 0; } }
.empty { text-align: center; padding: 40px; color: var(--text-muted); }
.checkbox-col { width: 40px; text-align: center; }
input[type="checkbox"] { accent-color: var(--accent); cursor: pointer; }
#bulk-actions { display: none; gap: 10px; align-items: center; }
#bulk-actions.active { display: flex; }
#bulk-count { font-size: 13px; color: var(--accent); }
.loading { text-align: center; padding: 40px; color: var(--text-muted); }
</style>
</head>
<body>
<header>
    <h1>&gt;_ Claude Sessions Manager</h1>
    <div class="stats" id="stats"></div>
</header>
<div class="app-body">
<div id="sidebar">
    <h3>Projects</h3>
    <div id="project-list"></div>
</div>
<div class="main-content">
<div class="controls">
    <input type="text" id="filter" placeholder="Filter by topic, branch...">
    <div id="bulk-actions">
        <span id="bulk-count">0 selected</span>
        <button class="btn btn-danger btn-sm" onclick="bulkDelete()">Delete Selected</button>
    </div>
    <button class="btn" onclick="refresh()">Refresh</button>
</div>
<div style="flex:1;overflow:auto">
<table>
    <thead>
        <tr>
            <th class="checkbox-col"><input type="checkbox" id="select-all" onchange="toggleSelectAll(this)"></th>
            <th data-sort="date" class="sorted">Date <span class="arrow">v</span></th>
            <th data-sort="project">Project</th>
            <th>Branch</th>
            <th>Topic</th>
            <th>Last Response</th>
            <th data-sort="messages" style="text-align:right">Msgs</th>
            <th data-sort="size" style="text-align:right">Size</th>
            <th>Actions</th>
        </tr>
    </thead>
    <tbody id="session-list">
        <tr><td colspan="9" class="loading">Loading sessions...</td></tr>
    </tbody>
</table>

<!-- Detail Modal -->
<div class="modal-overlay" id="detail-modal">
    <div class="modal">
        <h2>Session Details</h2>
        <div id="detail-content"></div>
        <div class="modal-actions">
            <button class="btn" onclick="closeModal('detail-modal')">Close</button>
        </div>
    </div>
</div>

<!-- Delete Confirm Modal -->
<div class="modal-overlay" id="delete-modal">
    <div class="modal">
        <h2 style="color: var(--red)">Confirm Delete</h2>
        <div id="delete-content"></div>
        <div class="modal-actions">
            <button class="btn" onclick="closeModal('delete-modal')">Cancel</button>
            <button class="btn btn-danger" id="confirm-delete-btn">Delete</button>
        </div>
    </div>
</div>

<div class="toast" id="toast"></div>
</div><!-- /table wrapper -->
</div><!-- /main-content -->
</div><!-- /app-body -->

<script>
let sessions = [];
let sortKey = 'date';
let sortReverse = true;
let selected = new Set();
let selectedProject = '__all__';

async function fetchSessions() {
    const resp = await fetch('/api/sessions');
    const data = await resp.json();
    sessions = data.sessions;
    updateStats(data.stats);
    renderSidebar();
    renderTable();
}

function renderSidebar() {
    const projects = {};
    sessions.forEach(s => {
        if (!projects[s.project_path]) projects[s.project_path] = { count: 0, size: 0, active: 0 };
        projects[s.project_path].count++;
        projects[s.project_path].size += s.total_size;
        if (s.is_active) projects[s.project_path].active++;
    });
    const sorted = Object.entries(projects).sort((a, b) => b[1].size - a[1].size);
    const container = document.getElementById('project-list');
    let html = `<div class="project-item ${selectedProject === '__all__' ? 'active' : ''}" onclick="selectProject('__all__')">
        <span class="proj-name">All Projects</span>
        <span class="proj-meta">${sessions.length} sessions, ${formatSize(sessions.reduce((a,s) => a + s.total_size, 0))}</span>
    </div>`;
    sorted.forEach(([path, info]) => {
        const active = selectedProject === path ? ' active' : '';
        const marker = info.active > 0 ? ' <span style="color:var(--green)">*</span>' : '';
        html += `<div class="project-item${active}" onclick="selectProject('${escapeHtml(path)}')">
            <span class="proj-name">${escapeHtml(shortProject(path))}${marker}</span>
            <span class="proj-meta">${info.count} sessions, ${formatSize(info.size)}</span>
        </div>`;
    });
    container.innerHTML = html;
}

function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
    if (bytes < 1024*1024*1024) return (bytes/(1024*1024)).toFixed(1) + ' MB';
    return (bytes/(1024*1024*1024)).toFixed(1) + ' GB';
}

function selectProject(path) {
    selectedProject = path;
    renderSidebar();
    renderTable();
}

function updateStats(stats) {
    document.getElementById('stats').innerHTML =
        `<span><span class="stat-value">${stats.total_sessions}</span> sessions</span>` +
        `<span><span class="stat-value">${stats.total_projects}</span> projects</span>` +
        `<span><span class="stat-value">${stats.total_size}</span> total</span>` +
        `<span><span class="stat-value">${stats.active_sessions}</span> active</span>`;
}

function getFiltered() {
    const ft = document.getElementById('filter').value.toLowerCase();
    let filtered = sessions;
    if (selectedProject !== '__all__') {
        filtered = filtered.filter(s => s.project_path === selectedProject);
    }
    if (ft) {
        filtered = filtered.filter(s =>
            s.project_path.toLowerCase().includes(ft) ||
            s.first_message.toLowerCase().includes(ft) ||
            s.last_user_message.toLowerCase().includes(ft) ||
            s.last_assistant_message.toLowerCase().includes(ft) ||
            s.git_branch.toLowerCase().includes(ft) ||
            s.session_id.toLowerCase().includes(ft)
        );
    }
    // Sort
    filtered.sort((a, b) => {
        let va, vb;
        if (sortKey === 'date') { va = a.started_at || ''; vb = b.started_at || ''; }
        else if (sortKey === 'project') { va = a.project_path; vb = b.project_path; }
        else if (sortKey === 'messages') { va = a.total_messages; vb = b.total_messages; }
        else if (sortKey === 'size') { va = a.total_size; vb = b.total_size; }
        if (va < vb) return sortReverse ? 1 : -1;
        if (va > vb) return sortReverse ? -1 : 1;
        return 0;
    });
    return filtered;
}

function renderTable() {
    const filtered = getFiltered();
    const tbody = document.getElementById('session-list');
    if (filtered.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="empty">No sessions found</td></tr>';
        return;
    }
    tbody.innerHTML = filtered.map(s => {
        const active = s.is_active ? ' active' : '';
        const badge = s.is_active ? `<span class="active-badge">ACTIVE (PID ${s.active_pid})</span>` : '';
        const checked = selected.has(s.session_id) ? 'checked' : '';
        const deleteDisabled = s.is_active ? 'disabled title="Cannot delete active session"' : '';
        const lastResp = s.last_assistant_message ? (s.last_assistant_message.length > 60 ? s.last_assistant_message.substring(0, 60) + '...' : s.last_assistant_message) : '-';
        return `<tr class="${active}">
            <td class="checkbox-col"><input type="checkbox" ${checked} ${s.is_active ? 'disabled' : ''} onchange="toggleSelect('${s.session_id}', this)"></td>
            <td class="date">${s.started_str} ${badge}</td>
            <td class="project">${shortProject(s.project_path)}</td>
            <td class="branch">${s.git_branch || '-'}</td>
            <td class="topic" title="${escapeHtml(s.first_message)}">${escapeHtml(s.topic)}</td>
            <td class="topic" title="${escapeHtml(s.last_assistant_message)}">${escapeHtml(lastResp)}</td>
            <td class="msgs">${s.total_messages}</td>
            <td class="size">${s.size_str}</td>
            <td>
                <button class="btn btn-sm" onclick="showDetail('${s.session_id}')">Info</button>
                <button class="btn btn-sm btn-danger" onclick="confirmDelete('${s.session_id}')" ${deleteDisabled}>Del</button>
            </td>
        </tr>`;
    }).join('');
    updateBulkActions();
}

function shortProject(path) {
    const home = '/Users/' + path.split('/')[2];
    if (path.startsWith(home)) path = '~' + path.substring(home.length);
    const parts = path.split('/');
    if (parts.length > 4) return parts.slice(0,2).join('/') + '/.../' + parts.slice(-2).join('/');
    return path;
}

function escapeHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function toggleSelect(id, cb) {
    if (cb.checked) selected.add(id); else selected.delete(id);
    updateBulkActions();
}
function toggleSelectAll(cb) {
    const filtered = getFiltered();
    if (cb.checked) {
        filtered.forEach(s => { if (!s.is_active) selected.add(s.session_id); });
    } else {
        selected.clear();
    }
    renderTable();
}
function updateBulkActions() {
    const ba = document.getElementById('bulk-actions');
    const count = selected.size;
    if (count > 0) {
        ba.classList.add('active');
        document.getElementById('bulk-count').textContent = `${count} selected`;
    } else {
        ba.classList.remove('active');
    }
}

function showDetail(id) {
    const s = sessions.find(x => x.session_id === id);
    if (!s) return;
    const content = document.getElementById('detail-content');
    content.innerHTML = `
        <div class="modal-detail"><span class="label">Session ID:</span> <span class="session-id">${s.session_id}</span></div>
        <div class="modal-detail"><span class="label">Status:</span> ${s.is_active ? '<span style="color:var(--green)">ACTIVE (PID ' + s.active_pid + ')</span>' : 'Inactive'}</div>
        <div class="modal-detail"><span class="label">Project:</span> <span class="project">${escapeHtml(s.project_path)}</span></div>
        <div class="modal-detail"><span class="label">Working Dir:</span> ${escapeHtml(s.cwd)}</div>
        <div class="modal-detail"><span class="label">Git Branch:</span> <span class="branch">${s.git_branch || 'N/A'}</span></div>
        <div class="modal-detail"><span class="label">Version:</span> ${s.version || 'N/A'}</div>
        <div class="modal-detail"><span class="label">Started:</span> ${s.started_str}</div>
        <div class="modal-detail"><span class="label">Duration:</span> ${s.duration_str}</div>
        <div class="modal-detail"><span class="label">Messages:</span> ${s.user_message_count} user / ${s.assistant_message_count} assistant / ${s.total_messages} total</div>
        <div class="modal-detail"><span class="label">JSONL Size:</span> ${s.file_size_str}</div>
        <div class="modal-detail"><span class="label">Total Size:</span> ${s.size_str}</div>
        ${s.pr_links && s.pr_links.length ? '<div class="modal-detail"><span class="label">PRs Created:</span> ' + s.pr_links.map(l => '<a href="' + escapeHtml(l) + '" target="_blank" style="color:var(--accent)">' + escapeHtml(l) + '</a>').join(', ') + '</div>' : ''}
        <hr style="border-color:var(--border);margin:12px 0">
        <div class="modal-detail"><span class="label">First Message:</span></div>
        <div style="margin-top:8px;padding:10px;background:var(--bg);border-radius:4px;font-size:13px;white-space:pre-wrap;max-height:150px;overflow-y:auto">${escapeHtml(s.first_message || '(empty)')}</div>
        ${s.last_user_message && s.last_user_message !== s.first_message ? '<div class="modal-detail" style="margin-top:12px"><span class="label">Last User Msg:</span></div><div style="margin-top:8px;padding:10px;background:var(--bg);border-radius:4px;font-size:13px;white-space:pre-wrap;max-height:150px;overflow-y:auto">' + escapeHtml(s.last_user_message) + '</div>' : ''}
        ${s.last_assistant_message ? '<div class="modal-detail" style="margin-top:12px"><span class="label">Last Response:</span></div><div style="margin-top:8px;padding:10px;background:var(--bg);border-radius:4px;font-size:13px;white-space:pre-wrap;max-height:150px;overflow-y:auto;color:var(--accent)">' + escapeHtml(s.last_assistant_message) + '</div>' : ''}
    `;
    openModal('detail-modal');
}

function confirmDelete(id) {
    const s = sessions.find(x => x.session_id === id);
    if (!s || s.is_active) return;
    const content = document.getElementById('delete-content');
    content.innerHTML = `
        <p>Are you sure you want to delete this session?</p>
        <div class="modal-detail"><span class="label">Project:</span> ${escapeHtml(s.project_path)}</div>
        <div class="modal-detail"><span class="label">Topic:</span> ${escapeHtml(s.topic)}</div>
        <div class="modal-detail"><span class="label">Date:</span> ${s.started_str}</div>
        <div class="modal-detail"><span class="label">Size:</span> ${s.size_str}</div>
        <p style="color:var(--red);margin-top:12px">This action cannot be undone.</p>
    `;
    const btn = document.getElementById('confirm-delete-btn');
    btn.onclick = () => doDelete(id);
    openModal('delete-modal');
}

async function doDelete(id) {
    closeModal('delete-modal');
    try {
        const resp = await fetch('/api/sessions/' + id, { method: 'DELETE' });
        const data = await resp.json();
        if (data.ok) {
            showToast('Session deleted', 'success');
            selected.delete(id);
            await fetchSessions();
        } else {
            showToast('Error: ' + data.error, 'error');
        }
    } catch (e) {
        showToast('Error: ' + e.message, 'error');
    }
}

async function bulkDelete() {
    if (selected.size === 0) return;
    const count = selected.size;
    if (!confirm(`Delete ${count} selected session(s)? This cannot be undone.`)) return;
    let deleted = 0, errors = 0;
    for (const id of [...selected]) {
        try {
            const resp = await fetch('/api/sessions/' + id, { method: 'DELETE' });
            const data = await resp.json();
            if (data.ok) { deleted++; selected.delete(id); }
            else errors++;
        } catch { errors++; }
    }
    showToast(`Deleted ${deleted} session(s)${errors ? ', ' + errors + ' error(s)' : ''}`, errors ? 'error' : 'success');
    await fetchSessions();
}

function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function showToast(msg, type) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.className = 'toast show ' + type;
    setTimeout(() => t.className = 'toast', 3000);
}
function refresh() {
    document.getElementById('session-list').innerHTML = '<tr><td colspan="9" class="loading">Loading...</td></tr>';
    fetchSessions();
}

// Sort headers
document.querySelectorAll('th[data-sort]').forEach(th => {
    th.addEventListener('click', () => {
        const key = th.dataset.sort;
        if (sortKey === key) sortReverse = !sortReverse;
        else { sortKey = key; sortReverse = key !== 'project'; }
        // Update header indicators
        document.querySelectorAll('th[data-sort]').forEach(h => {
            h.classList.remove('sorted');
            h.querySelector('.arrow')?.remove();
        });
        th.classList.add('sorted');
        th.insertAdjacentHTML('beforeend', `<span class="arrow">${sortReverse ? 'v' : '^'}</span>`);
        renderTable();
    });
});

// Filter
document.getElementById('filter').addEventListener('input', () => renderTable());

// Keyboard shortcuts
document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT') return;
    if (e.key === '/') { e.preventDefault(); document.getElementById('filter').focus(); }
    if (e.key === 'Escape') {
        closeModal('detail-modal');
        closeModal('delete-modal');
    }
});

// Initial load
fetchSessions();
</script>
</body>
</html>"""


def _session_to_dict(s) -> dict:
    return {
        "session_id": s.session_id,
        "project_dir": s.project_dir,
        "project_path": s.project_path,
        "first_message": s.first_message,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "last_activity": s.last_activity.isoformat() if s.last_activity else None,
        "started_str": s.started_str,
        "duration_str": s.duration_str,
        "topic": s.topic,
        "user_message_count": s.user_message_count,
        "assistant_message_count": s.assistant_message_count,
        "total_messages": s.total_messages,
        "file_size": s.file_size,
        "file_size_str": s.file_size_str,
        "total_size": s.total_size,
        "size_str": s.size_str,
        "git_branch": s.git_branch,
        "version": s.version,
        "cwd": s.cwd,
        "is_active": s.is_active,
        "active_pid": s.active_pid,
        "slug": s.slug,
        "last_user_message": s.last_user_message,
        "last_assistant_message": s.last_assistant_message,
        "last_prompt": s.last_prompt,
        "pr_links": s.pr_links,
    }


class SessionAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the session manager API and web UI."""

    sessions_cache: list | None = None

    def log_message(self, format, *args):
        # Suppress default logging
        pass

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str):
        body = html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _refresh_cache(self):
        SessionAPIHandler.sessions_cache = discover_sessions()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/" or parsed.path == "":
            self._send_html(HTML_PAGE)
            return

        if parsed.path == "/api/sessions":
            self._refresh_cache()
            sessions = SessionAPIHandler.sessions_cache or []
            stats = get_summary_stats(sessions)
            self._send_json({
                "sessions": [_session_to_dict(s) for s in sessions],
                "stats": stats,
            })
            return

        self.send_error(404, "Not found")

    def do_DELETE(self):
        parsed = urlparse(self.path)

        # /api/sessions/<session_id>
        if parsed.path.startswith("/api/sessions/"):
            session_id = parsed.path.split("/")[-1]
            sessions = SessionAPIHandler.sessions_cache or discover_sessions()
            session = next((s for s in sessions if s.session_id == session_id), None)

            if not session:
                self._send_json({"ok": False, "error": "Session not found"}, 404)
                return

            if session.is_active:
                self._send_json(
                    {"ok": False, "error": f"Cannot delete active session (PID {session.active_pid})"},
                    400,
                )
                return

            try:
                results = delete_session(session)
                self._refresh_cache()
                self._send_json({"ok": True, "deleted": results})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, 500)
            return

        self.send_error(404, "Not found")


def run_web(port: int = 8420, open_browser: bool = True):
    """Start the web UI server."""
    server = HTTPServer(("127.0.0.1", port), SessionAPIHandler)
    url = f"http://127.0.0.1:{port}"
    print(f"Claude Sessions Manager - Web UI")
    print(f"Listening on {url}")
    print(f"Press Ctrl+C to stop\n")
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
