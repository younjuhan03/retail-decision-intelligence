from pathlib import Path
from dataclasses import asdict
import json
import platform
import importlib.metadata
import html
import numpy as np
import pandas as pd
from .data import load_m5
from .forecast import predict, score, residual_paths, MODELS
from .inventory import Scenario, optimize, feasible_baseline, simulate
from .review import review


def evaluate_window(pred, past_predictions, model, config, overrides=None):
    cfg = dict(config)
    cfg.update(overrides or {})
    origin = int(pred.origin.iloc[0])
    pred = pred.sort_values(['id', 'day'])
    ids = list(pred.id.unique())
    n = len(ids)
    forecast = pred[model].to_numpy().reshape(n, 28)
    actual = pred.sales.to_numpy().reshape(n, 28)
    item = pred.groupby('id', sort=True).first()
    costs = item.price_asof.to_numpy() * cfg['cost_ratio']
    initial = np.floor(item.mean28.to_numpy() * cfg['initial_days'])
    budget = float((item.mean28.to_numpy() * 28 * costs).sum() * cfg['budget_ratio'])
    scenario = Scenario(budget, cfg['holding_daily_ratio'], cfg['penalty_cost_multiple'], int(cfg['lead_days']))
    residuals = residual_paths(past_predictions, model, ids, origin, cfg['scenario_count'], cfg['uncertainty_scale'], cfg['seed'])
    paths = np.maximum(0, forecast[None] + residuals)
    solution = optimize(paths, costs, initial, scenario)
    # Same initial stock, lead, cash, terminal treatment for all policies.
    policies = {'historical_average': feasible_baseline(np.maximum(0, item.mean28.to_numpy() * 28 - initial), costs, budget),
                'forecast_order_up_to': feasible_baseline(np.maximum(0, forecast.sum(axis=1) - initial), costs, budget)}
    point_solution = None
    if cfg.get('include_point_optimizer', False):
        point_solution = optimize(forecast[None], costs, initial, scenario)
        if point_solution['orders'] is not None:
            policies['point_optimized'] = point_solution['orders']
    if solution['orders'] is not None:
        policies['optimized'] = solution['orders']
    rows, allocations = [], []
    for policy, orders in policies.items():
        result = simulate(actual, orders, costs, initial, scenario)
        rows.append({'origin': origin, 'policy': policy, 'budget': budget, **result})
        for i, key in enumerate(ids):
            allocations.append({'origin': origin, 'policy': policy, 'id': key, 'order_units': int(orders[i]),
                                'unit_cost_assumed': costs[i], 'initial_inventory_assumed': initial[i],
                                'forecast_28d': float(forecast[i].sum()), 'actual_proxy_28d': float(actual[i].sum())})
    low, high = np.quantile(paths, [.1, .9], axis=0)
    coverage = float(((actual >= low) & (actual <= high)).mean())
    decision = review(solution, costs, budget, evidence_ready=False, coverage=coverage)
    intervals = pred[['origin', 'id', 'day']].copy()
    intervals['lower_10'] = low.reshape(-1)
    intervals['upper_90'] = high.reshape(-1)
    intervals['observed_proxy'] = actual.reshape(-1)
    intervals['covered'] = ((actual >= low) & (actual <= high)).reshape(-1)
    return rows, allocations, {'origin': origin, 'scenario': asdict(scenario), 'model': model,
                              'empirical_80pct_coverage': coverage, 'review': decision,
                              'point_solver_status': point_solution['status'] if point_solution else None,
                              'solver_status': solution['status'], 'solver_objective': solution.get('objective')}, intervals


