/* =============================================================================
   Challenge Hunter AI v2.2 — Frontend logic
   Premium UI, all views, all actions.
   ============================================================================= */

// Global error handler — catches any uncaught errors and shows a toast
// so the user never sees "nothing happens"
window.addEventListener('error', (e) => {
  console.error('Global error:', e.error || e.message);
  try {
    const stack = document.getElementById('toast-stack');
    if (stack) {
      const t = document.createElement('div');
      t.className = 'toast error';
      t.textContent = 'JS Error: ' + (e.message || 'unknown') + ' — open browser console (F12) for details';
      t.onclick = () => t.remove();
      stack.appendChild(t);
      setTimeout(() => t.remove(), 8000);
    }
  } catch (_) {}
});

const API = async (path, opts = {}) => {
  try {
    const r = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...opts
    });
    let data = null;
    try { data = await r.json(); } catch (_) { data = { error: 'invalid JSON' }; }
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
  layout: 'grid',
  opportunities: [],
  stats: {},
  loading: false
};

// Toast
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

// Format helpers
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

// ========== Card render ==========
function renderCard(opp) {
  const tags = (opp.tags || '').split(',').filter(Boolean).slice(0, 5)
    .map(t => `<span class="tag">#${escapeHtml(t.trim())}</span>`).join('');
  const score = Number(opp.opportunity_score) || 0;
  const winProb = Number(opp.win_probability) || 0;
  const scoreColor = score >= 70 ? 'var(--accent-green)'
    : score >= 50 ? 'var(--accent-yellow)' : 'var(--accent-red)';
  const scoreCircum = 2 * Math.PI * 24;
  const scoreOffset = scoreCircum * (1 - score / 100);
  const winCircum = 2 * Math.PI * 24;
  const winOffset = winCircum * (1 - winProb / 100);
  const oppId = Number(opp.id) || 0;
  const oppName = escapeHtml(opp.name || 'Untitled');
  const oppSource = escapeHtml(opp.source || 'unknown');
  const oppStatus = escapeHtml(opp.status || 'pending');
  const oppPolicy = escapeHtml(opp.ai_policy || 'unclear');
  const oppDiff = escapeHtml(opp.difficulty || 'medium');
  const oppPrize = Number(opp.prize_usd) || 0;
  const oppEv = Number(opp.expected_value) || 0;
  const oppDays = Number(opp.days_remaining) || 0;
  const oppDeadline = escapeHtml(opp.deadline || '');
  const oppRules = escapeHtml(opp.rules_summary || '').slice(0, 160);

  return `
    <div class="opp-card ${scoreClass(score)}" data-id="${oppId}" onclick="openAnalysis(${oppId})">
      <div class="header">
        <span class="source-badge">${oppSource}</span>
        <span class="status-dot-inline">
          <span class="status-dot ${opp.status === 'pending' ? '' : ''}"></span>
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
        <span class="countdown" style="font-family:var(--font-mono);">${oppDeadline}</span>
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
      <div class="tags">${tags}<span class="tag ai">AI ${oppPolicy}</span></div>
      <div class="summary">${oppRules}</div>
      <div class="actions" onclick="event.stopPropagation();">
        <button class="btn" onclick="openAnalysis(${oppId})">🔍 Analyze</button>
        <button class="btn btn-success" onclick="approve(${oppId})" title="Approve">✓</button>
        <button class="btn btn-primary" onclick="buildNow(${oppId})" title="Quick build (LLM only)">🤖</button>
        <button class="btn" onclick="hermesStart(${oppId})" title="Full autonomous Hermes pipeline (generate→test→fix→deploy→submit)" style="background:linear-gradient(135deg,var(--accent-purple),var(--accent-blue));color:white;border:none;">✦ Hermes</button>
        <button class="btn" onclick="deployNow(${oppId})" title="Deploy to Railway/Vercel" style="background:var(--accent-green);color:white;border:none;">🚀</button>
        <button class="btn" onclick="videoNow(${oppId})" title="Generate demo video" style="background:var(--accent-yellow);color:white;border:none;">🎬</button>
        <button class="btn" onclick="submitNow(${oppId})" title="Generate submission package" style="background:var(--accent-purple);color:white;border:none;">📝</button>
        <button class="btn btn-danger" onclick="reject(${oppId})" title="Reject">✕</button>
      </div>
    </div>
  `;
}

