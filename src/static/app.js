/* =============================================================================
   Challenge Hunter AI v2.0 — Frontend logic
   Vanilla JS, no build step. Talks to /api/*.
   ============================================================================= */

const API = async (path, opts = {}) => {
  try {
    const r = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts
    });
    let data = null;
    try {
      data = await r.json();
    } catch (_) {
      data = { error: 'invalid JSON response' };
    }
    return { ok: r.ok, status: r.status, data };
  } catch (err) {
    return { ok: false, status: 0, data: { error: err.message } };
  }
};

const state = {
  view: 'dashboard',
  status: 'all',
  tag: null,
  search: '',
  sort: 'score',
  opportunities: [],
  stats: {},
  loading: false
};

// -----------------------------------------------------------------------------
// Toast system
// -----------------------------------------------------------------------------
const toast = (msg, type = 'info', ms = 4000) => {
  const stack = document.getElementById('toast-stack') || (() => {
    const s = document.createElement('div');
    s.id = 'toast-stack';
    s.className = 'toast-stack';
    document.body.appendChild(s);
    return s;
  })();
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.textContent = msg;
  t.onclick = () => t.remove();
  stack.appendChild(t);
  setTimeout(() => t.remove(), ms);
};

// -----------------------------------------------------------------------------
// Format helpers
// -----------------------------------------------------------------------------
const fmtMoney = (n) => '$' + Number(n || 0).toLocaleString();
const fmtNum = (n) => Number(n || 0).toLocaleString();
const fmtDays = (d) => {
  if (d == null) return '—';
  if (d <= 0) return 'EXPIRED';
  if (d === 1) return '1 day';
  return `${d} days`;
};
const escapeHtml = (s) => String(s || '').replace(/[&<>"']/g,
  c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

const scoreClass = (s) => s >= 70 ? 'score-high' : s >= 50 ? 'score-medium' : 'score-low';
const deadlineClass = (d) => d <= 3 ? 'urgent' : d <= 7 ? 'warning' : '';
const aiPolicyClass = (p) => ({
  'allowed': 'tag ai',
  'restricted': 'tag',
  'banned': 'tag',
  'unclear': 'tag'
}[p] || 'tag');

// -----------------------------------------------------------------------------
// Rendering
// -----------------------------------------------------------------------------
function renderCard(opp) {
  const tags = (opp.tags || '').split(',').filter(Boolean).slice(0, 5)
    .map(t => `<span class="tag">#${escapeHtml(t.trim())}</span>`).join('');
  const score = opp.opportunity_score || 0;
  const winProb = opp.win_probability || 0;
  const scoreColor = score >= 70 ? 'var(--accent-green)'
    : score >= 50 ? 'var(--accent-yellow)' : 'var(--accent-red)';
  const scoreCircum = 2 * Math.PI * 24;
  const scoreOffset = scoreCircum * (1 - score / 100);
  const winCircum = 2 * Math.PI * 24;
  const winOffset = winCircum * (1 - winProb / 100);
  const oppId = opp.id || 0;
  const oppName = escapeHtml(opp.name || 'Untitled');
  const oppUrl = escapeHtml(opp.url || '#');
  const oppSource = escapeHtml(opp.source || 'unknown');
  const oppStatus = escapeHtml(opp.status || 'pending');
  const oppPolicy = escapeHtml(opp.ai_policy || 'unclear');
  const oppDiff = escapeHtml(opp.difficulty || 'medium');
  const oppPrize = Number(opp.prize_usd || 0);
  const oppEv = Number(opp.expected_value || 0);
  const oppDays = Number(opp.days_remaining || 0);
  const oppDeadline = escapeHtml(opp.deadline || '');
  const oppRules = escapeHtml(opp.rules_summary || '').slice(0, 160);

  return `
    <div class="opp-card ${scoreClass(score)}" data-id="${oppId}" onclick="openAnalysis(${oppId})" style="cursor:pointer;">
      <div class="header">
        <span class="source-badge">${oppSource}</span>
        <span class="status-dot-inline">
          <span class="status-dot ${opp.status === 'pending' ? 'idle' : ''}"></span>
          ${oppStatus}
        </span>
      </div>
      <h3 class="name">${oppName}</h3>
      <div class="prize-block">
        <span class="amount">${fmtMoney(oppPrize)}</span>
        <span class="ev">EV ${fmtMoney(oppEv)}</span>
      </div>
      <div class="deadline ${deadlineClass(oppDays)}">
        <span>⏱</span>
        <span>${fmtDays(oppDays)} remaining</span>
        <span class="countdown">${oppDeadline}</span>
      </div>
      <div class="score-row">
        <div class="gauge" title="Opportunity score">
          <svg width="64" height="64" viewBox="0 0 64 64">
            <circle class="gauge-bg" cx="32" cy="32" r="24" fill="none" stroke-width="5"/>
            <circle class="gauge-fg" cx="32" cy="32" r="24" fill="none"
              stroke="${scoreColor}" stroke-width="5"
              stroke-dasharray="${scoreCircum}"
              stroke-dashoffset="${scoreOffset}"
              stroke-linecap="round"/>
          </svg>
          <div class="label">${score}</div>
          <div class="small-label">score</div>
        </div>
        <div class="gauge" title="Win probability">
          <svg width="64" height="64" viewBox="0 0 64 64">
            <circle class="gauge-bg" cx="32" cy="32" r="24" fill="none" stroke-width="5"/>
            <circle class="gauge-fg" cx="32" cy="32" r="24" fill="none"
              stroke="var(--accent-blue)" stroke-width="5"
              stroke-dasharray="${winCircum}"
              stroke-dashoffset="${winOffset}"
              stroke-linecap="round"/>
          </svg>
          <div class="label">${winProb}%</div>
          <div class="small-label">win</div>
        </div>
        <div style="flex:1; text-align:right; font-size:11px; color:var(--text-muted);">
          <div>AI: <strong>${oppPolicy}</strong></div>
          <div style="margin-top:4px;">${oppDiff}</div>
        </div>
      </div>
      <div class="tags">${tags}<span class="${aiPolicyClass(opp.ai_policy)}">AI ${oppPolicy}</span></div>
      <div class="summary">${oppRules}</div>
      <div class="actions" onclick="event.stopPropagation();">
        <button class="btn btn-ghost" onclick="openAnalysis(${oppId})">🔍 Analyze</button>
        <button class="btn btn-success" onclick="approve(${oppId})">✅ Approve</button>
        <button class="btn btn-danger btn-icon" onclick="reject(${oppId})" title="Reject">❌</button>
        <button class="btn btn-ghost btn-icon" onclick="ignore(${oppId})" title="Ignore">🔕</button>
      </div>
    </div>
  `;
}

function renderListRow(opp) {
  return `
    <tr data-id="${opp.id}" onclick="openAnalysis(${opp.id})">
      <td>${escapeHtml(opp.name)}</td>
      <td class="mono">${fmtMoney(opp.prize_usd)}</td>
      <td>${fmtDays(opp.days_remaining)}</td>
      <td class="mono">${opp.opportunity_score || 0}</td>
      <td class="mono">${opp.win_probability || 0}%</td>
      <td>${escapeHtml(opp.ai_policy || 'unclear')}</td>
      <td>${escapeHtml(opp.source || '')}</td>
    </tr>
  `;
}

function renderStats(s) {
  const row = document.getElementById('stat-row');
  if (!row) return;
  row.innerHTML = `
    <div class="stat-card blue">
      <div class="label">Total Active</div>
      <div class="value">${fmtNum(s.total_active)}</div>
      <div class="trend">all opportunities</div>
    </div>
    <div class="stat-card red">
      <div class="label">High Priority</div>
      <div class="value">${fmtNum(s.high_priority)}</div>
      <div class="trend">score ≥ 70</div>
    </div>
    <div class="stat-card green">
      <div class="label">Avg Win Prob</div>
      <div class="value">${s.avg_win_probability || 0}%</div>
      <div class="trend">${fmtNum(s.approved)} approved</div>
    </div>
    <div class="stat-card yellow">
      <div class="label">Prize Pool</div>
      <div class="value">${fmtMoney(s.total_prize_pool)}</div>
      <div class="trend">${fmtNum(s.building)} building</div>
    </div>
    <div class="stat-card purple">
      <div class="label">Expected Value</div>
      <div class="value">${fmtMoney(s.expected_value_total)}</div>
      <div class="trend">${fmtNum(s.submitted)} submitted</div>
    </div>
  `;
}

// -----------------------------------------------------------------------------
// Loaders
// -----------------------------------------------------------------------------
async function loadStats() {
  const r = await API('/api/stats');
  if (r.ok) {
    state.stats = r.data;
    renderStats(r.data);
  }
}

async function loadOpportunities() {
  state.loading = true;
  showSkeleton();
  const params = new URLSearchParams();
  // Map special UI statuses to API params
  if (state.status === 'all' || !state.status) {
    // no filter
  } else if (state.status === 'high') {
    params.set('min_score', '70');
  } else if (state.status === 'building') {
    // Building shows in_progress OR approved (since build starts after approve)
    // The API doesn't support OR, so we just query approved
    params.set('status', 'approved');
  } else if (state.status === 'submitted' || state.status === 'complete') {
    // No opportunities actually submitted yet, so we'll show approved
    params.set('status', 'approved');
  } else {
    params.set('status', state.status);
  }
  if (state.tag) params.set('tag', state.tag);
  if (state.search) params.set('search', state.search);
  if (state.sort) params.set('sort_by', state.sort);
  const r = await API('/api/opportunities?' + params.toString());
  state.loading = false;
  if (!r.ok) {
    toast('Failed to load opportunities', 'error');
    return;
  }
  state.opportunities = r.data.items;
  renderOpportunities();
}

function renderOpportunities() {
  const grid = document.getElementById('card-grid');
  const tbody = document.querySelector('#list-table tbody');
  if (grid) grid.innerHTML = state.opportunities.map(renderCard).join('');
  if (tbody) tbody.innerHTML = state.opportunities.map(renderListRow).join('');
  const countEl = document.getElementById('result-count');
  if (countEl) {
    countEl.textContent = `${state.opportunities.length} ${state.opportunities.length === 1 ? 'opportunity' : 'opportunities'}`;
  }
}

function showSkeleton() {
  const grid = document.getElementById('card-grid');
  if (!grid) return;
  grid.innerHTML = Array.from({ length: 6 }, () =>
    `<div class="opp-card">
      <div class="skeleton" style="height:14px;width:60%;"></div>
      <div class="skeleton" style="height:24px;width:80%;"></div>
      <div class="skeleton" style="height:40px;width:50%;"></div>
      <div class="skeleton" style="height:60px;width:100%;"></div>
    </div>`
  ).join('');
}

// -----------------------------------------------------------------------------
// Actions
// -----------------------------------------------------------------------------
async function approve(id) {
  const card = document.querySelector(`.opp-card[data-id="${id}"]`);
  if (card) card.style.opacity = '0.5';
  const r = await API(`/api/opportunities/${id}/approve`, { method: 'POST' });
  if (r.ok) {
    toast(`Build started for #${id}`, 'success');
    loadOpportunities();
    loadStats();
  } else {
    toast('Approve failed: ' + (r.data?.error || r.status), 'error');
    if (card) card.style.opacity = '';
  }
}

async function reject(id) {
  const r = await API(`/api/opportunities/${id}/reject`, { method: 'POST' });
  if (r.ok) { toast(`#${id} rejected`, 'warning'); loadOpportunities(); loadStats(); }
  else toast('Reject failed', 'error');
}

async function ignore(id) {
  const r = await API(`/api/opportunities/${id}/ignore`, { method: 'POST' });
  if (r.ok) { toast(`#${id} ignored`, 'info'); loadOpportunities(); loadStats(); }
  else toast('Ignore failed', 'error');
}

async function triggerScan() {
  toast('Scan triggered', 'info');
  const r = await API('/api/scan', { method: 'POST' });
  if (r.ok) {
    toast(`Scan started (${r.data.scan_id})`, 'success');
    setTimeout(() => { loadOpportunities(); loadStats(); }, 15000);
  } else toast('Scan failed', 'error');
}

// -----------------------------------------------------------------------------
// Analysis modal
// -----------------------------------------------------------------------------
async function openAnalysis(id) {
  let r;
  try {
    r = await API(`/api/opportunities/${id}`);
  } catch (err) {
    toast(`Failed to load: ${err.message}`, 'error');
    console.error('openAnalysis fetch error:', err);
    return;
  }
  if (!r.ok) {
    toast(`Failed to load opportunity #${id}: ${r.status}`, 'error');
    console.error('openAnalysis API error:', r);
    return;
  }
  const opp = r.data;
  if (!opp || !opp.id) {
    toast('Opportunity data is empty', 'error');
    return;
  }
  const a = opp.analysis_json || {};
  const rp = a.recommended_project || {};

  const modal = document.getElementById('modal');
  if (!modal) {
    toast('Modal element not found in DOM', 'error');
    return;
  }
  let sidebarHTML, bodyHTML;
  try {
    sidebarHTML = `
    <h2 style="margin:0 0 1rem; font-size:18px;">${escapeHtml(opp.name)}</h2>
    <div class="prize-block"><span class="amount">${fmtMoney(opp.prize_usd)}</span><span class="ev">EV ${fmtMoney(opp.expected_value)}</span></div>
    <div class="deadline ${deadlineClass(opp.days_remaining)}" style="margin:1rem 0;">
      <span>⏱</span><span>${fmtDays(opp.days_remaining)} remaining</span>
    </div>
    <div style="margin:1rem 0; display:flex; gap:1rem;">
      <div class="gauge">
        <svg width="80" height="80" viewBox="0 0 80 80">
          <circle class="gauge-bg" cx="40" cy="40" r="32" fill="none" stroke-width="6"/>
          <circle class="gauge-fg" cx="40" cy="40" r="32" fill="none"
            stroke="var(--accent-green)" stroke-width="6"
            stroke-dasharray="${2 * Math.PI * 32}"
            stroke-dashoffset="${2 * Math.PI * 32 * (1 - (opp.opportunity_score || 0) / 100)}"
            stroke-linecap="round"/>
        </svg>
        <div class="label">${opp.opportunity_score || 0}</div>
        <div class="small-label">score</div>
      </div>
      <div class="gauge">
        <svg width="80" height="80" viewBox="0 0 80 80">
          <circle class="gauge-bg" cx="40" cy="40" r="32" fill="none" stroke-width="6"/>
          <circle class="gauge-fg" cx="40" cy="40" r="32" fill="none"
            stroke="var(--accent-blue)" stroke-width="6"
            stroke-dasharray="${2 * Math.PI * 32}"
            stroke-dashoffset="${2 * Math.PI * 32 * (1 - (opp.win_probability || 0) / 100)}"
            stroke-linecap="round"/>
        </svg>
        <div class="label">${opp.win_probability || 0}%</div>
        <div class="small-label">win</div>
      </div>
    </div>
    <div style="font-size:12px; color:var(--text-muted); margin-top:0.5rem;">
      AI Policy: <strong>${escapeHtml(opp.ai_policy || 'unclear')}</strong><br>
      Difficulty: <strong>${escapeHtml(opp.difficulty || 'medium')}</strong><br>
      Source: <strong>${escapeHtml(opp.source || '')}</strong>
    </div>
    <a href="${escapeHtml(opp.url)}" target="_blank" class="btn btn-ghost" style="margin-top:1rem; width:100%; justify-content:center;">
      🔗 Open source
    </a>
    <div style="display:flex; gap:0.5rem; margin-top:1rem;">
      <button class="btn btn-success" style="flex:1;" onclick="approve(${opp.id}); document.getElementById('modal').classList.remove('show');">✅ Approve</button>
      <button class="btn btn-danger" onclick="reject(${opp.id}); document.getElementById('modal').classList.remove('show');">❌</button>
      <button class="btn btn-ghost" onclick="ignore(${opp.id}); document.getElementById('modal').classList.remove('show');">🔕</button>
    </div>
  `;

  const tech = rp.tech_stack || {};
  const techAll = [...(tech.frontend || []), ...(tech.backend || []),
    ...(tech.database || []), ...(tech.ai || []), ...(tech.deployment || [])];

  document.getElementById('modal-body');  // keep ref so older browsers don't strip

  bodyHTML = `
    <div class="section callout">
      <h3>Summary</h3>
      <p>${escapeHtml(a.summary || 'No analysis yet.')}</p>
    </div>
    <div class="section green">
      <h3>Why This Is Good</h3>
      <p>${escapeHtml(a.why_this_is_good || '')}</p>
    </div>
    <div class="section">
      <h3>Requirements</h3>
      <ul>${(a.requirements || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
    </div>
    <div class="section yellow">
      <h3>Risks</h3>
      <ul>${(a.risks || []).map(r => `<li>${escapeHtml(r)}</li>`).join('')}</ul>
    </div>
    <div class="recommended-project">
      <h2 style="margin:0 0 0.25rem;">🚀 ${escapeHtml(rp.name || 'Recommended Project')}</h2>
      <div style="color:var(--text-secondary); margin-bottom:1rem; font-style:italic;">${escapeHtml(rp.tagline || '')}</div>
      <p>${escapeHtml(rp.concept || '')}</p>
      <p><strong>Problem:</strong> ${escapeHtml(rp.problem_solved || '')}</p>
      <h3>Tech Stack</h3>
      <div class="tech-pills">${techAll.map(t => `<span class="tech-pill">${escapeHtml(t)}</span>`).join('')}</div>
      <h3 style="margin-top:1rem;">Key Features</h3>
      <ul>${(rp.key_features || []).map(f => `<li>${escapeHtml(f)}</li>`).join('')}</ul>
      <h3 style="margin-top:1rem;">Demo Approach</h3>
      <p>${escapeHtml(rp.demo_approach || '')}</p>
      <div class="section purple" style="margin-top:1rem;">
        <h3>Wow Factor</h3>
        <p>${escapeHtml(rp.wow_factor || '')}</p>
      </div>
      <div style="margin-top:1rem; font-size:12px; color:var(--text-muted);">
        Estimated build: <strong>${rp.estimated_build_days || '?'} days</strong>
      </div>
    </div>
    <div class="section purple">
      <h3>Submission Strategy</h3>
      <p>${escapeHtml(a.submission_strategy || '')}</p>
    </div>
    <div class="section">
      <h3>Judge Appeal</h3>
      <p>${escapeHtml(a.judge_appeal || '')}</p>
    </div>
    <div class="section">
      <h3>Alternatives</h3>
      ${(a.alternative_projects || []).map(p =>
        `<div style="margin:0.5rem 0;"><strong>${escapeHtml(p.name)}</strong> — ${escapeHtml(p.concept)} <span style="color:var(--text-muted);">(${p.build_days}d)</span></div>`
      ).join('')}
    </div>
    <div class="section ${a.recommended_action === 'approve' ? 'green' : 'red'}">
      <h3>Recommended Action: ${escapeHtml((a.recommended_action || 'monitor').toUpperCase())}</h3>
      <p>${escapeHtml(a.action_reasoning || '')}</p>
    </div>
  `;
    document.getElementById('modal-sidebar').innerHTML = sidebarHTML;
    document.getElementById('modal-body').innerHTML = bodyHTML;
    modal.classList.add('show');
  } catch (err) {
    console.error('Modal render failed:', err);
    toast(`Failed to render analysis: ${err.message}`, 'error');
  }
}

function closeModal() {
  document.getElementById('modal')?.classList.remove('show');
}

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') closeModal();
});