def run(raw, output, config):
    out = Path(output)
    out.mkdir(parents=True, exist_ok=True)
    config = dict(config)
    if config['horizon'] != 28 or len(config['origins']) < 6 or any(b - a < 28 for a, b in zip(config['origins'], config['origins'][1:])):
        raise ValueError('Require 28-day horizon and >=6 nonoverlapping chronological origins')
    calibration_count = int(config.get('calibration_count', 3))
    if calibration_count < 1 or len(config['origins']) < calibration_count + 3:
        raise ValueError('Require calibration blocks, one selection block and at least two evaluation blocks')
    panel, selected, cal, manifest = load_m5(raw, config)
    predictions = []
    for origin in config['origins']:
        print(f'Training and forecasting origin d_{origin}', flush=True)
        p, _ = predict(panel, cal, origin, seed=config['seed'])
        predictions.append(p)
    predictions = pd.concat(predictions, ignore_index=True)
    scores = score(predictions, panel)
    selection_origin = config['origins'][calibration_count]
    ranking = scores[scores.origin == selection_origin].groupby('model').mae.mean().sort_values()
    winner = ranking.index[0]
    # Calibration and selection always precede evaluation; retrospective runs remain exploratory.
    # Freeze uncertainty blocks, excluding selection/evaluation residuals.
    calibration = predictions[predictions.origin.isin(config['origins'][:calibration_count])]
    test_origins = config['origins'][calibration_count + 1:]
    evaluations, allocation, decisions, intervals, sensitivity = [], [], [], [], []
    for origin in test_origins:
        p = predictions[predictions.origin == origin]
        rows, alloc, decision, interval = evaluate_window(p, calibration, winner, config)
        evaluations.extend(rows); allocation.extend(alloc); decisions.append(decision); intervals.append(interval)
        variants = [('base', {})]
        for key, values in {'budget_ratio': [.5, 1.0, 1.25], 'penalty_cost_multiple': [1., 6.],
                            'holding_daily_ratio': [0., .01], 'lead_days': [0, 7],
                            'initial_days': [0., 7.], 'uncertainty_scale': [.5, 1.5]}.items():
            variants.extend((f'{key}={value}', {key: value}) for value in values)
        if not config.get('run_sensitivity', True):
            variants = [('base', {})]
        for label, changes in variants:
            if label == 'base':
                scenario_rows = rows
            else:
                scenario_rows, _, _, _ = evaluate_window(p, calibration, winner, config, changes)
            sensitivity.extend({'variant': label, **r} for r in scenario_rows)
    evaluation = pd.DataFrame(evaluations)
    evaluation['start_date'] = evaluation.origin.map(cal.set_index('day').date.add(pd.Timedelta(days=1)).to_dict())
    evaluation['end_date'] = evaluation.origin.add(28).map(cal.set_index('day').date.to_dict())
    # No confidence interval: two held-out time blocks are insufficient for reliable inference.
    paired = evaluation.pivot(index='origin', columns='policy', values='total_cost')
    improvements = []
    for baseline in ['historical_average', 'forecast_order_up_to']:
        if 'optimized' in paired:
            valid = paired[[baseline, 'optimized']].dropna()
            denominator = float(valid[baseline].sum())
            improvements.append({'baseline': baseline, 'paired_windows': len(valid),
                                 'baseline_total_cost_denominator': denominator,
                                 'optimized_total_cost': float(valid.optimized.sum()),
                                 'simulation_cost_change_fraction': float((denominator - valid.optimized.sum()) / denominator) if denominator else None})
    comparison_rows = []
    for candidate in ['point_optimized', 'optimized']:
        if candidate not in paired:
            continue
        for baseline in ['historical_average', 'forecast_order_up_to']:
            valid = paired[[baseline, candidate]].dropna()
            denominator = float(valid[baseline].sum())
            comparison_rows.append({'candidate': candidate, 'baseline': baseline, 'paired_windows': len(valid),
                'candidate_total_cost': float(valid[candidate].sum()), 'baseline_total_cost': denominator,
                'cost_increase_fraction': float((valid[candidate].sum() - denominator) / denominator) if denominator else None,
                'lower_cost_windows': int((valid[candidate] < valid[baseline]).sum())})
    pd.DataFrame(comparison_rows).to_csv(out / 'policy_comparison.csv', index=False)
    coverage = float(pd.concat(intervals).covered.mean())
    summary = {'status': 'COMPUTED; HUMAN REVIEW REQUIRED', 'selected_model': winner,
               'calibration_origins': config['origins'][:calibration_count],
               'evaluation_role': config.get('evaluation_role', 'original held-out evaluation'),
               'selection_origin': selection_origin, 'test_origins': test_origins,
               'series_count': len(selected), 'improvements': improvements,
               'empirical_80pct_coverage': coverage,
               'coverage_definition': 'Fraction of held-out SKU-days inside the empirical 10–90% scenario envelope; uncalibrated.',
               'interpretation': 'Counterfactual simulation conditional on assumptions; not actual Walmart cost savings.',
               'uncertainty_warning': f'{calibration_count} calibration blocks and {len(test_origins)} evaluation blocks; overlapping histories and limited seasons do not support population-significance claims.'}
    predictions.to_parquet(out / 'forecasts.parquet', index=False)
    panel.to_parquet(out / 'panel.parquet', index=False)
    selected.to_csv(out / 'selected_series.csv', index=False)
    scores.to_csv(out / 'forecast_metrics.csv', index=False)
    evaluation.to_csv(out / 'policy_evaluation.csv', index=False)
    pd.DataFrame(allocation).to_csv(out / 'allocations.csv', index=False)
    pd.DataFrame(sensitivity).to_csv(out / 'sensitivity.csv', index=False)
    pd.concat(intervals).to_csv(out / 'interval_coverage.csv', index=False)
    for name, content in [('summary', summary), ('decisions', decisions), ('provenance', manifest), ('config', config)]:
        (out / f'{name}.json').write_text(json.dumps(content, indent=2, default=str), encoding='utf-8')
    versions = {x: importlib.metadata.version(x) for x in ['numpy', 'pandas', 'scipy', 'scikit-learn']}
    (out / 'environment.json').write_text(json.dumps({'python': platform.python_version(), 'packages': versions}, indent=2))
    render_report(out, summary, evaluation, scores, test_origins)
    return summary