function renderListRow(opp) {
  return `
    <tr data-id="${opp.id}" onclick="openAnalysis(${opp.id})">
      <td>${escapeHtml(opp.name)}</td>
      <td style="font-family:var(--font-mono);">${fmtMoney(opp.prize_usd)}</td>
      <td>${fmtDays(opp.days_remaining)}</td>
      <td style="font-family:var(--font-mono);">${opp.opportunity_score || 0}</td>
      <td style="font-family:var(--font-mono);">${opp.win_probability || 0}%</td>
      <td>${escapeHtml(opp.ai_policy || 'unclear')}</td>
      <td>${escapeHtml(opp.source || '')}</td>
    </tr>
  `;
}

// Hero stats
function renderHeroStats(s) {
  const root = document.getElementById('hero-stats');
  if (!root) return;
  root.innerHTML = `
    <div class="hero-stat">
      <div class="value">${fmtNum(s.total_active || 0)}</div>
      <div class="label">Active opportunities</div>
    </div>
    <div class="hero-stat">
      <div class="value">${fmtMoney(s.total_prize_pool || 0)}</div>
      <div class="label">Prize pool</div>
    </div>
    <div class="hero-stat">
      <div class="value">${fmtNum(s.high_priority || 0)}</div>
      <div class="label">High priority</div>
    </div>
    <div class="hero-stat">
      <div class="value">${fmtMoney(s.expected_value_total || 0)}</div>
      <div class="label">Expected value</div>
    </div>
    <div class="hero-stat">
      <div class="value">${s.avg_win_probability || 0}%</div>
      <div class="label">Avg win rate</div>
    </div>
  `;
}

// Loaders
async function loadStats() {
  const r = await API('/api/stats');
  if (r.ok) {
    state.stats = r.data;
    renderHeroStats(r.data);
  }
}

async function loadOpportunities() {
  state.loading = true;
  showSkeleton();
  const params = new URLSearchParams();
  if (state.status === 'all' || !state.status) {
    // no filter
  } else if (state.status === 'high') {
    params.set('min_score', '70');
  } else if (state.status === 'building' || state.status === 'submitted' || state.status === 'complete') {
    params.set('status', 'approved');
  } else {
    params.set('status', state.status);
  }
  if (state.tag) params.set('tag', state.tag);
  if (state.search) params.set('search', state.search);
  if (state.sort) params.set('sort_by', state.sort);
  
  try {
    const r = await API('/api/opportunities?' + params.toString());
    state.loading = false;
    if (!r.ok) {
      toast('Failed to load opportunities: ' + (r.data?.error || r.status), 'error');
      // Clear skeleton and show error message
      const grid = document.getElementById('card-grid');
      if (grid) {
        grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:60px 20px; color:var(--accent-red);"><h3>Failed to load opportunities</h3><p>Error: ' + (r.data?.error || r.status) + '</p><button class="btn" onclick="loadOpportunities()">Retry</button></div>';
      }
      return;
    }
    state.opportunities = r.data.items;
    renderOpportunities();
  } catch (err) {
    state.loading = false;
    toast('Network error: ' + err.message, 'error');
    const grid = document.getElementById('card-grid');
    if (grid) {
      grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:60px 20px; color:var(--accent-red);"><h3>Network error</h3><p>' + err.message + '</p><button class="btn" onclick="loadOpportunities()">Retry</button></div>';
    }
  }
}

