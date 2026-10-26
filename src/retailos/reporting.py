"""Display-only summaries; never feed held-out outcomes back into order decisions."""
import numpy as np
import pandas as pd

POLICY_LABELS = {'historical_average': 'Trailing-average orders', 'forecast_order_up_to': 'Forecast order-up-to', 'point_optimized': 'Point-forecast optimized orders', 'optimized': 'Scenario-optimized orders'}
MODEL_LABELS = {'historical_mean': 'Active-history mean', 'seasonal_naive': 'Seasonal naive', 'rolling_mean': 'Trailing 28-day mean', 'gradient_boosting': 'Gradient boosting'}


def policy_totals(evaluations):
    columns = ['total_cost', 'procurement', 'holding_cost', 'lost_sales_penalty', 'unmet_units', 'proxy_units', 'ending_inventory', 'budget']
    totals = evaluations.groupby('policy', sort=True)[columns].sum()
    totals['fill_rate'] = 1 - totals.unmet_units.div(totals.proxy_units.replace(0, np.nan))
    totals['budget_utilization'] = totals.procurement.div(totals.budget.replace(0, np.nan)).fillna(0)
    totals.index = totals.index.map(lambda x: POLICY_LABELS.get(x, x))
    return totals


def forecast_totals(metrics):
    rows = []
    for model, g in metrics.groupby('model', sort=True):
        actual = g.actual_units.sum()
        rows.append({'model': MODEL_LABELS.get(model, model), 'mae': g.mae.mean(), 'rmse': np.sqrt(g.mse.mean()),
                     'wape': g.abs_error.sum() / actual if actual > 0 else np.nan, 'bias': g.bias.mean()})
    return pd.DataFrame(rows).sort_values('mae').reset_index(drop=True)


def paired_cost_comparison(evaluations):
    """Compare only matched windows; positive change means a higher cost."""
    wide = evaluations.pivot(index='origin', columns='policy', values='total_cost')
    rows = []
    if 'historical_average' not in wide:
        return pd.DataFrame(rows)
    for candidate in wide.columns:
        if candidate == 'historical_average':
            continue
        paired = wide[['historical_average', candidate]].dropna()
        base = paired.historical_average.sum()
        rows.append({'Policy': POLICY_LABELS.get(candidate, candidate),
                     'Paired windows': len(paired),
                     'Cost change vs trailing average': (paired[candidate].sum() - base) / base if base else np.nan,
                     'Lower-cost windows': int((paired[candidate] < paired.historical_average).sum())})
    return pd.DataFrame(rows)