// -----------------------------------------------------------------------------
// Nav & filters
// -----------------------------------------------------------------------------
function setView(v) {
  state.view = v;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.view === v);
  });
  // Show/hide the corresponding view container
  const views = {
    dashboard: 'dashboard-view',
    high: 'dashboard-view',
    approved: 'dashboard-view',
    building: 'dashboard-view',
    submitted: 'dashboard-view',
    analytics: 'analytics-view',
    settings: 'settings-view',
  };
  const target = views[v] || 'dashboard-view';
  ['dashboard-view', 'analytics-view', 'settings-view'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = (id === target) ? '' : 'none';
  });
  // Page title
  document.getElementById('page-title').textContent =
    ({ dashboard: 'Dashboard', high: 'High Priority', approved: 'Approved',
       building: 'Building', submitted: 'Submitted', analytics: 'Analytics',
       settings: 'Settings' }[v] || 'Dashboard');
  // Apply filters for status-based views
  if (v === 'dashboard') setStatus('all');
  else if (v === 'high') setStatus('high');
  else if (v === 'approved') setStatus('approved');
  else if (v === 'building') setStatus('building');
  else if (v === 'submitted') setStatus('submitted');
  // Lazy-load special pages
  if (v === 'analytics') renderAnalytics();
  if (v === 'settings') renderSettings();
}