function renderOpportunities() {
  const grid = document.getElementById('card-grid');
  const tbody = document.querySelector('#list-table tbody');
  
  // Show empty state if no opportunities
  if (state.opportunities.length === 0 && !state.loading) {
    const emptyMsg = '<div style="grid-column:1/-1; text-align:center; padding:60px 20px; color:var(--text-muted);"><h3 style="margin-bottom:10px;">No opportunities found</h3><p>Try adjusting filters or click "⚡ Scan Now" to discover new opportunities.</p></div>';
    if (grid) grid.innerHTML = emptyMsg;
    if (tbody) tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:40px; color:var(--text-muted);">No opportunities found</td></tr>';
  } else {
    if (grid) grid.innerHTML = state.opportunities.map(renderCard).join('');
    if (tbody) tbody.innerHTML = state.opportunities.map(renderListRow).join('');
  }
  
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

// Actions
async function approve(id) {
  const card = document.querySelector(`.opp-card[data-id="${id}"]`);
  if (card) card.style.opacity = '0.5';
  const r = await API(`/api/opportunities/${id}/approve`, { method: 'POST' });
  if (r.ok) {
    toast(`Approved #${id}. Use ✦ Hermes for full build.`, 'success');
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

async function buildNow(id) {
  if (!confirm(`🤖 Quick build for #${id}?\n\nSingle LLM call (1-3 min). No testing or fixing.\n\nFor the full autonomous pipeline (generate → test → fix → deploy → submit), use ✦ Hermes instead.`)) return;
  toast('🤖 Quick build started...', 'info');
  const r = await API(`/api/opportunities/${id}/build`, { method: 'POST' });
  if (r.ok) {
    toast(`Build started for #${id}. Check back in 1-2 min.`, 'success');
    pollBuildStatus(id);
  } else {
    toast('Build failed: ' + (r.data?.error || r.status), 'error');
  }
}

async function hermesStart(id) {
  if (!confirm(`✦ Start full Hermes pipeline for #${id}?\n\nThis is the FULL autonomous loop:\n  1. Generate code via LLM\n  2. Install dependencies\n  3. Run tests\n  4. Auto-fix failures (up to 3 attempts)\n  5. Security audit (bandit)\n  6. Commit to GitHub\n  7. Deploy to Railway/Vercel\n  8. Generate demo video\n  9. Generate submission package\n\nTakes 5-30 minutes. Requires LLM keys + GITHUB_TOKEN + (optionally) RAILWAY_TOKEN.`)) return;
  toast('✦ Hermes pipeline starting...', 'info');
  const r = await API(`/api/opportunities/${id}/hermes`, { method: 'POST' });
  if (r.ok) {
    toast(`Hermes running for #${id}. Watch dashboard for progress.`, 'success');
    showActiveBuild(id);
    pollHermesStatus(id);
  } else {
    toast('Hermes failed: ' + (r.data?.error || r.status), 'error');
  }
}

async function deployNow(id) {
  if (!confirm(`🚀 Deploy #${id}?\n\nPushes generated code to GitHub + (if Railway/Vercel tokens are set) deploys it live.\n\nRequires GITHUB_TOKEN + (optionally) RAILWAY_TOKEN / VERCEL_TOKEN on the server.`)) return;
  toast('🚀 Deploy started...', 'info');
  const r = await API(`/api/deploy/${id}`, { method: 'POST' });
  if (r.ok) toast(`Deployment triggered for #${id}. Check back in 1-2 min.`, 'success');
  else toast('Deploy failed: ' + (r.data?.error || r.status), 'error');
}

async function videoNow(id) {
  if (!confirm(`🎬 Generate demo video for #${id}?\n\nAI writes a script, generates slides, and (if gTTS/ffmpeg available) renders an MP4.\n\nTakes 1-2 minutes.`)) return;
  toast('🎬 Video generation started...', 'info');
  const r = await API(`/api/video/${id}/generate`, { method: 'POST' });
  if (r.ok) toast(`Video started for #${id}. Check back in 1-2 min.`, 'success');
  else toast('Video failed: ' + (r.data?.error || r.status), 'error');
}

async function submitNow(id) {
  toast('📝 Generating submission package...', 'info');
  const r = await API(`/api/submit/${id}/package`);
  if (r.ok && r.data.package) {
    const pkg = r.data.package;
    const lines = [
      '📋 SUBMISSION PACKAGE — #' + id,
      '',
      `Project: ${pkg.project?.name || '?'}`,
      `Tagline: ${pkg.project?.tagline || ''}`,
      `Deadline: ${pkg.deadline} (${pkg.days_remaining}d remaining)`,
      '',
      '--- TECH STACK ---',
      Object.entries(pkg.project?.tech_stack || {}).map(([k, v]) => `${k}: ${(v || []).join(', ')}`).join('\n'),
      '',
      '--- DESCRIPTION (first 800 chars) ---',
      pkg.project?.description?.slice(0, 800) + '...',
      '',
      '--- CHECKLIST ---',
      Object.entries(pkg.submission_checklist || {}).map(([k, v]) => `${k}: ${v}`).join('\n'),
    ];
    alert(lines.join('\n'));
    toast('Submission package ready — see alert', 'success');
  } else {
    toast('Package failed: ' + (r.data?.error || r.status), 'error');
  }
}

async function triggerScan() {
  const btn = document.getElementById('scan-btn');
  const originalText = btn ? btn.innerHTML : null;
  if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Scanning…'; }
  toast('Scan triggered', 'info');
  try {
    const r = await API('/api/scan', { method: 'POST' });
    if (r.ok) {
      toast(`Scan started (${r.data.scan_id})`, 'success');
      setTimeout(() => { loadOpportunities(); loadStats(); }, 15000);
    } else toast('Scan failed', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = originalText || '⚡ Scan Now'; }
  }
}

function showActiveBuild(id) {
  const card = document.getElementById('active-build-card');
  const idSpan = document.getElementById('active-build-id');
  if (card && idSpan) {
    idSpan.textContent = id;
    card.style.display = 'block';
  }
}

async function pollBuildStatus(id) {
  showActiveBuild(id);
  let checks = 0;
  const poll = setInterval(async () => {
    checks++;
    const stat = await API('/api/build/status');
    if (stat.ok && stat.data.some(b => b.id === id && b.build_status === 'complete')) {
      clearInterval(poll);
      toast(`✅ Build complete for #${id}!`, 'success');
      document.getElementById('active-build-card').style.display = 'none';
      loadOpportunities(); loadStats();
    } else if (stat.ok && stat.data.some(b => b.id === id && b.build_status === 'failed')) {
      clearInterval(poll);
      toast(`❌ Build failed for #${id}`, 'error');
      document.getElementById('active-build-card').style.display = 'none';
      loadOpportunities();
    } else if (checks >= 12) {
      clearInterval(poll);
      toast(`⏳ Build still running for #${id} (5 min)`, 'info');
    }
  }, 5000);
}

async function pollHermesStatus(id) {
  let checks = 0;
  const poll = setInterval(async () => {
    checks++;
    const r = await API(`/api/hermes/${id}/status`);
    if (r.ok && !r.data.running) {
      clearInterval(poll);
      document.getElementById('active-build-card').style.display = 'none';
      const fixAttempts = r.data.log.filter(l => l.step && l.step.startsWith('hermes_fix')).length;
      toast(`✦ Hermes complete for #${id}! (${fixAttempts} fix attempts)`, 'success');
      loadOpportunities(); loadStats();
    } else if (checks >= 60) {
      clearInterval(poll);
      toast(`⏳ Hermes still running for #${id} (15+ min)`, 'info');
    }
  }, 10000);  // poll every 10s (Hermes takes longer)
}

// Analysis modal
async function openAnalysis(id) {
  const oppId = Number(id) || 0;
  if (!oppId) { toast('Invalid opportunity ID', 'error'); return; }
  const modal = document.getElementById('modal');
  if (!modal) { toast('Modal element missing', 'error'); return; }
  let r;
  try { r = await API(`/api/opportunities/${oppId}`); }
  catch (err) { toast(`Failed to load: ${err.message}`, 'error'); return; }
  if (!r.ok) { toast(`Failed to load #${oppId}: ${r.status}`, 'error'); return; }
  const opp = r.data;
  if (!opp || !opp.id) { toast('Opportunity data is empty', 'error'); return; }
  let a = {};
  try { a = typeof opp.analysis_json === 'string' ? JSON.parse(opp.analysis_json) : (opp.analysis_json || {}); }
  catch (_) { a = {}; }
  const rp = a.recommended_project || {};
  const tech = rp.tech_stack || {};
  const techAll = [
    ...(tech.frontend || []), ...(tech.backend || []),
    ...(tech.database || []), ...(tech.ai || []), ...(tech.deployment || [])
  ];
  const score = Number(opp.opportunity_score) || 0;
  const winProb = Number(opp.win_probability) || 0;
  const prize = Number(opp.prize_usd) || 0;
  const ev = Number(opp.expected_value) || 0;
  const days = Number(opp.days_remaining) || 0;
  const scoreCirc = 2 * Math.PI * 32;
  const scoreOff = scoreCirc * (1 - score / 100);
  const winOff = scoreCirc * (1 - winProb / 100);

  const sidebarHTML = [
    '<h2 style="margin:0 0 1rem; font-size:20px; font-weight:700; letter-spacing:-0.02em;">', escapeHtml(opp.name || 'Untitled'), '</h2>',
    '<div class="prize-block"><span class="amount">', fmtMoney(prize), '</span>',
    '<span class="ev">EV ', fmtMoney(ev), '</span></div>',
    '<div class="deadline ', deadlineClass(days), '" style="margin:1rem 0;">',
    '<span>⏱</span><span>', fmtDays(days), ' remaining</span></div>',
    '<div style="margin:1rem 0; display:flex; gap:1rem;">',
    '<div class="gauge"><svg width="80" height="80" viewBox="0 0 80 80">',
    '<circle class="gauge-bg" cx="40" cy="40" r="32" fill="none" stroke-width="6"/>',
    '<circle class="gauge-fg" cx="40" cy="40" r="32" fill="none" stroke="var(--accent-green)" stroke-width="6"',
    'stroke-dasharray="', scoreCirc, '" stroke-dashoffset="', scoreOff, '" stroke-linecap="round"/></svg>',
    '<div class="label">', score, '</div><div class="small-label">score</div></div>',
    '<div class="gauge"><svg width="80" height="80" viewBox="0 0 80 80">',
    '<circle class="gauge-bg" cx="40" cy="40" r="32" fill="none" stroke-width="6"/>',
    '<circle class="gauge-fg" cx="40" cy="40" r="32" fill="none" stroke="var(--accent-blue)" stroke-width="6"',
    'stroke-dasharray="', scoreCirc, '" stroke-dashoffset="', winOff, '" stroke-linecap="round"/></svg>',
    '<div class="label">', winProb, '%</div><div class="small-label">win</div></div>',
    '</div>',
    '<div style="font-size:12px; color:var(--text-muted); margin-top:0.5rem;">',
    'AI: <strong>', escapeHtml(opp.ai_policy || 'unclear'), '</strong><br>',
    'Difficulty: <strong>', escapeHtml(opp.difficulty || 'medium'), '</strong><br>',
    'Source: <strong>', escapeHtml(opp.source || ''), '</strong></div>',
    '<a href="', escapeHtml(opp.url || '#'), '" target="_blank" rel="noopener" class="btn btn-ghost" style="margin-top:1rem; width:100%; justify-content:center;">🔗 Open source</a>',
    '<div style="display:flex; gap:0.5rem; margin-top:1rem; flex-wrap:wrap;">',
    '<button class="btn btn-success" style="flex:1;" onclick="approve(', opp.id, '); document.getElementById(\'modal\').classList.remove(\'show\');">✓ Approve</button>',
    '<button class="btn btn-primary" style="flex:1;" onclick="hermesStart(', opp.id, '); document.getElementById(\'modal\').classList.remove(\'show\');">✦ Full Hermes</button>',
    '<button class="btn" onclick="buildNow(', opp.id, '); document.getElementById(\'modal\').classList.remove(\'show\');" title="Quick build only">🤖</button>',
    '<button class="btn btn-danger" onclick="reject(', opp.id, '); document.getElementById(\'modal\').classList.remove(\'show\');">✕</button>',
    '</div>',
    '<div style="display:flex; gap:0.5rem; margin-top:0.5rem; flex-wrap:wrap;">',
    '<button class="btn" style="flex:1;" onclick="deployNow(', opp.id, '); document.getElementById(\'modal\').classList.remove(\'show\');">🚀 Deploy</button>',
    '<button class="btn" style="flex:1;" onclick="videoNow(', opp.id, '); document.getElementById(\'modal\').classList.remove(\'show\');">🎬 Video</button>',
    '<button class="btn" style="flex:1;" onclick="submitNow(', opp.id, '); document.getElementById(\'modal\').classList.remove(\'show\');">📝 Submit</button>',
    '</div>'
  ].join('');

  const bodyParts = [];
  bodyParts.push('<div class="section callout"><h3>Summary</h3><p>',
    escapeHtml(a.summary || 'No analysis yet.'), '</p></div>');
  bodyParts.push('<div class="section green"><h3>Why This Is Good</h3><p>',
    escapeHtml(a.why_this_is_good || ''), '</p></div>');
  bodyParts.push('<div class="section"><h3>Requirements</h3><ul>',
    (a.requirements || []).map(r => '<li>' + escapeHtml(r) + '</li>').join(''),
    '</ul></div>');
  bodyParts.push('<div class="section yellow"><h3>Risks</h3><ul>',
    (a.risks || []).map(r => '<li>' + escapeHtml(r) + '</li>').join(''),
    '</ul></div>');
  bodyParts.push('<div class="recommended-project">',
    '<h2>🚀 ', escapeHtml(rp.name || 'Recommended Project'), '</h2>',
    '<div style="color:var(--text-secondary); margin-bottom:1rem; font-style:italic;">',
    escapeHtml(rp.tagline || ''), '</div>',
    '<p>', escapeHtml(rp.concept || ''), '</p>',
    '<p><strong>Problem:</strong> ', escapeHtml(rp.problem_solved || ''), '</p>',
    '<h3>Tech Stack</h3>',
    '<div class="tech-pills">', techAll.map(t => '<span class="tech-pill">' + escapeHtml(t) + '</span>').join(''), '</div>',
    '<h3 style="margin-top:1rem;">Key Features</h3><ul>',
    (rp.key_features || []).map(f => '<li>' + escapeHtml(f) + '</li>').join(''),
    '</ul>',
    '<h3 style="margin-top:1rem;">Demo Approach</h3><p>',
    escapeHtml(rp.demo_approach || ''), '</p>',
    '<div class="section purple" style="margin-top:1rem;"><h3>Wow Factor</h3><p>',
    escapeHtml(rp.wow_factor || ''), '</p></div>',
    '<div style="margin-top:1rem; font-size:12px; color:var(--text-muted);">',
    'Estimated build: <strong>', (rp.estimated_build_days || '?'), ' days</strong></div>',
    '</div>');
  bodyParts.push('<div class="section purple"><h3>Submission Strategy</h3><p>',
    escapeHtml(a.submission_strategy || ''), '</p></div>');
  bodyParts.push('<div class="section"><h3>Judge Appeal</h3><p>',
    escapeHtml(a.judge_appeal || ''), '</p></div>');
  bodyParts.push('<div class="section"><h3>Alternatives</h3>',
    (a.alternative_projects || []).map(p =>
      '<div style="margin:0.5rem 0;"><strong>' + escapeHtml(p.name || '?') + '</strong> — ' +
      escapeHtml(p.concept || '?') + ' <span style="color:var(--text-muted);">(' +
      (p.build_days || '?') + 'd)</span></div>'
    ).join(''),
    '</div>');
  bodyParts.push('<div class="section ', (a.recommended_action === 'approve' ? 'green' : 'red'),
    '"><h3>Recommended Action: ', escapeHtml((a.recommended_action || 'monitor').toUpperCase()),
    '</h3><p>', escapeHtml(a.action_reasoning || ''), '</p></div>');
  const bodyHTML = bodyParts.join('');

  try {
    const sb = document.getElementById('modal-sidebar');
    const bd = document.getElementById('modal-body');
    if (!sb || !bd) { toast('Modal sub-elements missing', 'error'); return; }
    sb.innerHTML = sidebarHTML;
    bd.innerHTML = bodyHTML;
    modal.classList.add('show');
  } catch (err) {
    console.error('Modal render failed:', err);
    toast('Render error: ' + err.message, 'error');
  }
}

function closeModal() { document.getElementById('modal')?.classList.remove('show'); }
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

// Views
function setView(v) {
  state.view = v;
  document.querySelectorAll('.nav-item').forEach(el => {
    el.classList.toggle('active', el.dataset.view === v);
  });
  const views = {
    dashboard: 'dashboard-view', high: 'dashboard-view', approved: 'dashboard-view',
    building: 'dashboard-view', submitted: 'dashboard-view',
    calendar: 'calendar-view', advisor: 'advisor-view', research: 'research-view',
    analytics: 'analytics-view', settings: 'settings-view',
  };
  const target = views[v] || 'dashboard-view';
  ['dashboard-view', 'calendar-view', 'advisor-view', 'research-view',
   'analytics-view', 'settings-view'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = (id === target) ? '' : 'none';
  });
  const titles = {
    dashboard: 'Dashboard', high: 'High Priority', approved: 'Approved',
    building: 'Building', submitted: 'Submitted',
    calendar: 'Calendar', advisor: 'AI Advisor', research: 'Research',
    analytics: 'Analytics', settings: 'Settings'
  };
  const t = document.getElementById('page-title');
  if (t) t.textContent = titles[v] || 'Dashboard';
  if (v === 'dashboard') setStatus('all');
  else if (v === 'high') setStatus('high');
  else if (v === 'approved') setStatus('approved');
  else if (v === 'building') setStatus('building');
  else if (v === 'submitted') setStatus('submitted');
  else if (v === 'calendar') renderCalendar();
  else if (v === 'advisor') renderAdvisor();
  else if (v === 'research') renderResearch();
  else if (v === 'analytics') renderAnalytics();
  else if (v === 'settings') renderSettings();
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

function setSort(s) { state.sort = s; loadOpportunities(); }
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
  document.querySelectorAll('[data-layout]').forEach(el => {
    el.classList.toggle('active', el.dataset.layout === mode);
  });
  state.layout = mode;
}

// Calendar view
async function renderCalendar() {
  const root = document.getElementById('calendar-root');
  if (!root) return;
  root.innerHTML = '<div class="skeleton" style="height:200px;"></div>';
  const r = await API('/api/advisor/calendar');
  if (!r.ok || !r.data) {
    root.innerHTML = '<div class="advisor-section">Failed to load calendar</div>';
    return;
  }
  const buckets = r.data;
  const bucketMeta = {
    this_week: { title: '⚠ This week (urgent)', class: 'urgent' },
    next_week: { title: '◷ Next week', class: 'soon' },
    this_month: { title: '◎ This month', class: 'month' },
    later: { title: '○ Later', class: 'later' },
  };
  const html = ['<div class="advisor-section"><h2>◷ Deadline Calendar</h2>'];
  for (const [key, meta] of Object.entries(bucketMeta)) {
    const items = buckets[key] || [];
    html.push(`<div class="calendar-bucket ${meta.class}"><h3>${meta.title} (${items.length})</h3>`);
    if (items.length === 0) {
      html.push('<div style="color:var(--text-muted); font-size:13px;">No opportunities in this window</div>');
    } else {
      html.push('<table class="list-table"><thead><tr><th>Name</th><th>Prize</th><th>Days</th><th>Score</th></tr></thead><tbody>');
      for (const o of items) {
        html.push(`<tr style="cursor:pointer;" onclick="openAnalysis(${o.id})"><td>${escapeHtml(o.name)}</td><td style="font-family:var(--font-mono);">${fmtMoney(o.prize_usd)}</td><td>${o.days_remaining}d</td><td style="font-family:var(--font-mono);">${o.opportunity_score}</td></tr>`);
      }
      html.push('</tbody></table>');
    }
    html.push('</div>');
  }
  html.push('</div>');
  root.innerHTML = html.join('');
}

// Advisor view
async function renderAdvisor() {
  const root = document.getElementById('advisor-root');
  if (!root) return;
  // Daily standup
  const standup = await API('/api/advisor/daily');
  if (standup.ok && standup.data) {
    const s = standup.data;
    const standupHtml = [
      '<div class="advisor-section" style="margin-bottom:14px;">',
      `<strong>${s.pending_total}</strong> active opportunities · `,
      `<strong>$${(s.total_prize_pool || 0).toLocaleString()}</strong> prize pool · `,
      `<strong>$${(s.total_expected_value || 0).toLocaleString()}</strong> expected value`,
      (s.urgent && s.urgent.length > 0) ? `<br><br>⚠ <strong>${s.urgent.length} urgent:</strong> ${s.urgent.slice(0, 3).map(o => `#${o.id} ${o.name.slice(0, 30)} (${o.days_remaining}d)`).join(', ')}` : '',
      '</div>'
    ].join('');
    document.getElementById('standup-content').innerHTML = standupHtml;
  }
  // AI advice
  const advice = await API('/api/advisor/advice');
  if (advice.ok && advice.data) {
    const a = advice.data;
    let adviceHtml = `<div class="advisor-section" style="margin-bottom:14px;">`;
    if (a.top_pick) {
      const p = a.top_pick;
      adviceHtml += `<div style="margin-bottom:14px; padding:14px; background:rgba(48,209,88,0.1); border:1px solid rgba(48,209,88,0.3); border-radius:12px;">
        <strong>✦ Top pick:</strong> #${p.id} ${escapeHtml(p.name)}<br>
        <span style="font-family:var(--font-mono);">$${p.prize_usd.toLocaleString()}</span> ·
        <span>${p.days_remaining}d left</span> ·
        <span>score ${p.opportunity_score}</span>
      </div>`;
    }
    adviceHtml += `<div class="advice-text">${escapeHtml(a.advice || 'No advice available')}</div>`;
    if (a.note) adviceHtml += `<div style="margin-top:10px; font-size:12px; color:var(--text-muted);">${escapeHtml(a.note)}</div>`;
    adviceHtml += '</div>';
    document.getElementById('advice-content').innerHTML = adviceHtml;
  }
  // Top recommendations
  const recs = await API('/api/advisor/recommendations');
  if (recs.ok && recs.data && recs.data.items) {
    const items = recs.data.items;
    let recHtml = '<table class="list-table"><thead><tr><th>#</th><th>Name</th><th>Prize</th><th>Days</th><th>Score</th><th>Composite</th><th>Priority</th></tr></thead><tbody>';
    for (const o of items) {
      recHtml += `<tr style="cursor:pointer;" onclick="openAnalysis(${o.id})">
        <td>${o.id}</td>
        <td>${escapeHtml(o.name)}</td>
        <td style="font-family:var(--font-mono);">$${(o.prize_usd || 0).toLocaleString()}</td>
        <td>${o.days_remaining || 0}d</td>
        <td style="font-family:var(--font-mono);">${o.opportunity_score || 0}</td>
        <td style="font-family:var(--font-mono);">${o.composite_score || 0}</td>
        <td>${o.priority || '—'}</td>
      </tr>`;
    }
    recHtml += '</tbody></table>';
    document.getElementById('recommendations-content').innerHTML = recHtml;
  }
}

// Research view
async function renderResearch() {
  const root = document.getElementById('research-root');
  if (!root) return;
  const r = await API('/api/research/data');
  if (!r.ok || !r.data) {
    root.innerHTML = '<div class="advisor-section">Failed to load research data</div>';
    return;
  }
  const items = r.data.items || [];
  if (items.length === 0) {
    root.innerHTML = '<div class="advisor-section"><h2>⌘ Research Data</h2><p style="color:var(--text-muted);">No research yet. Trigger a scan via the backend to populate.</p></div>';
    return;
  }
  const html = ['<div class="advisor-section"><h2>⌘ Research Data (past winners)</h2>',
    '<table class="list-table"><thead><tr><th>Title</th><th>Category</th><th>Prize</th><th>Winner</th></tr></thead><tbody>'];
  for (const o of items) {
    html.push(`<tr><td>${escapeHtml(o.title || '?')}</td><td>${escapeHtml(o.category || '?')}</td><td style="font-family:var(--font-mono);">$${(o.prize_usd || 0).toLocaleString()}</td><td>${escapeHtml(o.winner_name || '?')}</td></tr>`);
  }
  html.push('</tbody></table></div>');
  root.innerHTML = html.join('');
}

// Analytics view
async function renderAnalytics() {
  const root = document.getElementById('analytics-root');
  if (!root) return;
  root.innerHTML = '<div class="skeleton" style="height:200px;"></div>';
  const r = await API('/api/analytics');
  if (!r.ok || !r.data) return;
  const d = r.data;
  root.innerHTML =
    '<div class="advisor-section"><h2>◐ Analytics</h2>' +
    '<div class="section"><h3>By Source</h3><table class="list-table"><thead><tr><th>Source</th><th>Count</th><th>Pool</th></tr></thead><tbody>' +
    (d.by_source || []).map(s =>
      '<tr><td>' + escapeHtml(s.source || '?') + '</td><td>' + (s.n || 0) + '</td><td style="font-family:var(--font-mono);">' + fmtMoney(s.pool) + '</td></tr>'
    ).join('') + '</tbody></table></div>' +
    '<div class="section"><h3>By Week</h3><table class="list-table"><thead><tr><th>Week</th><th>Count</th><th>Avg Score</th></tr></thead><tbody>' +
    (d.by_week || []).map(w =>
      '<tr><td>' + (w.week || '?') + '</td><td>' + (w.n || 0) + '</td><td>' + Math.round(w.avg_score || 0) + '</td></tr>'
    ).join('') + '</tbody></table></div>' +
    '</div>';
}

// Settings view
async function renderSettings() {
  const root = document.getElementById('settings-root');
  if (!root) return;
  const r = await API('/api/settings');
  if (!r.ok || !r.data) return;
  const s = r.data;
  root.innerHTML = '<div class="advisor-section"><h2>⚙ Settings</h2>' +
    '<div class="section"><h3>Integrations</h3>' +
    `<p>📱 Telegram: <strong>${s.telegram_enabled ? '✅ enabled' : '❌ disabled'}</strong></p>` +
    `<p>💬 Discord: <strong>${s.discord_enabled ? '✅ enabled' : '❌ disabled'}</strong></p>` +
    `<p>🔔 ntfy: <strong>${s.ntfy_enabled ? '✅ enabled' : '❌ disabled'}</strong></p>` +
    `<p>🤖 LLM: <strong>${s.llm_configured ? '✅ configured' : '❌ not configured'}</strong> (tokenrouter / NVIDIA NIM)</p>` +
    `<p>📁 GitHub: <strong>${s.github_enabled ? '✅ enabled' : '❌ disabled'}</strong></p>` +
    `<p>🚀 Railway: <strong>${s.railway_enabled ? '✅ enabled' : '❌ disabled'}</strong></p>` +
    `<p>▲ Vercel: <strong>${s.vercel_enabled ? '✅ enabled' : '❌ disabled'}</strong></p>` +
    '</div>' +
    '<div class="section"><h3>Configuration</h3>' +
    `<p>Scan interval: <strong>${s.scan_interval_hours}h</strong></p>` +
    `<p>Min prize: <strong>${fmtMoney(s.min_prize_usd)}</strong></p>` +
    `<p>Min score for alert: <strong>${s.min_score_for_alert}</strong></p>` +
    '</div>' +
    `<div class="section"><h3>Setup instructions</h3>` +
    '<p>To enable features, set these env vars in Railway:</p>' +
    '<pre style="background:var(--bg-base); padding:14px; border-radius:8px; font-size:12px; color:var(--text-secondary); overflow-x:auto;">' +
    'LLM_PRIMARY_KEY=your-tokenrouter-key\nLLM_FALLBACK_KEY=your-nvidia-key\nGITHUB_TOKEN=ghp_xxxxx\nGITHUB_USERNAME=yourname\nRAILWAY_TOKEN=xxxxx\nTELEGRAM_BOT_TOKEN=xxxxx\nTELEGRAM_CHAT_ID=xxxxx' +
    '</pre></div></div>';
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.nav-item').forEach(el => {
    el.addEventListener('click', () => setView(el.dataset.view));
  });
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

  setInterval(() => { loadStats(); }, 60000);
});
