"""Web UI for managing Claude Code sessions.

Uses Python's built-in http.server with embedded HTML/CSS/JS.
No external web framework dependencies.
"""

import json
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from .session_manager import (
    build_project_tree,
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
    --text-muted: #7079a8;
    --text-dim: #565f89;
    --accent: #7aa2f7;
    --green: #9ece6a;
    --red: #f7768e;
    --orange: #ff9e64;
    --yellow: #e0af68;
    --purple: #bb9af7;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
html, body { height: 100%; overflow: hidden; }
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    background: var(--bg);
    color: var(--text);
    display: flex;
    flex-direction: column;
    font-size: 13px;
}
.mono { font-family: 'SF Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace; }
.app-body { display: flex; flex: 1; overflow: hidden; }

/* ---------- Header ---------- */
header {
    background: var(--bg-surface);
    border-bottom: 1px solid var(--border);
    padding: 12px 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-shrink: 0;
}
header h1 { font-size: 16px; font-weight: 600; color: var(--accent); letter-spacing: 0.02em; }
.stats { display: flex; gap: 18px; font-size: 12.5px; color: var(--text-dim); align-items: baseline; }
.stats .stat-value { color: var(--text); font-weight: 600; }
.stats .stat-active .stat-value { color: var(--green); }
.stats .stat-size { color: var(--text-dim); }

/* ---------- Sidebar / folder tree ---------- */
#sidebar {
    width: 300px;
    min-width: 300px;
    background: var(--bg-surface);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.sidebar-head { padding: 12px 14px 8px; }
.sidebar-head h3 {
    font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
    color: var(--text-dim); margin-bottom: 8px;
}
#proj-filter {
    width: 100%; background: var(--bg); border: 1px solid var(--border); color: var(--text);
    padding: 6px 10px; border-radius: 6px; font-size: 12px; outline: none; font-family: inherit;
}
#proj-filter:focus { border-color: var(--accent); }
#tree { flex: 1; overflow-y: auto; padding: 4px 6px 16px; }
.tnode {
    display: flex; align-items: center; gap: 4px; height: 26px;
    border-radius: 6px; cursor: pointer; user-select: none; font-size: 12.5px;
    padding-right: 8px;
}
.tnode:hover { background: var(--bg-highlight); }
.tnode.sel { background: rgba(122,162,247,0.16); }
.tnode.sel .tname { color: var(--accent); font-weight: 600; }
.tnode .caret {
    width: 14px; flex-shrink: 0; text-align: center; color: var(--text-dim);
    font-size: 10px; cursor: pointer;
}
.tnode .tlabel { flex: 1; display: flex; align-items: center; gap: 6px; min-width: 0; }
.tnode .tname { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.tnode.is-group .tname { color: var(--text-muted); }
.tnode .tcount {
    margin-left: auto; flex-shrink: 0; font-size: 11px; color: var(--text-dim);
    background: rgba(255,255,255,0.05); padding: 1px 7px; border-radius: 10px;
}
.tnode.sel .tcount { background: rgba(122,162,247,0.22); color: var(--accent); }
.tnode.is-group > .tlabel > .tname { font-weight: 600; }
.tnode.is-leaf .tname { color: var(--text); font-weight: 400; }
.tnode.is-leaf.sel .tname { color: var(--accent); font-weight: 600; }
.tnode .thint { color: var(--text-dim); font-size: 11px; }
.tnode .troot { color: var(--text-dim); font-size: 9.5px; text-transform: uppercase; letter-spacing: 0.04em; border: 1px solid var(--border); border-radius: 3px; padding: 0 4px; margin-left: 2px; }
.tnode .twt { color: var(--yellow); }
.dot { display: inline-block; width: 7px; height: 7px; border-radius: 50%; background: var(--green); box-shadow: 0 0 5px var(--green); vertical-align: middle; }

/* ---------- Main ---------- */
.main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.controls {
    padding: 10px 18px; display: flex; gap: 10px; align-items: center;
    border-bottom: 1px solid var(--border); background: var(--bg-surface); flex-shrink: 0;
}
#filter {
    flex: 1; min-width: 120px; background: var(--bg); border: 1px solid var(--border);
    color: var(--text); padding: 8px 12px; border-radius: 6px; font-family: inherit;
    font-size: 13px; outline: none;
}
#filter:focus { border-color: var(--accent); }
#filter::placeholder { color: var(--text-dim); }
#result-count { font-size: 12px; color: var(--text-dim); white-space: nowrap; }
.sort-wrap { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--text-dim); }
#sort-select {
    background: var(--bg); border: 1px solid var(--border); color: var(--text);
    padding: 7px 8px; border-radius: 6px; font-family: inherit; font-size: 12.5px; cursor: pointer; outline: none;
}
.btn {
    padding: 7px 13px; border: 1px solid var(--border); background: var(--bg); color: var(--text);
    border-radius: 6px; cursor: pointer; font-family: inherit; font-size: 12.5px; transition: all 0.12s; white-space: nowrap;
}
.btn:hover { background: var(--bg-highlight); border-color: var(--accent); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn-danger { border-color: var(--red); color: var(--red); }
.btn-danger:hover { background: rgba(247, 118, 142, 0.15); }
.btn-sm { padding: 4px 9px; font-size: 12px; }
.btn-primary { background: var(--accent); color: var(--bg); border-color: var(--accent); font-weight: 600; }
.btn-primary:hover { background: #8fb0f9; }
#bulk-actions { display: none; gap: 10px; align-items: center; }
#bulk-actions.active { display: flex; }
#bulk-count { font-size: 12.5px; color: var(--accent); font-weight: 600; }

/* ---------- Table ---------- */
.table-wrap { flex: 1; overflow-y: auto; overflow-x: hidden; }
table { width: 100%; border-collapse: collapse; table-layout: fixed; }
thead th {
    position: sticky; top: 0; z-index: 10; background: var(--bg-surface);
    padding: 9px 12px; text-align: left; font-size: 11px; text-transform: uppercase;
    letter-spacing: 0.05em; color: var(--text-dim); border-bottom: 1px solid var(--border);
    white-space: nowrap; user-select: none;
}
th.sortable { cursor: pointer; }
th.sortable:hover { color: var(--accent); }
th.sorted { color: var(--accent); }
th .arrow { margin-left: 3px; }
td { padding: 9px 12px; border-bottom: 1px solid var(--border); vertical-align: middle; overflow: hidden; }
tbody tr { cursor: pointer; }
tbody tr:hover td { background: var(--bg-highlight); }
tr.is-active td.c-session { border-left: 2px solid var(--green); }

.c-check { width: 34px; text-align: center; }
.c-when { width: 90px; color: var(--text-dim); font-size: 12px; white-space: nowrap; }
.c-project { width: 168px; }
.c-msgs { width: 58px; text-align: right; color: var(--text-muted); font-variant-numeric: tabular-nums; }
.c-actions { width: 132px; text-align: right; white-space: nowrap; }

.s-title { font-size: 13.5px; color: var(--text); font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; display: flex; align-items: center; gap: 7px; }
.s-title .live { display: inline-flex; align-items: center; gap: 4px; color: var(--green); font-size: 10.5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; flex-shrink: 0; }
.s-title .name-tag { flex-shrink: 0; font-size: 10px; color: var(--purple); border: 1px solid rgba(187,154,247,0.4); border-radius: 4px; padding: 0 5px; text-transform: none; letter-spacing: 0; font-weight: 500; }
.s-title .recap-tag { flex-shrink: 0; font-size: 10px; color: var(--yellow); border: 1px solid rgba(224,175,104,0.45); border-radius: 4px; padding: 0 5px; font-weight: 500; }
.msg-block.recap-block { border-left: 3px solid var(--accent); max-height: 260px; }
.recap-callout { margin: 0 0 6px; padding: 11px 14px; background: rgba(122,162,247,0.09); border-left: 3px solid var(--accent); border-radius: 6px; font-size: 13px; line-height: 1.55; color: var(--text); }
.recap-callout .recap-ico { color: var(--accent); margin-right: 7px; font-weight: 700; }
.recap-callout .recap-lbl { color: var(--text-dim); text-transform: uppercase; font-size: 10px; letter-spacing: 0.06em; margin-right: 8px; }
.s-sub { font-size: 11.5px; color: var(--text-dim); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 2px; }
.c-project .proj-leaf { color: var(--accent); font-size: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.c-project .proj-branch { color: var(--orange); font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.c-project.same-as-prev .proj-leaf, .c-project.same-as-prev .proj-branch { opacity: 0; }

/* ---------- Modal ---------- */
.modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 1000; align-items: center; justify-content: center; }
.modal-overlay.active { display: flex; }
.modal {
    background: var(--bg-surface); border: 1px solid var(--border); border-radius: 10px;
    padding: 0; width: 620px; max-width: 92vw; max-height: 86vh; overflow: hidden;
    display: flex; flex-direction: column;
}
.modal-head { padding: 18px 22px 14px; border-bottom: 1px solid var(--border); }
.modal-head .m-title { font-size: 17px; font-weight: 600; color: var(--text); line-height: 1.3; }
.modal-head .m-meta { margin-top: 6px; font-size: 12.5px; color: var(--text-dim); display: flex; flex-wrap: wrap; gap: 10px; align-items: center; }
.modal-head .m-meta .chip { color: var(--accent); }
.modal-head .m-meta .chip-branch { color: var(--orange); }
.modal-head .m-meta .chip-live { color: var(--green); font-weight: 600; }
.modal-head .m-meta .chip-agent { color: var(--purple); }
.modal-body { padding: 16px 22px; overflow-y: auto; }
.modal-actions { padding: 14px 22px; border-top: 1px solid var(--border); display: flex; gap: 10px; justify-content: flex-end; }
.detail-grid { display: grid; grid-template-columns: max-content 1fr; gap: 5px 16px; font-size: 12.5px; align-items: baseline; }
.detail-grid .label { color: var(--text-dim); }
.detail-grid .val { color: var(--text); word-break: break-word; }
.section-title { font-size: 11px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--text-muted); margin: 16px 0 8px; }
.msg-block { padding: 10px 12px; background: var(--bg); border-radius: 6px; font-size: 12.5px; white-space: pre-wrap; max-height: 160px; overflow-y: auto; line-height: 1.5; }
.msg-block.mono { font-size: 12px; }
hr.divider { border: none; border-top: 1px solid var(--border); margin: 14px 0; }

.toast {
    position: fixed; bottom: 24px; right: 24px; background: var(--bg-surface); border: 1px solid var(--border);
    padding: 11px 18px; border-radius: 8px; font-size: 13px; z-index: 2000; opacity: 0;
    transition: opacity 0.2s, transform 0.2s; transform: translateY(8px); pointer-events: none;
}
.toast.show { opacity: 1; transform: translateY(0); }
.toast.success { border-color: var(--green); }
.toast.error { border-color: var(--red); color: var(--red); }
.empty, .loading { text-align: center; padding: 48px 20px; color: var(--text-dim); }
input[type="checkbox"] { accent-color: var(--accent); cursor: pointer; width: 15px; height: 15px; }
</style>
</head>
<body>
<header>
    <h1>&gt;_ Claude Sessions Manager</h1>
    <div class="stats" id="stats"></div>
</header>
<div class="app-body">
<div id="sidebar">
    <div class="sidebar-head">
        <h3>Projects</h3>
        <input type="text" id="proj-filter" placeholder="Jump to folder...">
    </div>
    <div id="tree"><div class="loading">Loading...</div></div>
</div>
<div class="main-content">
<div class="controls">
    <input type="text" id="filter" placeholder="Search title, summary, message text, project, branch...">
    <span id="result-count"></span>
    <div class="sort-wrap">
        <label for="sort-select">Sort</label>
        <select id="sort-select">
            <option value="recent">Most recent</option>
            <option value="title">Title (A–Z)</option>
            <option value="project">Project</option>
            <option value="messages">Messages</option>
            <option value="size">Disk size</option>
        </select>
    </div>
    <div id="bulk-actions">
        <span id="bulk-count">0 selected</span>
        <button class="btn btn-danger btn-sm" onclick="bulkDelete()">Delete selected</button>
    </div>
    <button class="btn" onclick="refresh()">Refresh</button>
</div>
<div class="table-wrap">
<table>
    <thead id="table-head"></thead>
    <tbody id="session-list">
        <tr><td class="loading">Loading sessions...</td></tr>
    </tbody>
</table>
</div>
</div><!-- /main-content -->
</div><!-- /app-body -->

<!-- Detail Modal -->
<div class="modal-overlay" id="detail-modal">
    <div class="modal">
        <div class="modal-head" id="detail-head"></div>
        <div class="modal-body" id="detail-content"></div>
        <div class="modal-actions">
            <button class="btn btn-primary" id="detail-resume">Copy resume command</button>
            <button class="btn" onclick="closeModal('detail-modal')">Close</button>
        </div>
    </div>
</div>

<!-- Delete Confirm Modal -->
<div class="modal-overlay" id="delete-modal">
    <div class="modal" style="width:480px">
        <div class="modal-head"><div class="m-title" style="color:var(--red)">Delete this session?</div></div>
        <div class="modal-body" id="delete-content"></div>
        <div class="modal-actions">
            <button class="btn" onclick="closeModal('delete-modal')">Cancel</button>
            <button class="btn btn-danger" id="confirm-delete-btn">Delete permanently</button>
        </div>
    </div>
</div>

<div class="toast" id="toast"></div>

<script>
let sessions = [];
let tree = [];
let sortKey = 'recent';
let sortReverse = true;
let selected = new Set();
let selectedPath = '__all__';
let selectedGroup = true; // true = area group (prefix match); false = leaf working dir (exact)
let expanded = null;      // Set of expanded area paths; null until first load
let projFilter = '';

async function fetchSessions() {
    const resp = await fetch('/api/sessions');
    const data = await resp.json();
    sessions = data.sessions;
    tree = data.tree || [];
    if (expanded === null) {
        // Default: expand the top-level folders so recent projects are visible.
        expanded = new Set(tree.map(n => n.path));
    }
    updateStats(data.stats);
    renderTree();
    renderTable();
}

function updateStats(stats) {
    document.getElementById('stats').innerHTML =
        `<span><span class="stat-value">${stats.total_sessions}</span> sessions</span>` +
        `<span><span class="stat-value">${stats.total_projects}</span> projects</span>` +
        `<span class="stat-active"><span class="stat-value">${stats.active_sessions}</span> active</span>` +
        `<span class="stat-size">${stats.total_size}</span>`;
}

/* ---------------- Sidebar folder tree ---------------- */
function areaHit(area, f) {
    return (area.name || '').toLowerCase().includes(f) || (area.path || '').toLowerCase().includes(f);
}
function leafHit(leaf, f) {
    return (leaf.name || '').toLowerCase().includes(f)
        || (leaf.hint || '').toLowerCase().includes(f)
        || (leaf.path || '').toLowerCase().includes(f);
}

function renderTree() {
    const container = document.getElementById('tree');
    const total = sessions.length;
    const allSel = selectedPath === '__all__' ? ' sel' : '';
    let html = `<div class="tnode${allSel}" data-path="__all__" data-group="1" style="padding-left:6px">
        <span class="caret"></span>
        <span class="tlabel"><span class="tname">All projects</span><span class="tcount">${total}</span></span>
    </div>`;

    for (const area of tree) {
        const hit = !projFilter || areaHit(area, projFilter);
        const leaves = area.children.filter(l => !projFilter || hit || leafHit(l, projFilter));
        if (projFilter && !hit && leaves.length === 0) continue;

        const isExp = expanded.has(area.path) || projFilter !== '';
        const sel = (selectedGroup && selectedPath === area.path) ? ' sel' : '';
        const dot = area.active > 0 ? ' <span class="dot" title="has a live session"></span>' : '';
        html += `<div class="tnode is-group${sel}" data-path="${escAttr(area.path)}" data-group="1" style="padding-left:6px">
            <span class="caret" data-toggle="${escAttr(area.path)}">${isExp ? '▾' : '▸'}</span>
            <span class="tlabel"><span class="tname">${escapeHtml(area.name)}${dot}</span><span class="tcount">${area.count}</span></span>
        </div>`;
        if (!isExp) continue;
        for (const leaf of leaves) {
            const lsel = (!selectedGroup && selectedPath === leaf.path) ? ' sel' : '';
            const ldot = leaf.active > 0 ? ' <span class="dot" title="has a live session"></span>' : '';
            const root = leaf.is_root ? ' <span class="troot">root</span>' : '';
            const wt = leaf.worktree ? ' <span class="twt" title="git worktree">⑂</span>' : '';
            const hint = leaf.hint ? ` <span class="thint">${escapeHtml(leaf.hint)}</span>` : '';
            html += `<div class="tnode is-leaf${lsel}" data-path="${escAttr(leaf.path)}" data-group="0" style="padding-left:28px">
                <span class="tlabel"><span class="tname">${escapeHtml(leaf.name)}${wt}${root}${hint}${ldot}</span><span class="tcount">${leaf.count}</span></span>
            </div>`;
        }
    }
    container.innerHTML = html;

    container.querySelectorAll('[data-toggle]').forEach(el => {
        el.addEventListener('click', e => {
            e.stopPropagation();
            const p = el.dataset.toggle;
            if (expanded.has(p)) expanded.delete(p); else expanded.add(p);
            renderTree();
        });
    });
    container.querySelectorAll('[data-path]').forEach(el => {
        el.addEventListener('click', () => {
            selectedPath = el.dataset.path;
            selectedGroup = el.dataset.group === '1';
            renderTree();
            renderTable();
        });
    });
}

/* ---------------- Table ---------------- */
function matchesSelected(s) {
    if (selectedPath === '__all__') return true;
    if (selectedGroup) return s.real_path === selectedPath || s.real_path.startsWith(selectedPath + '/');
    return s.real_path === selectedPath;   // leaf = exact working dir
}

function getFiltered() {
    const ft = document.getElementById('filter').value.toLowerCase().trim();
    let filtered = sessions.filter(matchesSelected);
    if (ft) {
        filtered = filtered.filter(s =>
            (s.display_title || '').toLowerCase().includes(ft) ||
            (s.subtitle || '').toLowerCase().includes(ft) ||
            (s.ai_title || '').toLowerCase().includes(ft) ||
            (s.custom_title || '').toLowerCase().includes(ft) ||
            (s.first_message || '').toLowerCase().includes(ft) ||
            (s.last_user_message || '').toLowerCase().includes(ft) ||
            (s.last_assistant_message || '').toLowerCase().includes(ft) ||
            (s.real_path_short || '').toLowerCase().includes(ft) ||
            (s.git_branch || '').toLowerCase().includes(ft) ||
            (s.session_id || '').toLowerCase().includes(ft)
        );
    }
    filtered = filtered.slice().sort((a, b) => {
        let va, vb;
        if (sortKey === 'recent') { va = a.last_activity || a.started_at || ''; vb = b.last_activity || b.started_at || ''; }
        else if (sortKey === 'title') { va = (a.display_title || '').toLowerCase(); vb = (b.display_title || '').toLowerCase(); }
        else if (sortKey === 'project') { va = a.real_path; vb = b.real_path; }
        else if (sortKey === 'messages') { va = a.total_messages; vb = b.total_messages; }
        else if (sortKey === 'size') { va = a.total_size; vb = b.total_size; }
        if (va < vb) return sortReverse ? 1 : -1;
        if (va > vb) return sortReverse ? -1 : 1;
        return 0;
    });
    return filtered;
}

function renderHead(showProject) {
    const arrow = key => sortKey === key ? `<span class="arrow">${sortReverse ? '▾' : '▴'}</span>` : '';
    const cls = key => 'sortable' + (sortKey === key ? ' sorted' : '');
    let h = `<tr>
        <th class="c-check"><input type="checkbox" id="select-all" onchange="toggleSelectAll(this)"></th>
        <th class="c-when ${cls('recent')}" data-sort="recent">When ${arrow('recent')}</th>
        <th class="${cls('title')}" data-sort="title">Session ${arrow('title')}</th>`;
    if (showProject) h += `<th class="c-project ${cls('project')}" data-sort="project">Project ${arrow('project')}</th>`;
    h += `<th class="c-msgs ${cls('messages')}" data-sort="messages">Msgs ${arrow('messages')}</th>
        <th class="c-actions">Actions</th></tr>`;
    const thead = document.getElementById('table-head');
    thead.innerHTML = h;
    thead.querySelectorAll('th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const key = th.dataset.sort;
            if (sortKey === key) sortReverse = !sortReverse;
            else { sortKey = key; sortReverse = (key === 'recent' || key === 'messages' || key === 'size'); }
            document.getElementById('sort-select').value = key;
            renderTable();
        });
    });
}