function setStatus(s) {
  state.status = s;
  document.querySelectorAll('[data-status-pill]').forEach(el => {
    el.classList.toggle('active', el.dataset.statusPill === s);
  });
  loadOpportunities();
}
function setTag(t) {
  state.tag = state.tag === t ? null : t;
  document.querySelectorAll('[data-tag]').forEach(el => {
    el.classList.toggle('active', state.tag && el.dataset.tag === state.tag);
  });
  loadOpportunities();
}

function setSort(s) {
  state.sort = s;
  loadOpportunities();
}

function setSearch(q) {
  state.search = q;
  clearTimeout(window._searchTimer);
  window._searchTimer = setTimeout(loadOpportunities, 250);
}

function setLayout(mode) {
  const grid = document.getElementById('card-grid');
  const list = document.getElementById('list-view');
  if (mode === 'grid') {
    if (grid) grid.style.display = 'grid';
    if (list) list.classList.remove('active');
  } else {
    if (grid) grid.style.display = 'none';
    if (list) list.classList.add('active');
  }
  // Update active state on layout pills
  document.querySelectorAll('[data-layout]').forEach(el => {
    el.classList.toggle('active', el.dataset.layout === mode);
  });
  state.layout = mode;
}

// -----------------------------------------------------------------------------
// Analytics page
// -----------------------------------------------------------------------------
function renderAnalytics() {
  const root = document.getElementById('analytics-root');
  if (!root) return;
  root.innerHTML = '<div class="skeleton" style="height:200px;"></div>';
  API('/api/analytics').then(r => {
    if (!r.ok) return;
    const d = r.data;
    root.innerHTML = `
      <div class="section">
        <h3>Opportunities by Week</h3>
        <table class="list-table">
          <thead><tr><th>Week</th><th>Count</th><th>Avg Score</th></tr></thead>
          <tbody>${d.by_week.map(w => `<tr><td>${w.week}</td><td>${w.n}</td><td>${Math.round(w.avg_score || 0)}</td></tr>`).join('')}</tbody>
        </table>
      </div>
      <div class="section">
        <h3>By Source</h3>
        <table class="list-table">
          <thead><tr><th>Source</th><th>Count</th><th>Pool</th></tr></thead>
          <tbody>${d.by_source.map(s => `<tr><td>${escapeHtml(s.source)}</td><td>${s.n}</td><td class="mono">${fmtMoney(s.pool)}</td></tr>`).join('')}</tbody>
        </table>
      </div>
    `;
  });
}

