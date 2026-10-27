"""Build a self-contained print-friendly page from published aggregate evidence."""
from pathlib import Path
from io import StringIO
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]

def build():
    evidence = ROOT / 'docs/evidence/comparison_v2'
    windows = pd.read_csv(evidence / 'policy_windows.csv')
    wide = windows.pivot(index='origin', columns='policy', values='total_cost')
    changes = wide.sub(wide.historical_average, axis=0).drop(columns='historical_average')
    names = {'forecast_order_up_to': 'Forecast order-up-to', 'point_optimized': 'Point optimization', 'optimized': 'Scenario optimization'}
    changes = changes.rename(columns=names)
    plt.rcParams.update({'font.size': 9, 'svg.fonttype': 'none'})
    ax = changes.plot.bar(stacked=False, figsize=(10, 3.2), color=['#94a3b8', '#e58a32', '#167d9a'], width=.8)
    ax.axhline(0, color='#334155', linewidth=.7)
    ax.set(xlabel='Evaluation origin (M5 day)', ylabel='Cost difference ($)')
    ax.legend(loc='upper center', bbox_to_anchor=(.5, 1.18), ncol=3, frameon=False)
    plt.tight_layout()
    buffer = StringIO(); plt.savefig(buffer, format='svg', bbox_inches='tight'); plt.close()
    svg = buffer.getvalue(); svg = svg[svg.index('<svg'):]
    totals = windows.groupby('policy')[['total_cost', 'unmet_units', 'proxy_units']].sum()
    labels = {'historical_average': 'Trailing-average orders', **names}
    rows = ''
    for policy in ['historical_average','forecast_order_up_to','point_optimized','optimized']:
        r = totals.loc[policy]; delta = (r.total_cost / totals.loc['historical_average','total_cost'] - 1) * 100
        wins = int((wide[policy] < wide.historical_average).sum())
        rows += f'<tr><td>{labels[policy]}</td><td>${r.total_cost:,.2f}</td><td>{delta:+.2f}%</td><td>{"—" if policy == "historical_average" else str(wins)+"/17"}</td><td>{1-r.unmet_units/r.proxy_units:.2%}</td></tr>'
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RetailOS | Evidence before complexity</title><style>
    *{box-sizing:border-box}body{font:15px/1.55 system-ui,sans-serif;color:#172b40;background:#edf2f6;margin:0}main{max-width:1000px;margin:32px auto;background:white;padding:42px}h1{font-size:38px;line-height:1.15;margin:12px 0}h2{font-size:21px;margin:25px 0 10px}.eyebrow{color:#167d9a;font-weight:700;letter-spacing:2px;font-size:12px}.lead{font-size:18px}.callout{padding:16px 20px;background:#edf6f8;border-left:4px solid #167d9a}.facts{display:flex;gap:26px;margin:20px 0}.facts strong{display:block;font-size:24px}table{border-collapse:collapse;width:100%;font-size:13px;table-layout:fixed}th,td{padding:10px 7px;border-bottom:1px solid #dbe3ec;text-align:right;overflow-wrap:anywhere}th:first-child,td:first-child{text-align:left;width:34%}th{background:#edf2f6}svg{width:100%;height:auto}figure{margin:16px 0}figcaption,.small{font-size:12px;color:#526477}button{padding:10px 16px;border:0;background:#172b40;color:white;cursor:pointer}a{color:#126c86}.page{break-before:page}footer{border-top:1px solid #dbe3ec;padding-top:12px;margin-top:25px;font-size:12px;color:#526477}@page{size:A4;margin:16mm}@media print{body{background:white;font-size:10pt}main{margin:0;padding:0;max-width:none}h1{font-size:27pt}h2{font-size:15pt}.lead{font-size:12pt}.no-print{display:none}table{font-size:9pt}tr,figure,.callout{break-inside:avoid}a{color:inherit;text-decoration:none}}
    </style></head><body><main><button class="no-print" onclick="window.print()">Print / Save as PDF</button>
    <p class="eyebrow">RETAILOS / RETROSPECTIVE DECISION STUDY</p><h1>Evidence before complexity.</h1><p class="lead">Can better sales forecasts improve inventory decisions under a shared purchasing budget?</p>
    <div class="facts"><div><strong>42</strong>product–store series</div><div><strong>17</strong>28-day evaluation episodes</div><div><strong>4</strong>ordering policies</div></div>
    <div class="callout"><b>Decision:</b> retain trailing-average ordering as the practical benchmark. Point optimization has a small aggregate cost advantage, but wins only 8 of 17 windows and has a lower unit fill rate. Scenario optimization has not established added value.</div>
    <h2>1. What the comparison found</h2><table><thead><tr><th>Policy</th><th>Modeled cost</th><th>Cost change*</th><th>Lower-cost windows*</th><th>Proxy fill rate</th></tr></thead><tbody>'''+rows+'''</tbody></table><p class="small">*Against trailing-average orders. Negative change means lower cost. All costs are simulations under assumed operating inputs; no actual Walmart savings were measured.</p>
    <h2>2. Small aggregate gains can hide uneven performance</h2><figure>'''+svg+'''<figcaption>Each policy has a separate bar; differences are not added together. Below zero means lower cost than trailing-average orders. Period: February 2, 2015–May 22, 2016.</figcaption></figure>
    <section class="page"><p class="eyebrow">INTERPRETATION / VERIFICATION / LIMITS</p><h2>3. What the experiment isolates</h2><p>Trailing-average and forecast order-up-to rules set target quantities and scale them to budget. Point optimization allocates the same budget using one forecast path and a cost objective. Scenario optimization uses that same objective with forecast-plus-residual paths. All policies share stock, lead time, budget and evaluation sales within each episode.</p>
    <p>Point optimization costs $678.05 less than trailing-average orders in aggregate, but wins only 8/17 windows. It beats scenario optimization in 14/17 windows. This supports investigating the current scenario construction; it does not prove uncertainty-aware optimization is generally inferior.</p>
    <h2>4. Prediction and uncertainty</h2><p>Gradient boosting has daily MAE 1.645 versus 1.712 for the trailing mean, approximately 3.95% lower. Twelve earlier residual blocks support eight sampled paths. The daily 10–90% scenario envelope contains 52.42% of evaluation observations; it is not a calibrated 80% prediction interval.</p>
    <h2>5. What was verified</h2><p>Independent daily replay of saved orders matched all 68 policy-window costs, with maximum absolute difference below $0.000001. Nonnegative integer orders, budget feasibility, unmet units and ending stock were checked. This is output-accounting verification, not independent retraining from official raw files.</p>
    <h2>6. Boundaries of the conclusion</h2><p>This is an exploratory retrospective comparison, not a fresh holdout. It includes previously inspected periods; shared histories and seasons make observations dependent. Each episode resets initial stock. Only 3/42 series overlap V1, so differences between the two studies cannot be attributed to a method revision.</p><p>Observed sales may understate demand. Purchase cost, holding cost, shortage penalties and initial stock are assumed. Ending stock receives no salvage credit. No statistical significance, deployment readiness or causal business benefit is claimed.</p>
    <div class="callout"><b>Stopping decision:</b> close this bounded experiment, preserve negative findings and avoid further model search merely to obtain a favorable headline. Any operational adoption requires verified inputs and prospective evaluation.</div>
    <footer>Source: official M5 data, executed locally by the project owner. Public aggregate evidence: docs/evidence/comparison_v2. Original V1 findings remain preserved.<br><a href="https://github.com/younjuhan03/retail-decision-intelligence">github.com/younjuhan03/retail-decision-intelligence</a></footer></section></main></body></html>'''
    destination = ROOT / 'docs/comparison_case_study.html'
    destination.write_text(page, encoding='utf-8')
    return destination

if __name__ == '__main__':
    print(build())
