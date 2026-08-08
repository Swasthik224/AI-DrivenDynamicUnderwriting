"""
dashboard_flask.py - Professional Live Dynamic Underwriting UI
"""
from flask import Flask, render_template_string

app = Flask(__name__)

APPLICANT_PROFILES = {
    "APP_CUSTOM": {
        "applicant_id": "APP_CUSTOM", "name": "Custom Live Applicant",
        "gender": "Female", "age_group": "25_50", "consent_given": True,
        "traditional_score": 650.0, "monthly_income_inr": 50000.0, "debt_to_income_ratio": 0.30,
        "num_existing_loans": 1, "upi_monthly_tx_volume": 50, "bnpl_repayment_rate": 0.85,
        "utility_pay_punctuality": 0.80, "telecom_recharge_regularity": 0.90,
        "ecommerce_monthly_spend": 10000.0, "ecommerce_return_rate": 0.05,
        "gig_income_stability_index": 0.70, "digital_footprint_consistency": 0.85,
        "device_change_frequency": 1, "mobile_wallet_tx_freq": 20
    },
    "APP_1042": {
        "applicant_id": "APP_1042", "name": "Priya Sharma — Gig Worker",
        "gender": "Female", "age_group": "25_50", "consent_given": True,
        "traditional_score": 620.0, "monthly_income_inr": 45000.0, "debt_to_income_ratio": 0.35,
        "num_existing_loans": 1, "upi_monthly_tx_volume": 85, "bnpl_repayment_rate": 0.98,
        "utility_pay_punctuality": 0.92, "telecom_recharge_regularity": 0.95,
        "ecommerce_monthly_spend": 8000.0, "ecommerce_return_rate": 0.04,
        "gig_income_stability_index": 0.88, "digital_footprint_consistency": 0.91,
        "device_change_frequency": 1, "mobile_wallet_tx_freq": 35
    },
    "APP_2091": {
        "applicant_id": "APP_2091", "name": "Rahul Verma — Salaried",
        "gender": "Male", "age_group": "25_50", "consent_given": True,
        "traditional_score": 750.0, "monthly_income_inr": 120000.0, "debt_to_income_ratio": 0.20,
        "num_existing_loans": 2, "upi_monthly_tx_volume": 30, "bnpl_repayment_rate": 0.70,
        "utility_pay_punctuality": 0.85, "telecom_recharge_regularity": 0.80,
        "ecommerce_monthly_spend": 25000.0, "ecommerce_return_rate": 0.12,
        "gig_income_stability_index": 0.30, "digital_footprint_consistency": 0.95,
        "device_change_frequency": 2, "mobile_wallet_tx_freq": 12
    },
    "APP_3310": {
        "applicant_id": "APP_3310", "name": "Suspicious Pattern — Test Case",
        "gender": "Male", "age_group": "Under_25", "consent_given": True,
        "traditional_score": 590.0, "monthly_income_inr": 30000.0, "debt_to_income_ratio": 0.55,
        "num_existing_loans": 4, "upi_monthly_tx_volume": 5, "bnpl_repayment_rate": 0.40,
        "utility_pay_punctuality": 0.35, "telecom_recharge_regularity": 0.30,
        "ecommerce_monthly_spend": 40000.0, "ecommerce_return_rate": 0.65,
        "gig_income_stability_index": 0.20, "digital_footprint_consistency": 0.25,
        "device_change_frequency": 6, "mobile_wallet_tx_freq": 2
    }
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Alt-Data Underwriting Console</title>
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
  input[type=range] { -webkit-appearance: none; height: 4px; border-radius: 999px; background: #232B3D; }
  input[type=range]::-webkit-slider-thumb {
    -webkit-appearance: none; width: 16px; height: 16px; border-radius: 999px;
    background: #818CF8; cursor: pointer; border: 3px solid #0B0F19; box-shadow: 0 0 0 1px #818CF8;
  }
  .field { background: #0F1420; border: 1px solid #232B3D; color: #E7EAF0; }
  .field:focus { outline: none; border-color: #6366F1; box-shadow: 0 0 0 3px rgba(99,102,241,0.15); }
  ::-webkit-scrollbar { width: 8px; } ::-webkit-scrollbar-thumb { background: #232B3D; border-radius: 8px; }
  .bar-track { background: #1A2133; }
  .spin { animation: spin 0.8s linear infinite; } @keyframes spin { to { transform: rotate(360deg); } }
  .fade-in { animation: fadeIn 0.35s ease both; } @keyframes fadeIn { from { opacity:0; transform: translateY(4px);} to {opacity:1; transform:none;} }
</style>
</head>
<body class="bg-canvas text-ink font-sans min-h-screen">

  <header class="border-b border-border/80 px-8 py-5 flex justify-between items-center sticky top-0 bg-canvas/90 backdrop-blur z-10">
    <div class="flex items-center gap-3">
      <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-brand to-brand2 flex items-center justify-center font-bold text-white text-sm">AI</div>
      <div>
        <h1 class="text-[15px] font-semibold tracking-tight text-ink">Alt-Data Underwriting Console</h1>
        <p class="text-[11px] text-mute">Multi-agent risk pipeline · dynamic behavioral scoring</p>
      </div>
    </div>
    <div class="flex items-center gap-3">
      <div class="flex items-center gap-2 bg-panel2 border border-border rounded-full pl-3 pr-1 py-1">
        <span class="text-[11px] text-mute font-medium">DPDP Consent</span>
        <input type="checkbox" id="input-consent" checked class="w-3.5 h-3.5 accent-brand rounded">
      </div>
      <span class="text-[11px] text-mute font-mono hidden sm:inline">v1.2 · demo</span>
    </div>
  </header>

  <main class="p-6 md:p-8 max-w-7xl mx-auto">
    <div class="grid grid-cols-1 lg:grid-cols-5 gap-6">

      <!-- LEFT: Inputs -->
      <div class="lg:col-span-2 card rounded-2xl shadow-card p-6 space-y-6 h-fit">
        <div>
          <label class="text-[11px] font-semibold text-mute uppercase tracking-wider">Applicant Profile</label>
          <select id="applicant-select" onchange="loadApplicantData()"
            class="field w-full rounded-lg p-2.5 text-sm font-medium mt-1.5">
            {% for id, profile in profiles.items() %}
              <option value="{{ id }}">{{ profile.name }}</option>
            {% endfor %}
          </select>
        </div>

        <div class="grid grid-cols-2 gap-3 pt-4 border-t border-border">
          <div>
            <label class="text-[11px] text-mute font-medium">Applicant ID</label>
            <input id="input-id" class="field w-full rounded-lg p-2.5 text-xs font-mono mt-1">
          </div>
          <div>
            <label class="text-[11px] text-mute font-medium">Gender</label>
            <select id="input-gender" class="field w-full rounded-lg p-2.5 text-xs mt-1">
              <option>Female</option><option>Male</option><option>Non-Binary</option>
            </select>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-3">
          <div>
            <label class="text-[11px] text-mute font-medium">Bureau Score</label>
            <input type="number" id="input-trad-score" class="field w-full rounded-lg p-2.5 text-xs mt-1">
          </div>
          <div>
            <label class="text-[11px] text-mute font-medium">Income (₹/mo)</label>
            <input type="number" id="input-income" class="field w-full rounded-lg p-2.5 text-xs mt-1">
          </div>
          <div>
            <label class="text-[11px] text-mute font-medium">DTI Ratio</label>
            <input type="number" step="0.01" id="input-dti" class="field w-full rounded-lg p-2.5 text-xs mt-1">
          </div>
        </div>

        <div class="space-y-4 pt-4 border-t border-border">
          <p class="text-[11px] font-semibold text-mute uppercase tracking-wider">Alternative Digital Signals</p>

          {% for sid, label in [('utility','Utility Payment Punctuality'), ('bnpl','BNPL Repayment Rate'),
                                  ('telecom','Telecom Recharge Regularity'), ('gig','Gig Income Stability'),
                                  ('digital','Digital Footprint Consistency'), ('ecomret','E-commerce Return Rate')] %}
          <div>
            <div class="flex justify-between text-xs text-mute mb-1">
              <span>{{ label }}</span><span id="val-{{ sid }}" class="font-mono text-ink">0.80</span>
            </div>
            <input type="range" id="input-{{ sid }}" min="0" max="1" step="0.01" oninput="updateVal('{{ sid }}')" class="w-full">
          </div>
          {% endfor %}

          <div class="grid grid-cols-2 gap-3 pt-2">
            <div>
              <label class="text-[11px] text-mute font-medium">UPI Monthly Volume</label>
              <input type="number" id="input-upi" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Device Changes (90d)</label>
              <input type="number" id="input-device" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Existing Loans</label>
              <input type="number" id="input-loans" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            </div>
            <div>
              <label class="text-[11px] text-mute font-medium">Wallet Tx / mo</label>
              <input type="number" id="input-wallet" class="field w-full rounded-lg p-2.5 text-xs mt-1">
            </div>
          </div>
        </div>

        <button onclick="runUnderwriting()" id="submit-btn"
          class="w-full bg-gradient-to-r from-brand to-brand2 hover:opacity-90 transition text-white font-semibold py-3 rounded-xl text-sm flex items-center justify-center gap-2">
          <span id="submit-label">Evaluate Application</span>
        </button>
      </div>

      <!-- RIGHT: Output -->
      <div class="lg:col-span-3 space-y-6">
        <div id="output-decision">
          <div class="card rounded-2xl p-10 text-center text-mute text-sm shadow-card">
            Select a profile or edit fields, then run the evaluation to see the multi-agent decision.
          </div>
        </div>
      </div>

    </div>
  </main>

<script>
  const profiles = {{ profiles | tojson }};

  function updateVal(id) {
    document.getElementById('val-' + id).innerText =
      parseFloat(document.getElementById('input-' + id).value).toFixed(2);
  }

  function loadApplicantData() {
    const a = profiles[document.getElementById('applicant-select').value];
    document.getElementById('input-id').value = a.applicant_id;
    document.getElementById('input-gender').value = a.gender;
    document.getElementById('input-consent').checked = a.consent_given;
    document.getElementById('input-trad-score').value = a.traditional_score;
    document.getElementById('input-income').value = a.monthly_income_inr;
    document.getElementById('input-dti').value = a.debt_to_income_ratio;
    document.getElementById('input-upi').value = a.upi_monthly_tx_volume;
    document.getElementById('input-device').value = a.device_change_frequency;
    document.getElementById('input-loans').value = a.num_existing_loans;
    document.getElementById('input-wallet').value = a.mobile_wallet_tx_freq;

    const sliderMap = {
      utility: 'utility_pay_punctuality', bnpl: 'bnpl_repayment_rate',
      telecom: 'telecom_recharge_regularity', gig: 'gig_income_stability_index',
      digital: 'digital_footprint_consistency', ecomret: 'ecommerce_return_rate'
    };
    for (const [sid, key] of Object.entries(sliderMap)) {
      document.getElementById('input-' + sid).value = a[key];
      updateVal(sid);
    }
  }

  function scoreColor(score) {
    if (score >= 60) return '#22C77A';
    if (score >= 45) return '#F5A524';
    return '#F0505A';
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
    const c = scoreColor(score);
    const pct = Math.max(0, Math.min(100, score));
    const deg = (pct / 100) * 360;
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
      const positive = d.shap_value >= 0; // positive SHAP -> pushes toward default in this model
      const color = positive ? '#F0505A' : '#22C77A';
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
    label.innerHTML = '<span class="inline-block w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full spin"></span> Running agents…';

    const payload = {
      applicant_id: document.getElementById('input-id').value,
      gender: document.getElementById('input-gender').value,
      age_group: "25_50",
      consent_given: document.getElementById('input-consent').checked,
      traditional_score: parseFloat(document.getElementById('input-trad-score').value),
      monthly_income_inr: parseFloat(document.getElementById('input-income').value),
      debt_to_income_ratio: parseFloat(document.getElementById('input-dti').value),
      num_existing_loans: parseInt(document.getElementById('input-loans').value || 0),
      upi_monthly_tx_volume: parseInt(document.getElementById('input-upi').value),
      bnpl_repayment_rate: parseFloat(document.getElementById('input-bnpl').value),
      utility_pay_punctuality: parseFloat(document.getElementById('input-utility').value),
      telecom_recharge_regularity: parseFloat(document.getElementById('input-telecom').value),
      ecommerce_monthly_spend: 10000.0,
      ecommerce_return_rate: parseFloat(document.getElementById('input-ecomret').value),
      gig_income_stability_index: parseFloat(document.getElementById('input-gig').value),
      digital_footprint_consistency: parseFloat(document.getElementById('input-digital').value),
      device_change_frequency: parseInt(document.getElementById('input-device').value),
      mobile_wallet_tx_freq: parseInt(document.getElementById('input-wallet').value || 0)
    };

    const out = document.getElementById('output-decision');

    try {
      const res = await fetch('http://localhost:8000/api/v1/underwrite', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        out.innerHTML = `
          <div class="card rounded-2xl p-6 border-bad/40 shadow-card fade-in">
            <p class="font-semibold text-bad text-sm mb-1">Blocked by Consent Agent</p>
            <p class="text-xs text-mute">${err.detail}</p>
          </div>`;
        return;
      }

      const d = await res.json();
      const badge = decisionBadge(d.decision);
      const selfCheck = d.self_check || { self_check_passed: true, issues: [] };

      out.innerHTML = `
        <div class="grid grid-cols-1 md:grid-cols-2 gap-6 fade-in">

          <div class="card rounded-2xl p-6 shadow-card md:col-span-2 flex items-center justify-between">
            <div class="flex items-center gap-5">
              ${gauge(d.credit_risk_score)}
              <div>
                <p class="text-[11px] text-mute uppercase tracking-wider mb-1">Decision Outcome</p>
                <span class="inline-block px-3 py-1 rounded-full text-sm font-semibold border ${badge}">${d.decision.replaceAll('_',' ')}</span>
                <p class="text-xs text-mute mt-2 max-w-xs">${d.decision_reason}</p>
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
            <p class="text-base font-semibold ${d.fraud_assessment.fraud_risk_level === 'LOW' ? 'text-good' : 'text-bad'}">
              ${d.fraud_assessment.fraud_risk_level}
            </p>
            <p class="text-xs text-mute mt-1 font-mono">ML anomaly score: ${d.fraud_assessment.ml_anomaly_score}</p>
            ${d.fraud_assessment.triggered_flags.length ? `
              <div class="mt-3 flex flex-wrap gap-1.5">
                ${d.fraud_assessment.triggered_flags.map(f => `<span class="text-[10px] bg-bad/10 text-bad border border-bad/30 rounded-full px-2 py-0.5">${f.replaceAll('_',' ')}</span>`).join('')}
              </div>` : ''}
          </div>

          <div class="card rounded-2xl p-5 shadow-card">
            <p class="text-[11px] font-semibold text-mute uppercase tracking-wider mb-3">Self-Check (Policy Review)</p>
            <p class="text-base font-semibold ${selfCheck.self_check_passed ? 'text-good' : 'text-warn'}">
              ${selfCheck.self_check_passed ? 'Passed' : 'Flagged'}
            </p>
            ${selfCheck.issues.length ? `<ul class="text-xs text-mute mt-2 space-y-1 list-disc list-inside">${selfCheck.issues.map(i=>`<li>${i}</li>`).join('')}</ul>`
              : `<p class="text-xs text-mute mt-1">Output consistent with policy and explainability requirements.</p>`}
          </div>

          <div class="card rounded-2xl p-5 shadow-card md:col-span-2">
            <p class="text-[11px] font-semibold text-mute uppercase tracking-wider mb-3">Top SHAP Drivers</p>
            ${shapBars(d.top_shap_drivers)}
          </div>

          <div class="card rounded-2xl p-5 shadow-card md:col-span-2">
            <p class="text-[11px] font-semibold text-mute uppercase tracking-wider mb-2">Generated Decision Explanation</p>
            <p class="text-xs font-mono text-ink/90 leading-relaxed">${d.explanation_letter}</p>
          </div>

        </div>`;
    } catch (e) {
      out.innerHTML = `<div class="card rounded-2xl p-6 shadow-card text-bad text-sm">Could not reach backend at localhost:8000. Is the FastAPI server running?</div>`;
    } finally {
      btn.disabled = false;
      label.innerText = 'Evaluate Application';
    }
  }

  window.onload = loadApplicantData;
</script>
</body>
</html>
"""

@app.route('/')
def home():
    return render_template_string(HTML_TEMPLATE, profiles=APPLICANT_PROFILES)

if __name__ == "__main__":
    app.run(port=5000, debug=True)