"""
dashboard_flask.py - Live Dynamic Underwriting UI with Custom Entry
"""
from flask import Flask, render_template_string
import json

app = Flask(__name__)

# Sample baseline profiles for quick testing
APPLICANT_PROFILES = {
    "APP_CUSTOM": {
        "applicant_id": "APP_CUSTOM",
        "name": "➕ Custom Live Applicant",
        "gender": "Female",
        "age_group": "25_50",
        "consent_given": True,
        "traditional_score": 650.0,
        "monthly_income_inr": 50000.0,
        "debt_to_income_ratio": 0.30,
        "upi_monthly_tx_volume": 50,
        "bnpl_repayment_rate": 0.85,
        "utility_pay_punctuality": 0.80,
        "telecom_recharge_regularity": 0.90,
        "ecommerce_monthly_spend": 10000.0,
        "ecommerce_return_rate": 0.05,
        "gig_income_stability_index": 0.70,
        "digital_footprint_consistency": 0.85,
        "device_change_frequency": 1
    },
    "APP_1042": {
        "applicant_id": "APP_1042",
        "name": "Priya Sharma (Gig Worker)",
        "gender": "Female",
        "age_group": "25_50",
        "consent_given": True,
        "traditional_score": 620.0,
        "monthly_income_inr": 45000.0,
        "debt_to_income_ratio": 0.35,
        "upi_monthly_tx_volume": 85,
        "bnpl_repayment_rate": 0.98,
        "utility_pay_punctuality": 0.92,
        "telecom_recharge_regularity": 0.95,
        "ecommerce_monthly_spend": 8000.0,
        "ecommerce_return_rate": 0.04,
        "gig_income_stability_index": 0.88,
        "digital_footprint_consistency": 0.91,
        "device_change_frequency": 1
    },
    "APP_2091": {
        "applicant_id": "APP_2091",
        "name": "Rahul Verma (Salaried)",
        "gender": "Male",
        "age_group": "25_50",
        "consent_given": True,
        "traditional_score": 750.0,
        "monthly_income_inr": 120000.0,
        "debt_to_income_ratio": 0.20,
        "upi_monthly_tx_volume": 30,
        "bnpl_repayment_rate": 0.70,
        "utility_pay_punctuality": 0.85,
        "telecom_recharge_regularity": 0.80,
        "ecommerce_monthly_spend": 25000.0,
        "ecommerce_return_rate": 0.12,
        "gig_income_stability_index": 0.30,
        "digital_footprint_consistency": 0.95,
        "device_change_frequency": 2
    }
}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Enterprise Live Underwriting Suite</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-900 text-slate-100 font-sans min-h-screen">
    <header class="bg-slate-800 border-b border-slate-700 px-8 py-4 flex justify-between items-center">
        <h1 class="text-xl font-bold text-emerald-400">⚡ AI Credit Agent Suite (Live Demo Mode)</h1>
        <div class="flex items-center gap-2">
            <span class="text-xs text-slate-400">DPDP Consent Status:</span>
            <input type="checkbox" id="input-consent" checked class="w-4 h-4 accent-emerald-500 rounded">
            <label for="input-consent" class="text-xs text-emerald-400 font-bold">Consented</label>
        </div>
    </header>

    <main class="p-8 max-w-7xl mx-auto">
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <!-- Left Panel: Form Controls -->
            <div class="bg-slate-800 p-6 rounded-xl border border-slate-700 space-y-4">
                <div>
                    <label class="text-xs text-slate-400 font-bold uppercase">Preset Selector or Live Custom Entry</label>
                    <select id="applicant-select" onchange="loadApplicantData()" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-emerald-400 font-bold mt-1">
                        {% for id, profile in profiles.items() %}
                            <option value="{{ id }}">{{ profile.name }}</option>
                        {% endfor %}
                    </select>
                </div>

                <div class="grid grid-cols-2 gap-4 pt-2 border-t border-slate-700">
                    <div>
                        <label class="text-xs text-slate-400">Applicant ID</label>
                        <input type="text" id="input-id" value="APP_LIVE_01" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs">
                    </div>
                    <div>
                        <label class="text-xs text-slate-400">Gender / Age Group</label>
                        <div class="flex gap-2">
                            <select id="input-gender" class="w-1/2 bg-slate-900 border border-slate-700 rounded p-2 text-xs">
                                <option value="Female">Female</option>
                                <option value="Male">Male</option>
                            </select>
                            <select id="input-age" class="w-1/2 bg-slate-900 border border-slate-700 rounded p-2 text-xs">
                                <option value="25_50">25-50</option>
                                <option value="<25">&lt;25</option>
                            </select>
                        </div>
                    </div>
                </div>

                <!-- Traditional Signals -->
                <div class="grid grid-cols-3 gap-3 pt-2 border-t border-slate-700">
                    <div>
                        <label class="text-xs text-slate-400">Bureau Score</label>
                        <input type="number" id="input-trad-score" value="650" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs">
                    </div>
                    <div>
                        <label class="text-xs text-slate-400">Income (INR)</label>
                        <input type="number" id="input-income" value="50000" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs">
                    </div>
                    <div>
                        <label class="text-xs text-slate-400">DTI Ratio</label>
                        <input type="number" step="0.01" id="input-dti" value="0.30" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs">
                    </div>
                </div>

                <!-- Alternative & Behavioral Signals -->
                <div class="space-y-3 pt-2 border-t border-slate-700">
                    <p class="text-xs font-bold text-slate-400 uppercase">Alternative Digital Footprint Signals</p>
                    
                    <div>
                        <div class="flex justify-between text-xs text-slate-400">
                            <span>Utility Payment Punctuality</span><span id="val-utility">0.80</span>
                        </div>
                        <input type="range" id="input-utility" min="0" max="1" step="0.05" oninput="updateVal('utility')" class="w-full accent-emerald-500">
                    </div>

                    <div>
                        <div class="flex justify-between text-xs text-slate-400">
                            <span>BNPL Repayment Rate</span><span id="val-bnpl">0.85</span>
                        </div>
                        <input type="range" id="input-bnpl" min="0" max="1" step="0.05" oninput="updateVal('bnpl')" class="w-full accent-emerald-500">
                    </div>

                    <div>
                        <div class="flex justify-between text-xs text-slate-400">
                            <span>Gig Income Stability</span><span id="val-gig">0.70</span>
                        </div>
                        <input type="range" id="input-gig" min="0" max="1" step="0.05" oninput="updateVal('gig')" class="w-full accent-emerald-500">
                    </div>

                    <div class="grid grid-cols-2 gap-3">
                        <div>
                            <label class="text-xs text-slate-400">UPI Monthly Volume</label>
                            <input type="number" id="input-upi" value="50" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs">
                        </div>
                        <div>
                            <label class="text-xs text-slate-400">Device Changes (90d)</label>
                            <input type="number" id="input-device" value="1" class="w-full bg-slate-900 border border-slate-700 rounded p-2 text-xs">
                        </div>
                    </div>
                </div>

                <button onclick="runUnderwriting()" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-bold py-3 rounded-lg transition-colors">
                    ⚡ Evaluate Application Live
                </button>
            </div>

            <!-- Right Panel: Output -->
            <div class="bg-slate-800 p-6 rounded-xl border border-slate-700">
                <h2 class="text-lg font-bold mb-4 text-slate-200">Multi-Agent Decision Output</h2>
                <div id="output-decision" class="text-slate-400 text-sm">
                    Enter values or select a preset and click "Evaluate Application Live".
                </div>
            </div>
        </div>
    </main>

    <script>
        const profiles = {{ profiles | tojson }};

        function updateVal(id) {
            document.getElementById('val-' + id).innerText = document.getElementById('input-' + id).value;
        }

        function loadApplicantData() {
            const selectedId = document.getElementById('applicant-select').value;
            const applicant = profiles[selectedId];

            document.getElementById('input-id').value = applicant.applicant_id;
            document.getElementById('input-gender').value = applicant.gender;
            document.getElementById('input-age').value = applicant.age_group;
            document.getElementById('input-consent').checked = applicant.consent_given;
            document.getElementById('input-trad-score').value = applicant.traditional_score;
            document.getElementById('input-income').value = applicant.monthly_income_inr;
            document.getElementById('input-dti').value = applicant.debt_to_income_ratio;
            
            document.getElementById('input-utility').value = applicant.utility_pay_punctuality;
            document.getElementById('val-utility').innerText = applicant.utility_pay_punctuality;

            document.getElementById('input-bnpl').value = applicant.bnpl_repayment_rate;
            document.getElementById('val-bnpl').innerText = applicant.bnpl_repayment_rate;

            document.getElementById('input-gig').value = applicant.gig_income_stability_index;
            document.getElementById('val-gig').innerText = applicant.gig_income_stability_index;

            document.getElementById('input-upi').value = applicant.upi_monthly_tx_volume;
            document.getElementById('input-device').value = applicant.device_change_frequency;
        }

        async function runUnderwriting() {
            // Read whatever is currently typed in the fields
            const payload = {
                applicant_id: document.getElementById('input-id').value,
                gender: document.getElementById('input-gender').value,
                age_group: document.getElementById('input-age').value,
                consent_given: document.getElementById('input-consent').checked,
                traditional_score: parseFloat(document.getElementById('input-trad-score').value),
                monthly_income_inr: parseFloat(document.getElementById('input-income').value),
                debt_to_income_ratio: parseFloat(document.getElementById('input-dti').value),
                upi_monthly_tx_volume: parseInt(document.getElementById('input-upi').value),
                bnpl_repayment_rate: parseFloat(document.getElementById('input-bnpl').value),
                utility_pay_punctuality: parseFloat(document.getElementById('input-utility').value),
                telecom_recharge_regularity: 0.90,
                ecommerce_monthly_spend: 10000.0,
                ecommerce_return_rate: 0.05,
                gig_income_stability_index: parseFloat(document.getElementById('input-gig').value),
                digital_footprint_consistency: 0.88,
                device_change_frequency: parseInt(document.getElementById('input-device').value)
            };

            try {
                const res = await fetch('http://localhost:8000/api/v1/underwrite', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });

                if (!res.ok) {
                    const err = await res.json();
                    document.getElementById('output-decision').innerHTML = `
                        <div class="bg-rose-950/50 border border-rose-700 p-4 rounded text-rose-300">
                            <p class="font-bold">❌ Decision Blocked by Consent Agent</p>
                            <p class="text-xs mt-1">${err.detail}</p>
                        </div>`;
                    return;
                }

                const data = await res.json();
                
                let shapList = data.top_shap_drivers.map(d => 
                    `<li class="flex justify-between py-1 border-b border-slate-800">
                        <span class="text-slate-300">${d.feature}</span>
                        <span class="${d.shap_value < 0 ? 'text-emerald-400' : 'text-rose-400'} font-mono">${d.shap_value > 0 ? '+' : ''}${d.shap_value}</span>
                    </li>`
                ).join('');

                document.getElementById('output-decision').innerHTML = `
                    <div class="space-y-4">
                        <div class="bg-slate-900 p-4 rounded-lg border border-slate-700 flex justify-between items-center">
                            <div>
                                <p class="text-xs text-slate-400">Decision Outcome</p>
                                <p class="text-xl font-bold ${data.decision === 'APPROVED' ? 'text-emerald-400' : 'text-rose-400'}">${data.decision}</p>
                            </div>
                            <div class="text-right">
                                <p class="text-xs text-slate-400">Credit Score</p>
                                <p class="text-2xl font-bold text-slate-100">${data.credit_risk_score} <span class="text-xs font-normal text-slate-400">/ 100</span></p>
                            </div>
                        </div>

                        <div class="bg-slate-900 p-4 rounded-lg border border-slate-700">
                            <p class="text-xs font-bold text-slate-400 mb-1">Fraud / Anomaly Level</p>
                            <p class="text-sm font-semibold ${data.fraud_assessment.fraud_risk_level === 'LOW' ? 'text-emerald-400' : 'text-rose-400'}">
                                ${data.fraud_assessment.fraud_risk_level} (ML Anomaly Score: ${data.fraud_assessment.ml_anomaly_score})
                            </p>
                        </div>

                        <div class="bg-slate-900 p-4 rounded-lg border border-slate-700">
                            <p class="text-xs font-bold text-slate-400 mb-2">Top SHAP Drivers</p>
                            <ul class="text-xs">${shapList}</ul>
                        </div>

                        <div class="bg-slate-900 p-4 rounded-lg border border-slate-700">
                            <p class="text-xs font-bold text-slate-400 mb-1">Generated Decision Explanation</p>
                            <p class="text-xs font-mono text-emerald-300 leading-relaxed">${data.explanation_letter}</p>
                        </div>
                    </div>`;
            } catch (e) {
                document.getElementById('output-decision').innerText = "Error contacting backend API at localhost:8000.";
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