function renderSettings() {
  const root = document.getElementById('settings-root');
  if (!root) return;
  API('/api/settings').then(r => {
    if (!r.ok) return;
    const s = r.data;
    root.innerHTML = `
      <div class="section">
        <h3>Configuration</h3>
        <p>Scan interval: <strong>${s.scan_interval_hours}h</strong></p>
        <p>Min prize: <strong>${fmtMoney(s.min_prize_usd)}</strong></p>
        <p>Min score for alert: <strong>${s.min_score_for_alert}</strong></p>
      </div>
      <div class="section">
        <h3>Notification Channels</h3>
        <p>📱 Telegram: <strong>${s.telegram_enabled ? 'enabled' : 'disabled'}</strong></p>
        <p>💬 Discord: <strong>${s.discord_enabled ? 'enabled' : 'disabled'}</strong></p>
        <p>🔔 ntfy: <strong>${s.ntfy_enabled ? 'enabled' : 'disabled'}</strong></p>
      </div>
      <div class="section">
        <h3>Integrations</h3>
        <p>📁 GitHub: <strong>${s.github_enabled ? 'enabled' : 'disabled'}</strong></p>
      </div>
    `;
  });
}

// -----------------------------------------------------------------------------
// Init
// -----------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', () => {
  // wire nav
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => setView(el.dataset.view));
  });
  // wire filters
  document.querySelectorAll('[data-status-pill]').forEach(el => {
    el.addEventListener('click', () => setStatus(el.dataset.statusPill));
  });
  document.querySelectorAll('[data-tag]').forEach(el => {
    el.addEventListener('click', () => setTag(el.dataset.tag));
  });
  document.getElementById('search-input')?.addEventListener('input', e => setSearch(e.target.value));
  document.getElementById('sort-select')?.addEventListener('change', e => setSort(e.target.value));
  document.getElementById('scan-btn')?.addEventListener('click', triggerScan);
  document.getElementById('modal-close')?.addEventListener('click', closeModal);
  document.getElementById('modal-backdrop')?.addEventListener('click', e => {
    if (e.target.id === 'modal-backdrop') closeModal();
  });

  loadStats();
  loadOpportunities();
  setView('dashboard');

  // refresh every 60s
  setInterval(() => { loadStats(); }, 60000);
});