def render_report(out, summary, evaluation, scores, test_origins):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    totals = evaluation.groupby('policy')[['procurement', 'holding_cost', 'lost_sales_penalty']].sum()
    ax = totals.plot.bar(stacked=True, color=['#2563eb', '#22c5a0', '#ef9b47'], figsize=(9, 5), rot=15)
    ax.set(ylabel='Simulated cost ($)', title='Cost composition • held-out historical-sales proxy')
    plt.tight_layout(); plt.savefig(out / 'cost_composition.png', dpi=170); plt.close()
    metrics = scores[scores.origin.isin(test_origins)].groupby('model')[['mae', 'mse', 'bias']].mean()
    metrics['rmse'] = np.sqrt(metrics.pop('mse'))
    narrative = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>RetailOS: Turning Demand Forecasts into Inventory Decisions</title><style>body{{font:17px/1.7 system-ui;margin:60px auto;max-width:1050px;padding:0 24px;background:#f5f7fb;color:#18243a}}h1{{font-size:45px;line-height:1.15}}h2{{margin-top:45px}}table{{border-collapse:collapse;background:white;width:100%;font-size:14px}}td,th{{padding:10px;border-bottom:1px solid #ddd;text-align:right}}img{{max-width:100%}}pre{{white-space:pre-wrap;background:#e6edf5;padding:20px}}</style><p>RETAILOS / DECISION INTELLIGENCE</p><h1>Turning Demand Forecasts into Inventory Decisions</h1><p>How should a retailer allocate a limited inventory budget when future sales are uncertain?</p><h2>Data and forecasting</h2><p>Official M5 observed unit sales and selling prices. Selection uses training-period information only. Earlier forecast windows provide uncalibrated empirical residual paths, one selects the forecast model, and subsequent windows evaluate decisions. Direct horizon features use only origin-available observations.</p>{metrics.to_html(float_format=lambda x:f'{x:.4f}')}<h2>Optimization and decision evaluation</h2><p>Integer orders share one purchasing budget. A 28-day review period, modeled initial stock, assumed purchase costs, and fixed lead time determine daily holding and unmet-proxy penalties. Baselines receive the same constraints.</p>{evaluation.to_html(index=False, float_format=lambda x:f'{x:.3f}')}<img src="cost_composition.png" alt="Computed cost decomposition"><h2>Results</h2><pre>{html.escape(json.dumps(summary, indent=2))}</pre><h2>Limitations and business implications</h2><p>These are model-based counterfactual costs, not observed Walmart savings. The empirical_80pct_coverage field describes a 10–90% scenario envelope, not a calibrated 80% prediction interval. Unit sales may understate unconstrained demand. Operating inputs are assumptions. The small number of independent time blocks prevents strong statistical claims. Review sensitivity.csv before choosing a policy; a forecast improvement alone does not establish a better decision.</p><p>Rule-based review explains verified allocations and flags limited evidence. No language model determines order quantities.</p></html>'''
    (out / 'case_study.html').write_text(narrative, encoding='utf-8')
