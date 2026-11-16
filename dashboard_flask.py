"""
dashboard_flask.py - Enterprise 4-Tab Agentic Underwriting Workstation (RBAC + Home Credit)
"""
from flask import Flask, render_template_string

app = Flask(__name__)

APPLICANT_PROFILES = {
    "100001": {
        "applicant_id": "100001",
        "name": "SK_100001 — Home Credit Test Applicant #1",
        "consent_given": True,
        "AMT_INCOME_TOTAL": 135000.0,
        "AMT_CREDIT": 568800.0,
        "AMT_ANNUITY": 20560.5,
        "AMT_GOODS_PRICE": 450000.0,
        "DAYS_EMPLOYED": -2329,
        "CNT_CHILDREN": 0,
        "CNT_FAM_MEMBERS": 2,
        "FLAG_OWN_CAR": "N",
        "FLAG_OWN_REALTY": "Y",
        "NAME_INCOME_TYPE": "Working",
        "NAME_EDUCATION_TYPE": "Higher education",
        "NAME_HOUSING_TYPE": "House / apartment",
    },
    "100005": {
        "applicant_id": "100005",
        "name": "SK_100005 — Home Credit Test Applicant #2",
        "consent_given": True,
        "AMT_INCOME_TOTAL": 99000.0,
        "AMT_CREDIT": 222768.0,
        "AMT_ANNUITY": 17370.0,
        "AMT_GOODS_PRICE": 180000.0,
        "DAYS_EMPLOYED": -4469,
        "CNT_CHILDREN": 0,
        "CNT_FAM_MEMBERS": 2,
        "FLAG_OWN_CAR": "N",
        "FLAG_OWN_REALTY": "Y",
        "NAME_INCOME_TYPE": "Working",
        "NAME_EDUCATION_TYPE": "Secondary / secondary special",
        "NAME_HOUSING_TYPE": "House / apartment",
    },
    "100013": {
        "applicant_id": "100013",
        "name": "SK_100013 — High Credit / Vehicle Owner",
        "consent_given": True,
        "AMT_INCOME_TOTAL": 202500.0,
        "AMT_CREDIT": 663264.0,
        "AMT_ANNUITY": 69777.0,
        "AMT_GOODS_PRICE": 630000.0,
        "DAYS_EMPLOYED": -4458,
        "CNT_CHILDREN": 0,
        "CNT_FAM_MEMBERS": 2,
        "FLAG_OWN_CAR": "Y",
        "FLAG_OWN_REALTY": "Y",
        "NAME_INCOME_TYPE": "Working",
        "NAME_EDUCATION_TYPE": "Higher education",
        "NAME_HOUSING_TYPE": "House / apartment",
    },
    "HIGH_RISK_CUSTOM": {
        "applicant_id": "HIGH_RISK_CUSTOM",
        "name": "Custom High-Leverage Test Case",
        "consent_given": True,
        "AMT_INCOME_TOTAL": 45000.0,
        "AMT_CREDIT": 900000.0,
        "AMT_ANNUITY": 55000.0,
        "AMT_GOODS_PRICE": 750000.0,
        "DAYS_EMPLOYED": -90,
        "CNT_CHILDREN": 3,
        "CNT_FAM_MEMBERS": 5,
        "FLAG_OWN_CAR": "N",
        "FLAG_OWN_REALTY": "N",
        "NAME_INCOME_TYPE": "Commercial associate",
        "NAME_EDUCATION_TYPE": "Lower secondary",
        "NAME_HOUSING_TYPE": "Rented apartment",
    },
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Enterprise Credit Underwriting Workstation</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdn.tailwindcss.com"></script>
<script>
  tailwind.config = {
    theme: {
      extend: {
        fontFamily: { sans: ['Inter','sans-serif'], mono: ['JetBrains Mono','monospace'] },
        colors: {
          canvas: '#0B0F19', panel: '#121826', panel2: '#0F1420',
          border: '#232B3D', ink: '#E7EAF0', mute: '#8B93A7',
          brand: '#6366F1', brand2: '#818CF8',
          good: '#22C77A', warn: '#F5A524', bad: '#F0505A'
        },
        boxShadow: { card: '0 1px 2px rgba(0,0,0,0.4), 0 8px 24px -12px rgba(0,0,0,0.5)' }
      }
    }
  }
</script>
<style>
  body { background: radial-gradient(circle at 20% 0%, #141B2D 0%, #0B0F19 55%); }
  .card { background: #121826; border: 1px solid #232B3D; }
  .field { background: #0F1420; border: 1px solid #232B3D; color: #E7EAF0; }
  .field:focus { outline: none; border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }
  .bar-track { background: #1A2133; }
  .spin { animation: spin 0.8s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
  .fade-in { animation: fadeIn 0.3s ease both; } @keyframes fadeIn { from { opacity:0; transform: translateY(4px);} to {opacity:1; transform:none;} }
</style>
</head>
<body class="bg-canvas text-ink font-sans min-h-screen">

  <!-- LOGIN MODAL -->
  <div id="login-screen" class="min-h-screen flex items-center justify-center p-6">
    <div class="card rounded-2xl shadow-card p-8 w-full max-w-md space-y-6">
      <div class="flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-brand to-brand2 flex items-center justify-center font-bold text-white">AI</div>
        <div>
          <h1 class="text-base font-semibold text-ink">Credit Underwriting Workstation</h1>
          <p class="text-xs text-mute">Role-Based JWT Authentication · Home Credit</p>
        </div>
      </div>

      <div class="space-y-4">
        <div>
          <label class="text-[11px] font-semibold text-mute uppercase tracking-wider">Quick Role Select</label>
          <select id="quick-role" onchange="fillDemoUser()" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            <option value="officer">Loan Officer (officer / officer123)</option>
            <option value="underwriter">Senior Underwriter (underwriter / underwriter123)</option>
            <option value="admin">Risk Admin (admin / admin123)</option>
          </select>
        </div>
        <div>
          <label class="text-[11px] text-mute font-medium">Username</label>
          <input id="login-user" value="officer" class="field w-full rounded-lg p-2.5 text-sm mt-1">
        </div>
        <div>
          <label class="text-[11px] text-mute font-medium">Password</label>
          <input id="login-pass" type="password" value="officer123" class="field w-full rounded-lg p-2.5 text-sm mt-1">
        </div>
        <div id="login-error" class="hidden text-xs text-bad bg-bad/10 border border-bad/30 rounded-lg p-2.5"></div>
        <button onclick="doLogin()" class="w-full bg-gradient-to-r from-brand to-brand2 hover:opacity-90 text-white font-semibold py-2.5 rounded-xl text-sm">
          Sign In to Workstation
        </button>
      </div>
    </div>
  </div>

  <!-- MAIN WORKSTATION -->
  <div id="app-shell" class="hidden">
    <header class="border-b border-border/80 px-6 md:px-8 py-4 flex flex-wrap justify-between items-center gap-4 sticky top-0 bg-canvas/90 backdrop-blur z-10">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-brand to-brand2 flex items-center justify-center font-bold text-white text-sm">AI</div>
        <div>
          <h1 class="text-[15px] font-semibold tracking-tight text-ink">Home Credit Underwriting Workstation</h1>
          <p class="text-[11px] text-mute">XGBoost · Isolation Forest · SHAP · MCP · RBAC</p>
        </div>
      </div>

      <!-- 4 Navigation Tabs -->
      <nav class="flex items-center gap-1.5 bg-panel2 border border-border rounded-xl p-1">
        <button onclick="switchTab('underwrite')" id="tab-btn-underwrite" class="tab-btn px-3 py-1.5 rounded-lg text-xs font-medium bg-brand text-white">1. Underwrite / Lookup</button>
        <button onclick="switchTab('review')" id="tab-btn-review" class="tab-btn px-3 py-1.5 rounded-lg text-xs font-medium text-mute hover:text-ink">2. Manual Review Queue <span id="queue-badge" class="ml-1 px-1.5 py-0.2 rounded-full bg-warn/20 text-warn text-[10px]">0</span></button>
        <button onclick="switchTab('batch')" id="tab-btn-batch" class="tab-btn px-3 py-1.5 rounded-lg text-xs font-medium text-mute hover:text-ink">3. Batch Scoring</button>
        <button onclick="switchTab('audit')" id="tab-btn-audit" class="tab-btn px-3 py-1.5 rounded-lg text-xs font-medium text-mute hover:text-ink">4. Audit & Fairness</button>
      </nav>

      <div class="flex items-center gap-3">
        <div class="text-right">
          <p id="user-display-name" class="text-xs font-semibold text-ink"></p>
          <p id="user-display-role" class="text-[10px] font-mono text-brand2"></p>
        </div>
        <button onclick="doLogout()" class="text-xs text-mute hover:text-bad border border-border rounded-lg px-2.5 py-1.5">Logout</button>
      </div>
    </header>

    <main class="p-6 md:p-8 max-w-7xl mx-auto">

      <!-- TAB 1: UNDERWRITE / LOOKUP -->
      <section id="tab-underwrite" class="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div class="lg:col-span-2 card rounded-2xl shadow-card p-6 space-y-5 h-fit">
          <div class="flex items-center justify-between">
            <label class="text-[11px] font-semibold text-mute uppercase tracking-wider">Applicant Preset</label>
            <div class="flex items-center gap-2">
              <span class="text-[11px] text-mute">Consent</span>
              <input type="checkbox" id="input-consent" checked class="w-3.5 h-3.5 accent-brand rounded">
            </div>
          </div>
          <select id="applicant-select" onchange="loadApplicantData()" class="field w-full rounded-lg p-2.5 text-sm font-medium">
            {% for id, profile in profiles.items() %}
              <option value="{{ id }}">{{ profile.name }}</option>
            {% endfor %}
          </select>

          <!-- Live MCP Lookup Bar -->
          <div class="pt-3 border-t border-border">
            <label class="text-[11px] text-mute font-medium">Lookup SK_ID_CURR in Home Credit CSV (via MCP)</label>
            <div class="flex gap-2 mt-1">
              <input id="input-id" class="field flex-1 rounded-lg p-2.5 text-xs font-mono" placeholder="e.g. 100001">
              <button onclick="fetchFromMcp()" class="px-3 py-2 rounded-lg bg-panel2 border border-border hover:border-brand text-xs font-medium text-brand2">
                Fetch MCP
              </button>
            </div>
            <p id="mcp-lookup-msg" class="text-[11px] text-mute mt-1"></p>
          </div>

          <div class="grid grid-cols-2 gap-3 pt-3 border-t border-border">
            <div>
              <label class="text-[11px] text-mute font-medium">Annual Income</label>
              <input type="number" id="input-income" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Credit Amount</label>
              <input type="number" id="input-credit" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Loan Annuity</label>
              <input type="number" id="input-annuity" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Goods Price</label>
              <input type="number" id="input-goods" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Days Employed</label>
              <input type="number" id="input-days-employed" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Income Type</label>
              <select id="input-income-type" class="field w-full rounded-lg p-2.5 text-xs mt-1">
                <option>Working</option><option>Commercial associate</option><option>Pensioner</option><option>State servant</option>
              </select>
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Education</label>
              <select id="input-education" class="field w-full rounded-lg p-2.5 text-xs mt-1">
                <option>Higher education</option><option>Secondary / secondary special</option><option>Incomplete higher</option><option>Lower secondary</option><option>Academic degree</option>
              </select>
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Housing</label>
              <select id="input-housing" class="field w-full rounded-lg p-2.5 text-xs mt-1">
                <option>House / apartment</option><option>Rented apartment</option><option>With parents</option><option>Municipal apartment</option>
              </select>
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Own Car / Realty</label>
              <div class="grid grid-cols-2 gap-2 mt-1">
                <select id="input-car" class="field rounded-lg p-2 text-xs"><option value="N">Car: N</option><option value="Y">Car: Y</option></select>
                <select id="input-realty" class="field rounded-lg p-2 text-xs"><option value="Y">Realty: Y</option><option value="N">Realty: N</option></select>
              </div>
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Children / Family</label>
              <div class="grid grid-cols-2 gap-2 mt-1">
                <input type="number" id="input-children" class="field rounded-lg p-2 text-xs" placeholder="Kids">
                <input type="number" id="input-family" class="field rounded-lg p-2 text-xs" placeholder="Fam">
              </div>
            </div>
          </div>

          <button onclick="runUnderwriting()" id="submit-btn" class="w-full bg-gradient-to-r from-brand to-brand2 hover:opacity-90 text-white font-semibold py-3 rounded-xl text-sm flex items-center justify-center gap-2">
            <span id="submit-label">Evaluate Home Credit Application</span>
          </button>
        </div>

        <div class="lg:col-span-3 space-y-6" id="output-decision">
          <div class="card rounded-2xl p-10 text-center text-mute text-sm shadow-card">
            Fetch any <span class="font-mono text-ink">SK_ID_CURR</span> via MCP or edit applicant fields, then click Evaluate.
          </div>
        </div>
      </section>

      <!-- TAB 2: MANUAL REVIEW QUEUE -->
      <section id="tab-review" class="hidden space-y-6">
        <div class="card rounded-2xl p-6 shadow-card flex justify-between items-center">
          <div>
            <h2 class="text-base font-semibold">Human-in-the-Loop Manual Review Queue</h2>
            <p class="text-xs text-mute">Applications flagged by Policy Review or Conditional Scoring. Senior Underwriters & Risk Admins can issue final overrides.</p>
          </div>
          <button onclick="loadReviewQueue()" class="px-3 py-1.5 rounded-lg bg-panel2 border border-border text-xs hover:border-brand">Refresh Queue</button>
        </div>
        <div id="review-queue-list" class="space-y-4"></div>
      </section>

      <!-- TAB 3: BATCH CSV SCORING -->
      <section id="tab-batch" class="hidden space-y-6">
        <div class="card rounded-2xl p-6 shadow-card space-y-4">
          <div class="flex flex-wrap justify-between items-center gap-4">
            <div>
              <h2 class="text-base font-semibold">Batch Portfolio Underwriting (CSV)</h2>
              <p class="text-xs text-mute">Upload a Home Credit CSV (e.g., slice of <span class="font-mono">application_test.csv</span>, up to 500 rows) for vectorized XGBoost + Isolation Forest scoring.</p>
            </div>
            <div class="flex items-center gap-3">
              <input type="file" id="batch-file" accept=".csv" class="text-xs text-mute file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-brand file:text-white file:text-xs file:font-semibold">
              <button onclick="runBatchScoring()" id="batch-btn" class="px-4 py-2 rounded-xl bg-gradient-to-r from-brand to-brand2 text-white text-xs font-semibold">Run Batch</button>
            </div>
          </div>
          <div id="batch-output"></div>
        </div>
      </section>

      <!-- TAB 4: AUDIT & FAIRNESS ANALYTICS -->
      <section id="tab-audit" class="hidden space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div class="card rounded-2xl p-6 shadow-card space-y-3">
            <h2 class="text-base font-semibold">Fairness & Bias Audit (Home Credit)</h2>
            <p class="text-xs text-mute">Evaluates demographic parity across <span class="font-mono">application_test.csv</span>. Restricted to <strong>Risk Admin</strong>.</p>
            <button onclick="runFairnessAudit()" id="fairness-btn" class="px-4 py-2 rounded-xl bg-brand text-white text-xs font-semibold">Run Fairness Audit</button>
            <pre id="fairness-output" class="text-xs font-mono bg-panel2 border border-border rounded-xl p-4 overflow-x-auto text-ink/90 max-h-72">Click "Run Fairness Audit" to evaluate bias metrics.</pre>
          </div>

          <div class="card rounded-2xl p-6 shadow-card space-y-3">
            <h2 class="text-base font-semibold">Model Governance & Retraining</h2>
            <p class="text-xs text-mute">Re-trains XGBoost, Isolation Forest & SHAP artifacts and updates HMAC signatures. Restricted to <strong>Risk Admin</strong>.</p>
            <button onclick="triggerRetrain()" id="retrain-btn" class="px-4 py-2 rounded-xl bg-warn text-canvas text-xs font-semibold">Retrain & Re-Sign Model</button>
            <pre id="retrain-output" class="text-xs font-mono bg-panel2 border border-border rounded-xl p-4 overflow-x-auto text-ink/90 max-h-72">Model artifact status: Active & HMAC-verified.</pre>
          </div>
        </div>

        <div class="card rounded-2xl p-6 shadow-card space-y-4">
          <div class="flex justify-between items-center">
            <h2 class="text-base font-semibold">Immutable Decision & Override Audit Trail</h2>
            <button onclick="loadAuditHistory()" class="px-3 py-1.5 rounded-lg bg-panel2 border border-border text-xs">Refresh Log</button>
          </div>
          <div id="audit-table-wrap" class="overflow-x-auto"></div>
        </div>
      </section>

    </main>
  </div>

<script>
  const profiles = {{ profiles | tojson }};
  const API_BASE = 'http://127.0.0.1:8000';
  let authToken = localStorage.getItem('uw_jwt') || '';
  let currentUser = JSON.parse(localStorage.getItem('uw_user') || 'null');

  function fillDemoUser() {
    const r = document.getElementById('quick-role').value;
    document.getElementById('login-user').value = r;
    document.getElementById('login-pass').value = r + '123';
  }

  function authHeaders(extra = {}) {
    return Object.assign({ 'Authorization': 'Bearer ' + authToken }, extra);
  }

  async function doLogin() {
    const username = document.getElementById('login-user').value.trim();
    const password = document.getElementById('login-pass').value;
    const errBox = document.getElementById('login-error');
    errBox.classList.add('hidden');

    try {
      const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });
      const data = await res.json();
      if (!res.ok) {
        errBox.innerText = data.detail || 'Login failed';
        errBox.classList.remove('hidden');
        return;
      }
      authToken = data.access_token;
      currentUser = data;
      localStorage.setItem('uw_jwt', authToken);
      localStorage.setItem('uw_user', JSON.stringify(data));
      enterApp();
    } catch (e) {
      errBox.innerText = 'Cannot reach FastAPI backend at 127.0.0.1:8000';
      errBox.classList.remove('hidden');
    }
  }

  function doLogout() {
    authToken = '';
    currentUser = null;
    localStorage.removeItem('uw_jwt');
    localStorage.removeItem('uw_user');
    document.getElementById('app-shell').classList.add('hidden');
    document.getElementById('login-screen').classList.remove('hidden');
  }

  function enterApp() {
    document.getElementById('login-screen').classList.add('hidden');
    document.getElementById('app-shell').classList.remove('hidden');
    document.getElementById('user-display-name').innerText = currentUser.full_name;
    document.getElementById('user-display-role').innerText = currentUser.role;

    const perms = new Set(currentUser.permissions || []);
    document.getElementById('fairness-btn').disabled = !perms.has('fairness_audit');
    document.getElementById('retrain-btn').disabled = !perms.has('retrain');
    if (!perms.has('fairness_audit')) document.getElementById('fairness-btn').classList.add('opacity-40', 'cursor-not-allowed');
    if (!perms.has('retrain')) document.getElementById('retrain-btn').classList.add('opacity-40', 'cursor-not-allowed');

    loadApplicantData();
    loadReviewQueue();
  }

  function switchTab(name) {
    ['underwrite', 'review', 'batch', 'audit'].forEach(t => {
      document.getElementById('tab-' + t).classList.add('hidden');
      const btn = document.getElementById('tab-btn-' + t);
      btn.classList.remove('bg-brand', 'text-white');
      btn.classList.add('text-mute');
    });
    document.getElementById('tab-' + name).classList.remove('hidden');
    const active = document.getElementById('tab-btn-' + name);
    active.classList.add('bg-brand', 'text-white');
    active.classList.remove('text-mute');

    if (name === 'review') loadReviewQueue();
    if (name === 'audit') loadAuditHistory();
  }

  function loadApplicantData() {
    const a = profiles[document.getElementById('applicant-select').value];
    document.getElementById('input-id').value = a.applicant_id;
    document.getElementById('input-consent').checked = a.consent_given;
    document.getElementById('input-income').value = a.AMT_INCOME_TOTAL;
    document.getElementById('input-credit').value = a.AMT_CREDIT;
    document.getElementById('input-annuity').value = a.AMT_ANNUITY;
    document.getElementById('input-goods').value = a.AMT_GOODS_PRICE;
    document.getElementById('input-days-employed').value = a.DAYS_EMPLOYED;
    document.getElementById('input-children').value = a.CNT_CHILDREN;
    document.getElementById('input-family').value = a.CNT_FAM_MEMBERS;
    document.getElementById('input-income-type').value = a.NAME_INCOME_TYPE;
    document.getElementById('input-education').value = a.NAME_EDUCATION_TYPE;
    document.getElementById('input-housing').value = a.NAME_HOUSING_TYPE;
    document.getElementById('input-car').value = a.FLAG_OWN_CAR;
    document.getElementById('input-realty').value = a.FLAG_OWN_REALTY;
  }

  async function fetchFromMcp() {
    const id = document.getElementById('input-id').value.trim();
    const msg = document.getElementById('mcp-lookup-msg');
    msg.innerText = 'Fetching from MCP server...';
    try {
      const res = await fetch(`${API_BASE}/api/v1/mcp-applicant/${encodeURIComponent(id)}`, { headers: authHeaders() });
      const data = await res.json();
      if (!res.ok || !data.result || !data.result.success) {
        msg.innerText = (data.result && data.result.message) || data.detail || 'Not found in CSV.';
        return;
      }
      const app = data.result.applicant;
      if (app.AMT_INCOME_TOTAL != null) document.getElementById('input-income').value = app.AMT_INCOME_TOTAL;
      if (app.AMT_CREDIT != null) document.getElementById('input-credit').value = app.AMT_CREDIT;
      if (app.AMT_ANNUITY != null) document.getElementById('input-annuity').value = app.AMT_ANNUITY;
      if (app.AMT_GOODS_PRICE != null) document.getElementById('input-goods').value = app.AMT_GOODS_PRICE;
      if (app.DAYS_EMPLOYED != null) document.getElementById('input-days-employed').value = app.DAYS_EMPLOYED;
      if (app.CNT_CHILDREN != null) document.getElementById('input-children').value = app.CNT_CHILDREN;
      if (app.CNT_FAM_MEMBERS != null) document.getElementById('input-family').value = app.CNT_FAM_MEMBERS;
      if (app.FLAG_OWN_CAR) document.getElementById('input-car').value = app.FLAG_OWN_CAR;
      if (app.FLAG_OWN_REALTY) document.getElementById('input-realty').value = app.FLAG_OWN_REALTY;
      msg.innerText = `Loaded SK_ID_CURR ${id} from Home Credit dataset via MCP.`;
    } catch (e) {
      msg.innerText = 'MCP lookup error: ' + e.message;
    }
  }

  function decisionBadge(decision) {
    const map = {
      APPROVED: 'bg-good/15 text-good border-good/30',
      CONDITIONAL_APPROVAL: 'bg-warn/15 text-warn border-warn/30',
      DECLINED: 'bg-bad/15 text-bad border-bad/30',
      FLAGGED_FOR_MANUAL_REVIEW: 'bg-warn/15 text-warn border-warn/30',
      REJECTED_NON_COMPLIANT: 'bg-bad/15 text-bad border-bad/30'
    };
    return map[decision] || 'bg-mute/15 text-mute border-mute/30';
  }

  function gauge(score) {
    const c = score >= 60 ? '#22C77A' : (score >= 45 ? '#F5A524' : '#F0505A');
    const deg = (Math.max(0, Math.min(100, score)) / 100) * 360;
    return `
      <div class="relative w-24 h-24 shrink-0">
        <div class="w-24 h-24 rounded-full" style="background: conic-gradient(${c} ${deg}deg, #1A2133 0deg);"></div>
        <div class="absolute inset-1.5 rounded-full bg-panel flex flex-col items-center justify-center">
          <span class="text-lg font-bold" style="color:${c}">${score}</span>
          <span class="text-[9px] text-mute">/ 100</span>
        </div>
      </div>`;
  }

  function shapBars(drivers) {
    const maxAbs = Math.max(...drivers.map(d => Math.abs(d.shap_value)), 0.0001);
    return drivers.map(d => {
      const pct = Math.min(100, (Math.abs(d.shap_value) / maxAbs) * 100);
      const color = d.shap_value >= 0 ? '#F0505A' : '#22C77A';
      return `
        <div class="mb-2.5">
          <div class="flex justify-between text-xs mb-1">
            <span class="text-ink/90">${d.feature.replaceAll('_',' ')}</span>
            <span class="font-mono" style="color:${color}">${d.shap_value > 0 ? '+' : ''}${d.shap_value.toFixed(4)}</span>
          </div>
          <div class="bar-track h-1.5 rounded-full w-full overflow-hidden">
            <div class="h-full rounded-full" style="width:${pct}%; background:${color}"></div>
          </div>
        </div>`;
    }).join('');
  }

  async function runUnderwriting() {
    const btn = document.getElementById('submit-btn');
    const label = document.getElementById('submit-label');
    btn.disabled = true;
    label.innerHTML = '<span class="inline-block w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full spin"></span> Evaluating…';

    const payload = {
      applicant_id: document.getElementById('input-id').value.trim(),
      consent_given: document.getElementById('input-consent').checked,
      AMT_INCOME_TOTAL: parseFloat(document.getElementById('input-income').value),
      AMT_CREDIT: parseFloat(document.getElementById('input-credit').value),
      AMT_ANNUITY: parseFloat(document.getElementById('input-annuity').value),
      AMT_GOODS_PRICE: parseFloat(document.getElementById('input-goods').value),
      DAYS_EMPLOYED: parseFloat(document.getElementById('input-days-employed').value),
      CNT_CHILDREN: parseFloat(document.getElementById('input-children').value || 0),
      CNT_FAM_MEMBERS: parseFloat(document.getElementById('input-family').value || 1),
      NAME_INCOME_TYPE: document.getElementById('input-income-type').value,
      NAME_EDUCATION_TYPE: document.getElementById('input-education').value,
      NAME_HOUSING_TYPE: document.getElementById('input-housing').value,
      FLAG_OWN_CAR: document.getElementById('input-car').value,
      FLAG_OWN_REALTY: document.getElementById('input-realty').value
    };

    const out = document.getElementById('output-decision');
    try {
      const res = await fetch(`${API_BASE}/api/v1/underwrite`, {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(payload)
      });
      const d = await res.json();
      if (!res.ok) {
        out.innerHTML = `<div class="card rounded-2xl p-6 border-bad/40 text-bad text-xs font-mono">${d.detail || JSON.stringify(d)}</div>`;
        return;
      }
      loadReviewQueue();
      const badge = decisionBadge(d.decision);
      const selfCheck = d.self_check || { self_check_passed: true, issues: [] };
      const mcpStatus = (d.mcp && d.mcp.status) || 'UNKNOWN';

      out.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 fade-in">
          <div class="card rounded-2xl p-6 shadow-card md:col-span-2 flex items-center justify-between">
            <div class="flex items-center gap-5">
              ${gauge(d.credit_risk_score)}
              <div>
                <div class="flex items-center gap-2 mb-1">
                  <p class="text-[11px] text-mute uppercase tracking-wider">Decision Outcome</p>
                  <span class="text-[10px] font-mono px-2 py-0.5 rounded bg-panel2 border border-border text-mute">MCP: ${mcpStatus}</span>
                </div>
                <span class="inline-block px-3 py-1 rounded-full text-sm font-semibold border ${badge}">${d.decision.replaceAll('_',' ')}</span>
                <p class="text-xs text-mute mt-2 max-w-md">${d.decision_reason}</p>
              </div>
            </div>
            <div class="text-right hidden sm:block">
              <p class="text-[11px] text-mute uppercase tracking-wider">Risk Tier</p>
              <p class="text-sm font-semibold text-ink mt-1">${d.risk_tier.replaceAll('_',' ')}</p>
              <p class="text-[11px] text-mute mt-2">PD: ${(d.default_probability*100).toFixed(1)}%</p>
            </div>
          </div>

          <div class="card rounded-2xl p-5 shadow-card">
            <p class="text-[11px] font-semibold text-mute uppercase tracking-wider mb-3">Fraud & Anomaly Signal</p>
            <p class="text-base font-semibold ${d.fraud_assessment.fraud_risk_level === 'LOW' ? 'text-good' : 'text-bad'}">${d.fraud_assessment.fraud_risk_level}</p>
            <p class="text-xs text-mute mt-1 font-mono">ML anomaly score: ${d.fraud_assessment.ml_anomaly_score}</p>
          </div>

          <div class="card rounded-2xl p-5 shadow-card">
            <p class="text-[11px] font-semibold text-mute uppercase tracking-wider mb-3">Self-Check (Policy Review)</p>
            <p class="text-base font-semibold ${selfCheck.self_check_passed ? 'text-good' : 'text-warn'}">${selfCheck.self_check_passed ? 'Passed' : 'Flagged'}</p>
            ${selfCheck.issues.length ? `<ul class="text-xs text-mute mt-2 space-y-1 list-disc list-inside">${selfCheck.issues.map(i=>`<li>${i}</li>`).join('')}</ul>`
              : `<p class="text-xs text-mute mt-1">All compliance & fairness checks passed.</p>`}
          </div>

          <div class="card rounded-2xl p-5 shadow-card md:col-span-2">
            <p class="text-[11px] font-semibold text-mute uppercase tracking-wider mb-3">Top SHAP Drivers</p>
            ${shapBars(d.top_shap_drivers)}
          </div>

          <div class="card rounded-2xl p-5 shadow-card md:col-span-2">
            <p class="text-[11px] font-semibold text-mute uppercase tracking-wider mb-2">Generated Decision Explanation</p>
            <p class="text-xs font-mono text-ink/90 leading-relaxed whitespace-pre-line">${d.explanation_letter}</p>
          </div>
        </div>`;
    } finally {
      btn.disabled = false;
      label.innerText = 'Evaluate Home Credit Application';
    }
  }

  async function loadReviewQueue() {
    try {
      const res = await fetch(`${API_BASE}/api/v1/review-queue`, { headers: authHeaders() });
      if (!res.ok) return;
      const data = await res.json();
      document.getElementById('queue-badge').innerText = data.count;
      const canOverride = (currentUser.permissions || []).includes('override_review');
      const wrap = document.getElementById('review-queue-list');
      if (!data.items.length) {
        wrap.innerHTML = `<div class="card rounded-2xl p-8 text-center text-mute text-xs">No applications pending manual review.</div>`;
        return;
      }
      wrap.innerHTML = data.items.map(item => `
        <div class="card rounded-2xl p-5 shadow-card flex flex-wrap justify-between items-center gap-4">
          <div class="space-y-1">
            <div class="flex items-center gap-2">
              <span class="font-mono text-sm font-bold text-ink">${item.applicant_id}</span>
              <span class="px-2.5 py-0.5 rounded-full text-xs border ${decisionBadge(item.decision)}">${item.decision}</span>
              <span class="text-xs text-mute">Score: <strong class="text-ink">${item.credit_risk_score}</strong></span>
            </div>
            <p class="text-xs text-mute">${item.decision_reason}</p>
          </div>
          ${canOverride ? `
            <div class="flex items-center gap-2">
              <input id="note-${item.applicant_id}" placeholder="Underwriter audit note..." class="field rounded-lg px-3 py-1.5 text-xs w-56">
              <button onclick="submitOverride('${item.applicant_id}','APPROVED')" class="px-3 py-1.5 rounded-lg bg-good/20 text-good border border-good/40 text-xs font-semibold">Approve</button>
              <button onclick="submitOverride('${item.applicant_id}','DECLINED')" class="px-3 py-1.5 rounded-lg bg-bad/20 text-bad border border-bad/40 text-xs font-semibold">Decline</button>
            </div>` : `<span class="text-[11px] text-warn font-mono">Senior Underwriter role required to override</span>`}
        </div>`).join('');
    } catch (_) {}
  }

  async function submitOverride(applicantId, decision) {
    const notes = document.getElementById('note-' + applicantId).value.trim() || 'Reviewed and verified by senior underwriter.';
    const res = await fetch(`${API_BASE}/api/v1/review-queue/${encodeURIComponent(applicantId)}/override`, {
      method: 'POST',
      headers: authHeaders({ 'Content-Type': 'application/json' }),
      body: JSON.stringify({ override_decision: decision, reviewer_notes: notes })
    });
    if (res.ok) {
      loadReviewQueue();
      loadAuditHistory();
    } else {
      const err = await res.json();
      alert(err.detail || 'Override failed');
    }
  }

  async function runBatchScoring() {
    const fileInput = document.getElementById('batch-file');
    const out = document.getElementById('batch-output');
    if (!fileInput.files.length) {
      out.innerHTML = `<p class="text-xs text-warn">Select a CSV file first.</p>`;
      return;
    }
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    out.innerHTML = `<p class="text-xs text-mute">Scoring batch...</p>`;

    const res = await fetch(`${API_BASE}/api/v1/underwrite/batch`, {
      method: 'POST',
      headers: authHeaders(),
      body: formData
    });
    const data = await res.json();
    if (!res.ok) {
      out.innerHTML = `<p class="text-xs text-bad font-mono">${data.detail}</p>`;
      return;
    }
    const s = data.summary;
    out.innerHTML = `
      <div class="grid grid-cols-2 sm:grid-cols-5 gap-3 my-4">
        <div class="bg-panel2 border border-border rounded-xl p-3"><p class="text-[10px] text-mute">TOTAL</p><p class="text-lg font-bold">${s.total_processed}</p></div>
        <div class="bg-panel2 border border-border rounded-xl p-3"><p class="text-[10px] text-good">APPROVED</p><p class="text-lg font-bold text-good">${s.approved}</p></div>
        <div class="bg-panel2 border border-border rounded-xl p-3"><p class="text-[10px] text-warn">CONDITIONAL</p><p class="text-lg font-bold text-warn">${s.conditional}</p></div>
        <div class="bg-panel2 border border-border rounded-xl p-3"><p class="text-[10px] text-warn">MANUAL REVIEW</p><p class="text-lg font-bold text-warn">${s.manual_review}</p></div>
        <div class="bg-panel2 border border-border rounded-xl p-3"><p class="text-[10px] text-bad">DECLINED</p><p class="text-lg font-bold text-bad">${s.declined}</p></div>
      </div>
      <div class="overflow-x-auto max-h-80">
        <table class="w-full text-left text-xs">
          <thead class="text-mute border-b border-border"><tr><th class="py-2">Applicant ID</th><th>Score</th><th>Default Prob</th><th>Anomaly</th><th>Decision</th></tr></thead>
          <tbody class="divide-y divide-border/50">
            ${data.results.slice(0, 100).map(r => `
              <tr>
                <td class="py-2 font-mono">${r.applicant_id}</td>
                <td>${r.credit_risk_score}</td>
                <td>${(r.default_probability*100).toFixed(1)}%</td>
                <td>${r.is_anomalous ? 'YES' : 'NO'} (${r.anomaly_score})</td>
                <td><span class="px-2 py-0.5 rounded-full text-[10px] border ${decisionBadge(r.decision)}">${r.decision}</span></td>
              </tr>`).join('')}
          </tbody>
        </table>
      </div>`;
  }

  async function runFairnessAudit() {
    const out = document.getElementById('fairness-output');
    out.innerText = 'Running fairness audit across Home Credit records...';
    const res = await fetch(`${API_BASE}/api/v1/fairness-audit`, { headers: authHeaders() });
    const data = await res.json();
    out.innerText = JSON.stringify(data, null, 2);
  }

  async function triggerRetrain() {
    const out = document.getElementById('retrain-output');
    out.innerText = 'Retraining XGBoost + Isolation Forest + SHAP on application_train.csv...';
    const res = await fetch(`${API_BASE}/api/v1/admin/retrain`, { method: 'POST', headers: authHeaders() });
    const data = await res.json();
    out.innerText = res.ok ? (data.output || 'Retraining succeeded.') : (data.detail || 'Retrain failed.');
  }

  async function loadAuditHistory() {
    const res = await fetch(`${API_BASE}/api/v1/audit-history`, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    const wrap = document.getElementById('audit-table-wrap');
    if (!data.items.length) {
      wrap.innerHTML = `<p class="text-xs text-mute">No decisions logged in this session yet.</p>`;
      return;
    }
    wrap.innerHTML = `
      <table class="w-full text-left text-xs">
        <thead class="text-mute border-b border-border">
          <tr><th class="py-2">Timestamp</th><th>Applicant</th><th>Officer</th><th>Score</th><th>Decision</th><th>Override By</th></tr>
        </thead>
        <tbody class="divide-y divide-border/50">
          ${data.items.map(i => `
            <tr>
              <td class="py-2 font-mono text-mute">${i.timestamp}</td>
              <td class="font-mono">${i.applicant_id}</td>
              <td>${i.submitted_by}</td>
              <td>${i.credit_risk_score}</td>
              <td><span class="px-2 py-0.5 rounded-full text-[10px] border ${decisionBadge(i.decision)}">${i.decision}</span></td>
              <td class="font-mono text-brand2">${i.override_by || '—'}</td>
            </tr>`).join('')}
        </tbody>
      </table>`;
  }

  window.onload = () => {
    if (authToken && currentUser) {
      enterApp();
    }
  };
</script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, profiles=APPLICANT_PROFILES)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)