function renderTable() {
    const filtered = getFiltered();
    const distinctProjects = new Set(filtered.map(s => s.real_path));
    const showProject = distinctProjects.size > 1;
    renderHead(showProject);

    document.getElementById('result-count').textContent =
        `${filtered.length} of ${sessions.length}`;

    const tbody = document.getElementById('session-list');
    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td class="empty" colspan="6">No sessions match.</td></tr>`;
        updateBulkActions();
        return;
    }
    let prevPath = null;
    tbody.innerHTML = filtered.map(s => {
        const checked = selected.has(s.session_id) ? 'checked' : '';
        const live = s.is_active ? `<span class="live">● live</span>` : '';
        const recapTag = s.has_recap ? `<span class="recap-tag" title="has a recap">⟳ recap</span>` : '';
        const title = s.display_title;
        const nameTag = (s.custom_title && s.custom_title !== title) ? `<span class="name-tag" title="named session">${escapeHtml(s.custom_title)}</span>` : '';
        const sub = s.subtitle ? `<div class="s-sub" title="${escAttr(s.subtitle)}">${escapeHtml(clip(s.subtitle, 120))}</div>` : '';
        let projCell = '';
        if (showProject) {
            const same = s.real_path === prevPath ? ' same-as-prev' : '';
            projCell = `<td class="c-project${same}">
                <div class="proj-leaf" title="${escAttr(s.real_path_short)}">${escapeHtml(s.project_leaf)}</div>
                <div class="proj-branch">${escapeHtml(s.git_branch || '-')}</div>
            </td>`;
        }
        prevPath = s.real_path;
        return `<tr class="${s.is_active ? 'is-active' : ''}" onclick="showDetail('${s.session_id}')">
            <td class="c-check" onclick="event.stopPropagation()"><input type="checkbox" ${checked} ${s.is_active ? 'disabled title="Cannot delete active session"' : ''} onchange="toggleSelect('${s.session_id}', this)"></td>
            <td class="c-when" title="${escAttr(s.last_activity_str)}">${escapeHtml(s.when_str)}</td>
            <td class="c-session">
                <div class="s-title">${nameTag}<span style="overflow:hidden;text-overflow:ellipsis">${escapeHtml(title)}</span>${live}${recapTag}</div>
                ${sub}
            </td>
            ${projCell}
            <td class="c-msgs" title="${s.user_message_count} user / ${s.assistant_message_count} assistant">${s.total_messages}</td>
            <td class="c-actions" onclick="event.stopPropagation()">
                <button class="btn btn-sm" onclick="copyResume('${s.session_id}')" title="Copy cd + resume command">Resume</button>
                <button class="btn btn-sm btn-danger" onclick="confirmDelete('${s.session_id}')" ${s.is_active ? 'disabled' : ''}>Del</button>
            </td>
        </tr>`;
    }).join('');
    updateBulkActions();
}

/* ---------------- Helpers ---------------- */
function clip(s, n) { return s.length > n ? s.substring(0, n - 1) + '…' : s; }
function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function escAttr(s) { return escapeHtml(s).replace(/'/g, '&#39;'); }
function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1048576) return (bytes/1024).toFixed(1) + ' KB';
    if (bytes < 1073741824) return (bytes/1048576).toFixed(1) + ' MB';
    return (bytes/1073741824).toFixed(1) + ' GB';
}

function toggleSelect(id, cb) {
    if (cb.checked) selected.add(id); else selected.delete(id);
    updateBulkActions();
}
function toggleSelectAll(cb) {
    const filtered = getFiltered();
    if (cb.checked) filtered.forEach(s => { if (!s.is_active) selected.add(s.session_id); });
    else selected.clear();
    renderTable();
}
function updateBulkActions() {
    const ba = document.getElementById('bulk-actions');
    if (selected.size > 0) { ba.classList.add('active'); document.getElementById('bulk-count').textContent = `${selected.size} selected`; }
    else ba.classList.remove('active');
}

function clipCopy(text, label) {
    navigator.clipboard.writeText(text).then(() => showToast('Copied: ' + label, 'success')).catch(() => {
        const ta = document.createElement('textarea');
        ta.value = text; document.body.appendChild(ta); ta.select();
        document.execCommand('copy'); document.body.removeChild(ta);
        showToast('Copied: ' + label, 'success');
    });
}
function resumeCommand(s) {
    return s && s.cwd ? `cd ${s.cwd} && claude --resume ${s.session_id}` : `claude --resume ${s.session_id}`;
}
function copyResume(id) {
    const s = sessions.find(x => x.session_id === id);
    clipCopy(resumeCommand(s), 'resume command');
}

/* ---------------- Detail modal ---------------- */
function showDetail(id) {
    const s = sessions.find(x => x.session_id === id);
    if (!s) return;
    const meta = [];
    if (s.is_active) meta.push(`<span class="chip-live">● live (PID ${s.active_pid})</span>`);
    meta.push(`<span class="chip">${escapeHtml(s.project_leaf)}</span>`);
    if (s.git_branch) meta.push(`<span class="chip-branch">${escapeHtml(s.git_branch)}</span>`);
    meta.push(`${escapeHtml(s.when_str)} · ${escapeHtml(s.started_str)}`);
    if (s.agent_name) meta.push(`<span class="chip-agent">agent: ${escapeHtml(s.agent_name)}</span>`);

    document.getElementById('detail-head').innerHTML =
        `<div class="m-title">${escapeHtml(s.display_title)}</div>
         <div class="m-meta">${meta.join('')}</div>`;

    const row = (label, val) => `<div class="label">${label}</div><div class="val">${val}</div>`;
    let grid = '';
    if (s.custom_title && s.custom_title !== s.display_title) grid += row('Name', escapeHtml(s.custom_title));
    if (s.ai_title && s.ai_title !== s.display_title) grid += row('Summary', escapeHtml(s.ai_title));
    grid += row('Session ID', `<span class="mono" style="font-size:11.5px">${escapeHtml(s.session_id)}</span>`);
    grid += row('Working dir', `<span class="mono" style="font-size:11.5px">${escapeHtml(s.cwd || s.real_path)}</span>`);
    grid += row('Version', escapeHtml(s.version || 'N/A'));
    grid += row('Started', escapeHtml(s.started_str));
    grid += row('Last active', escapeHtml(s.last_activity_str) + ` <span style="color:var(--text-dim)">(${escapeHtml(s.when_str)})</span>`);
    grid += row('Active span', escapeHtml(s.duration_str) + ` <span style="color:var(--text-dim)">first → last message</span>`);
    grid += row('Messages', `${s.user_message_count} user / ${s.assistant_message_count} assistant`);
    grid += row('Disk size', `${escapeHtml(s.size_str)}`);

    let usage = row('Model(s)', escapeHtml(s.models_str || 'N/A'));
    usage += row('Total tokens', escapeHtml(s.tokens_total_str));
    if (s.total_input_tokens) usage += row('Input', escapeHtml(s.tokens_in_str));
    if (s.total_output_tokens) usage += row('Output', escapeHtml(s.tokens_out_str));
    if (s.total_cache_read_tokens) usage += row('Cache read', `${escapeHtml(s.tokens_cache_read_str)} (${escapeHtml(s.cache_hit_ratio_str)} hit ratio)`);
    if (s.total_cache_creation_tokens) usage += row('Cache write', escapeHtml(s.tokens_cache_creation_str));
    if (s.service_tier) usage += row('Service tier', escapeHtml(s.service_tier));
    if (s.web_search_count) usage += row('Web search', s.web_search_count);
    if (s.web_fetch_count) usage += row('Web fetch', s.web_fetch_count);

    const prs = (s.pr_links && s.pr_links.length)
        ? `<div class="section-title">Pull requests</div>` + s.pr_links.map(l =>
            `<div><a href="${escAttr(l)}" target="_blank" style="color:var(--accent)">${escapeHtml(l)}</a></div>`).join('')
        : '';

    const block = (title, text) => text
        ? `<div class="section-title">${title}</div><div class="msg-block mono">${escapeHtml(text)}</div>` : '';

    const recap = s.recap
        ? `<div class="recap-callout"><span class="recap-ico">⟳</span><span class="recap-lbl">recap</span>${escapeHtml(s.recap)}</div>` : '';
    const compact = s.compact_summary
        ? `<div class="section-title">Continued-conversation summary</div>
           <div class="msg-block recap-block">${escapeHtml(s.compact_summary)}</div>` : '';

    document.getElementById('detail-content').innerHTML =
        `${recap}
         <div class="detail-grid">${grid}</div>
         <div class="section-title">Usage / context</div>
         <div class="detail-grid">${usage}</div>
         ${prs}
         ${compact}
         ${block('First message', s.first_message)}
         ${(s.last_user_message && s.last_user_message !== s.first_message) ? block('Last user message', s.last_user_message) : ''}
         ${block('Last assistant response', s.last_assistant_message)}`;

    document.getElementById('detail-resume').onclick = () => copyResume(s.session_id);
    openModal('detail-modal');
}

/* ---------------- Delete ---------------- */
function confirmDelete(id) {
    const s = sessions.find(x => x.session_id === id);
    if (!s || s.is_active) return;
    document.getElementById('delete-content').innerHTML = `
        <div class="detail-grid">
            <div class="label">Session</div><div class="val">${escapeHtml(s.display_title)}</div>
            <div class="label">Project</div><div class="val">${escapeHtml(s.real_path_short)}</div>
            <div class="label">When</div><div class="val">${escapeHtml(s.when_str)} (${escapeHtml(s.started_str)})</div>
            <div class="label">Disk size</div><div class="val">${escapeHtml(s.size_str)}</div>
        </div>
        <p style="color:var(--red);margin-top:14px">This permanently deletes the transcript, tool results, and file history. Cannot be undone.</p>`;
    document.getElementById('confirm-delete-btn').onclick = () => doDelete(id);
    openModal('delete-modal');
}
async function doDelete(id) {
    closeModal('delete-modal');
    try {
        const resp = await fetch('/api/sessions/' + id, { method: 'DELETE' });
        const data = await resp.json();
        if (data.ok) { showToast('Session deleted', 'success'); selected.delete(id); await fetchSessions(); }
        else showToast('Error: ' + data.error, 'error');
    } catch (e) { showToast('Error: ' + e.message, 'error'); }
}
async function bulkDelete() {
    if (selected.size === 0) return;
    if (!confirm(`Delete ${selected.size} selected session(s)? This cannot be undone.`)) return;
    let deleted = 0, errors = 0;
    for (const id of [...selected]) {
        try {
            const resp = await fetch('/api/sessions/' + id, { method: 'DELETE' });
            const data = await resp.json();
            if (data.ok) { deleted++; selected.delete(id); } else errors++;
        } catch { errors++; }
    }
    showToast(`Deleted ${deleted} session(s)${errors ? ', ' + errors + ' error(s)' : ''}`, errors ? 'error' : 'success');
    await fetchSessions();
}

/* ---------------- Misc ---------------- */
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function showToast(msg, type) {
    const t = document.getElementById('toast');
    t.textContent = msg; t.className = 'toast show ' + (type || '');
    clearTimeout(t._t); t._t = setTimeout(() => t.className = 'toast', 2600);
}
function refresh() {
    document.getElementById('session-list').innerHTML = '<tr><td class="loading">Loading...</td></tr>';
    fetchSessions();
}

document.getElementById('filter').addEventListener('input', () => renderTable());
document.getElementById('proj-filter').addEventListener('input', e => { projFilter = e.target.value.toLowerCase().trim(); renderTree(); });
document.getElementById('sort-select').addEventListener('change', e => {
    sortKey = e.target.value;
    sortReverse = (sortKey === 'recent' || sortKey === 'messages' || sortKey === 'size');
    renderTable();
});
document.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT') {
        if (e.key === 'Escape') e.target.blur();
        return;
    }
    if (e.key === '/') { e.preventDefault(); document.getElementById('filter').focus(); }
    if (e.key === 'Escape') { closeModal('detail-modal'); closeModal('delete-modal'); }
});
document.querySelectorAll('.modal-overlay').forEach(ov => {
    ov.addEventListener('click', e => { if (e.target === ov) ov.classList.remove('active'); });
});

fetchSessions();
</script>
</body>
</html>"""


def _session_to_dict(s) -> dict:
    return {
        "session_id": s.session_id,
        "project_dir": s.project_dir,
        "project_path": s.project_path,
        "real_path": s.real_path,
        "real_path_short": s.real_path_short,
        "project_leaf": s.project_leaf,
        "first_message": s.first_message,
        "started_at": s.started_at.isoformat() if s.started_at else None,
        "last_activity": s.last_activity.isoformat() if s.last_activity else None,
        "started_str": s.started_str,
        "last_activity_str": s.last_activity_str,
        "when_str": s.when_str,
        "duration_str": s.duration_str,
        "topic": s.topic,
        "ai_title": s.ai_title,
        "custom_title": s.custom_title,
        "agent_name": s.agent_name,
        "recap": s.recap,
        "has_recap": s.has_recap,
        "compact_summary": s.compact_summary,
        "has_compact_summary": s.has_compact_summary,
        "display_title": s.display_title,
        "subtitle": s.subtitle,
        "has_title": s.has_title,
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
        "total_input_tokens": s.total_input_tokens,
        "total_output_tokens": s.total_output_tokens,
        "total_cache_creation_tokens": s.total_cache_creation_tokens,
        "total_cache_read_tokens": s.total_cache_read_tokens,
        "total_tokens": s.total_tokens,
        "models_used": s.models_used,
        "models_str": s.models_str,
        "web_search_count": s.web_search_count,
        "web_fetch_count": s.web_fetch_count,
        "service_tier": s.service_tier,
        "tokens_total_str": s.tokens_total_str,
        "tokens_in_str": s.tokens_in_str,
        "tokens_out_str": s.tokens_out_str,
        "tokens_cache_read_str": s.tokens_cache_read_str,
        "tokens_cache_creation_str": s.tokens_cache_creation_str,
        "cache_hit_ratio_str": s.cache_hit_ratio_str,
    }


class SessionAPIHandler(BaseHTTPRequestHandler):
    """HTTP request handler for the session manager API and web UI."""

    sessions_cache: list | None = None
    root: str | None = None  # optional scope filter (set by run_web)

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
        SessionAPIHandler.sessions_cache = discover_sessions(SessionAPIHandler.root)

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
                "tree": build_project_tree(sessions),
            })
            return

        self.send_error(404, "Not found")

    def do_DELETE(self):
        parsed = urlparse(self.path)

        # /api/sessions/<session_id>
        if parsed.path.startswith("/api/sessions/"):
            session_id = parsed.path.split("/")[-1]
            sessions = SessionAPIHandler.sessions_cache or discover_sessions(SessionAPIHandler.root)
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


def run_web(port: int = 8420, open_browser: bool = True, root: str | None = None):
    """Start the web UI server.

    Threaded so multiple browser tabs (or keep-alive connections) don't block
    each other on the single-threaded default server. ``root`` optionally scopes
    discovery to sessions under a directory.
    """
    SessionAPIHandler.root = root
    server = ThreadingHTTPServer(("127.0.0.1", port), SessionAPIHandler)
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
