"""Export aggregate research evidence from a completed local run; never copy raw M5 rows.
Run from the repository root: python scripts/export_evidence.py --results results/local
"""
import argparse
import base64
from pathlib import Path
import html
import json
import hashlib
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from retailos.reporting import policy_totals, forecast_totals, POLICY_LABELS


def export(results, docs):
    results, docs = Path(results), Path(docs)
    evidence = docs / 'evidence'; evidence.mkdir(parents=True, exist_ok=True)
    summary = json.loads((results / 'summary.json').read_text(encoding='utf-8'))
    config = json.loads((results / 'config.json').read_text(encoding='utf-8'))
    provenance = json.loads((results / 'provenance.json').read_text(encoding='utf-8'))
    environment = json.loads((results / 'environment.json').read_text(encoding='utf-8'))
    policies = pd.read_csv(results / 'policy_evaluation.csv')
    metrics = pd.read_csv(results / 'forecast_metrics.csv')
    intervals = pd.read_csv(results / 'interval_coverage.csv')
    allocations = pd.read_csv(results / 'allocations.csv')
    panel = pd.read_parquet(results / 'panel.parquet')
    # Separate physical replay: source rows stay local; only validation scalars are exported.
    checked = 0
    for (origin, policy), group in allocations.groupby(['origin', 'policy']):
        total = 0.0
        for row in group.itertuples():
            stock = float(row.initial_inventory_assumed); lost = holding = 0.0
            if row.order_units < 0 or row.order_units != np.floor(row.order_units):
                raise ValueError('Invalid saved integer allocation')
            heldout = panel[(panel.id == row.id) & panel.day.between(origin + 1, origin + 28)].sort_values('day')
            if len(heldout) != 28:
                raise ValueError('Incomplete physical replay horizon')
            for day, sales in enumerate(heldout.sales):
                if day == config['lead_days']: stock += row.order_units
                served = min(stock, sales); lost += sales - served; stock -= served
                holding += stock * row.unit_cost_assumed * config['holding_daily_ratio']
            total += row.order_units * row.unit_cost_assumed + holding + lost * row.unit_cost_assumed * config['penalty_cost_multiple']
        saved = policies[(policies.origin == origin) & (policies.policy == policy)].iloc[0]
        if not np.isclose(total, saved.total_cost, atol=1e-6):
            raise ValueError('Physical replay does not match saved result')
        if saved.procurement > saved.budget + 1e-6:
            raise ValueError('Saved policy exceeds its cash budget')
        checked += 1
    totals = policy_totals(policies)
    test_metrics = forecast_totals(metrics[metrics.origin.isin(summary['test_origins'])])
    sensitivity = pd.read_csv(results / 'sensitivity.csv').pivot_table(index='variant', columns='policy', values='total_cost', aggfunc='sum')
    sensitivity['cost_change_vs_trailing_average_pct'] = 100 * (sensitivity.optimized / sensitivity.historical_average - 1)
    alternate_sensitivity = sensitivity.drop(index='base', errors='ignore')
    unfavorable_variants = int((alternate_sensitivity.cost_change_vs_trailing_average_pct > 0).sum())
    baseline = totals.loc[POLICY_LABELS['historical_average']]
    optimized = totals.loc[POLICY_LABELS['optimized']]
    forecast_baseline = totals.loc[POLICY_LABELS['forecast_order_up_to']]
    scores = test_metrics.set_index('model')
    delta = optimized.total_cost - baseline.total_cost
    cost_change_pct = 100 * delta / baseline.total_cost
    mae_change = 100 * (1 - scores.loc['Gradient boosting', 'mae'] / scores.loc['Trailing 28-day mean', 'mae'])
    coverage = float(intervals.covered.mean())
    if not np.isclose(coverage, summary['empirical_80pct_coverage']):
        raise ValueError('Coverage summary disagrees with saved observations')
    values = {
        'study': 'RetailOS first real-data study', 'status': 'COMPUTED; REVIEW REQUIRED',
        'source': provenance['source'], 'series_count': summary['series_count'], 'test_origins': summary['test_origins'],
        'start_date': str(policies.start_date.min()), 'end_date': str(policies.end_date.max()),
        'test_episodes': len(summary['test_origins']), 'sku_days': len(intervals),
        'calibration_unique_time_blocks': len(config['origins'][:3]), 'unfavorable_sensitivity_variants': unfavorable_variants, 'alternative_sensitivity_variants': len(alternate_sensitivity), 'sampled_scenarios': config['scenario_count'],
        'selected_forecast': summary['selected_model'], 'mae_reduction_vs_rolling_pct': float(mae_change),
        'cost_increase_vs_trailing_average_pct': float(cost_change_pct),
        'cost_increase_vs_forecast_order_up_to_pct': float(100 * (optimized.total_cost / forecast_baseline.total_cost - 1)),
        'uncalibrated_10_90_scenario_envelope_coverage': coverage,
        'cost_increase_dollars': float(delta),
        'cost_delta_breakdown': {col: float(optimized[col] - baseline[col]) for col in ['procurement', 'holding_cost', 'lost_sales_penalty']},
        'independently_replayed_policy_windows': checked,
        'interpretation': 'Historical-sales-proxy counterfactual simulation with assumed operating inputs; not measured Walmart savings.',
        'source_result_hashes': {name: hashlib.sha256((results / name).read_bytes()).hexdigest() for name in ['summary.json', 'policy_evaluation.csv', 'forecast_metrics.csv', 'interval_coverage.csv']},
        'operating_assumptions': config, 'original_run_environment': environment,
        'provenance_audit': provenance['audit'],
        'data_release_note': 'Only aggregate research summaries and original figures are exported; source data, SKU rows, forecasts, orders, prices and credentials remain excluded. This does not grant redistribution rights to M5 data.'}
    (evidence / 'first_run.json').write_text(json.dumps(values, indent=2), encoding='utf-8')
    totals.to_csv(evidence / 'policy_totals.csv')
    test_metrics.to_csv(evidence / 'forecast_metrics.csv', index=False)
    policies.to_csv(evidence / 'policy_windows.csv', index=False)
    sensitivity.to_csv(evidence / 'sensitivity_totals.csv')
    plt.rcParams.update({'font.size': 11, 'axes.spines.top': False, 'axes.spines.right': False})
    ax = totals[['procurement', 'holding_cost', 'lost_sales_penalty']].plot.bar(stacked=True, figsize=(9, 5), rot=12, color=['#2563eb', '#20b8a4', '#e99846'])
    ax.set(xlabel='', ylabel='Simulated cost ($)', title='Same budget, different allocation • two held-out episodes')
    ax.legend(['Purchasing expenditure', 'Holding cost', 'Unmet-sales-proxy penalty'], loc='lower left', fontsize=9)
    plt.tight_layout(); plt.savefig(evidence / 'policy_costs.png', dpi=170); plt.close()
    ax = test_metrics.set_index('model').mae.plot.barh(figsize=(8, 4), color='#2563eb')
    ax.invert_yaxis(); ax.set(xlabel='MAE (units per product–store day)', ylabel='', title='Point-forecast accuracy • lower is better')
    for bar in ax.patches: ax.text(bar.get_width() + .02, bar.get_y() + bar.get_height() / 2, f'{bar.get_width():.3f}', va='center')
    ax.set_xlim(0, test_metrics.mae.max() * 1.17)
    plt.tight_layout(); plt.savefig(evidence / 'forecast_mae.png', dpi=170); plt.close()
    def table(df): return '<div class="scroll">' + df.to_html(float_format=lambda x: f'{x:,.3f}', border=0) + '</div>'
    def embedded(name): return 'data:image/png;base64,' + base64.b64encode((evidence / name).read_bytes()).decode()
    screenshot = docs.parent / 'assets/screenshots/executive_overview.png'
    app_section = ''
    if screenshot.is_file():
        app_image = base64.b64encode(screenshot.read_bytes()).decode()
        app_section = '<h2>Actual application</h2><p>The current dashboard renders the inspected first-run results and keeps REVIEW REQUIRED visible. This is an actual running Streamlit capture, not a mockup.</p><figure><img src="data:image/png;base64,' + app_image + '" alt="Actual RetailOS executive overview"></figure>'
    document = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>RetailOS: Turning Demand Forecasts into Inventory Decisions</title><style>
    :root{{color-scheme:light}}*{{box-sizing:border-box}}body{{font:16px/1.7 system-ui;margin:0;background:#f4f7fb;color:#15293d}}main{{max-width:1080px;margin:auto;padding:48px 24px}}header{{background:#102a43;color:white;padding:38px;border-radius:18px}}header p{{color:#c6d9eb}}h1{{font-size:40px;line-height:1.15;max-width:820px}}h2{{margin-top:38px;font-size:25px}}.eyebrow{{font-size:12px;letter-spacing:3px;color:#4cd5b5}}.callout{{background:#fff1d9;border-left:4px solid #db9434;padding:20px;margin:24px 0}}.cards{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin:22px 0}}.card{{background:white;border:1px solid #dce5ef;border-radius:12px;padding:20px}}.card strong{{font-size:30px;display:block}}.small{{font-size:14px;color:#52667b}}table{{border-collapse:collapse;width:100%;font-size:12px;background:white}}td,th{{padding:10px;border-bottom:1px solid #dce5ef;text-align:right;overflow-wrap:anywhere}}.scroll{{overflow-x:auto}}img{{width:100%;height:auto;border-radius:10px}}a{{color:#2361ca}}li{{margin:8px 0}}@media(max-width:700px){{.cards{{grid-template-columns:1fr}}h1{{font-size:31px}}header{{padding:24px}}}}@media print{{body{{background:white;color:#132638}}main{{padding:0;max-width:none}}header{{background:white!important;color:#132638!important;padding:0;border-radius:0}}header p,.eyebrow{{color:#415970!important}}h1{{font-size:30px}}h2{{break-after:avoid}}.card,.callout,figure,tr{{break-inside:avoid}}thead{{display:table-header-group}}table{{font-size:10px}}td,th{{padding:6px}}.scroll{{overflow:visible}}a{{color:inherit}}.no-print{{display:none}}}}
    </style></head><body><main><header><p class="eyebrow">RETAILOS / BUSINESS ANALYTICS CASE STUDY</p><h1>Turning Demand Forecasts into Inventory Decisions</h1><p>Better forecasts are useful only when they support better decisions. This first real-data study found an important gap between the two.</p></header>
    <div class="cards"><div class="card"><strong>{summary['series_count']}</strong>product–store series</div><div class="card"><strong>{mae_change:.2f}%</strong>lower forecast MAE vs rolling mean</div><div class="card"><strong>+{cost_change_pct:.2f}%</strong>simulated inventory cost vs trailing average</div></div>
    <div class="callout"><b>Decision: REVIEW REQUIRED.</b> The scenario optimizer did not beat either practical order policy under the base assumptions. Retain a simple policy as the development benchmark; no production recommendation or actual savings claim is supported.</div>
    <h2>The business question</h2><p>How should a retailer allocate a limited purchasing budget across products when future sales are uncertain? RetailOS connects chronological forecasting, integer inventory optimization, held-out policy replay and grounded review. Its objective is to test decision value, rather than assume that a more complex model creates it.</p>
    <h2>Data and scope</h2><p>The designated source is <a href="https://www.kaggle.com/competitions/m5-forecasting-accuracy/data">official Walmart M5 unit sales, calendar and selling prices</a>. The study selected two eligible products per store–department across {html.escape(', '.join(config['stores']))}: {summary['series_count']} series and {int(provenance['audit']['rows']):,} selected historical rows. Eligibility requires a listed-price history of at least 84 days at the first forecast origin; zero-sales shares and volume use only training information. This is a deliberate contrast of demand patterns, not a probability sample of Walmart.</p><p>The two held-out episodes cover <b>{values['start_date']} through {values['end_date']}</b>, with initial inventory reset for each episode. Unit sales are a potentially censored demand proxy. Purchase cost, initial stock, holding cost, shortage penalty, budget and lead time are assumptions.</p>
    <h2>Forecasting</h2><p>Three earlier 28-day origins provide residual blocks; a fourth chooses the forecast model; the final two evaluate outcomes. Gradient boosting uses origin-available lag summaries, last observed price and known-calendar assumptions. Training targets end by each origin. It is compared with active-history mean, seasonal naive and trailing mean forecasts.</p>{table(test_metrics)}<figure><img src="{embedded('forecast_mae.png')}" alt="Computed held-out daily MAE by forecasting model"></figure>
    <h2>Inventory optimization</h2><p>A shared budget constrains nonnegative integer orders. One order arrives after an assumed two-day lead time during each 28-day episode. The objective is procurement plus expected daily holding and unmet-sales-proxy penalty across generated scenarios. Default purchase cost is 65% of last observed selling price; holding is 0.2% of assumed unit cost per day; shortage penalty is three times unit cost; budget is 75% of historical purchasing need; initial inventory is three days of trailing sales. There is no terminal salvage credit.</p><p>Both simple policies receive identical cash, stock, arrival and accounting assumptions. Infeasible targets use the same proportional reduction and integer rounding rule. Neither policy generation nor the optimizer sees future observed sales.</p>
    <h2>Decision evaluation and results</h2>{table(totals[['total_cost','procurement','holding_cost','lost_sales_penalty','fill_rate','ending_inventory']])}<figure><img src="{embedded('policy_costs.png')}" alt="Computed inventory cost decomposition for three policies"></figure><p>Across two paired test episodes, optimized cost was <b>${optimized.total_cost:,.2f}</b> versus <b>${baseline.total_cost:,.2f}</b> for trailing-average orders and <b>${forecast_baseline.total_cost:,.2f}</b> for forecast order-up-to. The increase is {cost_change_pct:.2f}% against the first baseline and {values['cost_increase_vs_forecast_order_up_to_pct']:.2f}% against the second, using each baseline's pooled cost as denominator.</p><p>An independent physical replay matched all {checked} saved policy-window costs. Against trailing-average orders, purchasing expenditure changed by ${values['cost_delta_breakdown']['procurement']:.3f}, holding by +${values['cost_delta_breakdown']['holding_cost']:,.2f}, and unmet-proxy penalties by +${values['cost_delta_breakdown']['lost_sales_penalty']:,.2f}. More inventory remained while more sales-proxy units went unmet: an allocation mismatch under this evaluation.</p>
    <h2>Diagnosis and sensitivity</h2><p>The original scenario-expected cost replay favored the optimizer, while held-out costs favored the simple policies. Only three unique residual blocks support eight sampled paths. The empirical 10–90% daily scenario envelope covered <b>{coverage:.2%}</b> of held-out SKU-days; it is not a calibrated 80% prediction interval. Inadequate scenario representation is a plausible contributor, not an established sole cause.</p><p>Optimization was more expensive than trailing-average orders in {unfavorable_variants} of {len(alternate_sensitivity)} alternative one-factor scenarios. The favorable shortage-penalty multiple of 1 changes the business objective and is not a reason to tune assumptions to manufacture success. The scenario variants are correlated, not independent replications.</p>{table(sensitivity[['cost_change_vs_trailing_average_pct']])}
    <h2>Grounded decision support</h2><p>The application uses deterministic explanations of verified spend, constraints and risk flags. It does not use an LLM to select orders, and it does not invent confidence scores. A successful mathematical solve remains separate from an evidence-supported business recommendation.</p>
    <h2>Limits and next experiments</h2><ul><li>Two held-out blocks and three calibration blocks do not establish population significance or robust tail protection.</li><li>Observed sales can understate demand; actual inventory and operating costs are unavailable.</li><li>Zero terminal salvage, central budget pooling and episode resets materially shape interpretation.</li><li>Compare point-forecast optimization, improved uncertainty construction and simple policies on pre-test development windows. Select the decision rule before evaluating new holdout periods.</li><li>Already inspected test windows may support exploratory reanalysis; they are no longer an untouched confirmation set.</li></ul>
    {app_section}<h2>Business implication</h2><p>The verified accomplishment is an end-to-end decision experiment that can reject an attractive but unsupported optimization recommendation. Better point accuracy was insufficient for better inventory decisions. The present evidence supports improving scenario validation and retaining a transparent baseline, not deploying the optimizer or claiming Walmart savings.</p><p class="small">Original run: Windows / Python {html.escape(environment['python'])}. Aggregate evidence is reproducible with <code>python scripts/export_evidence.py --results results/local</code>. Raw source data, SKU observations and detailed order allocations are excluded from this page and the public snapshot. No Walmart implementation or endorsement is implied.</p></main></body></html>'''
    (docs / 'case_study.html').write_text(document, encoding='utf-8')
    print(json.dumps(values, indent=2))
    return values

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', default='results/local')
    parser.add_argument('--docs', default='docs')
    args = parser.parse_args(); export(args.results, args.docs)
