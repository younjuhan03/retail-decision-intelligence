"""Display-only summaries; never feed held-out outcomes back into order decisions."""
import numpy as np
import pandas as pd

POLICY_LABELS = {'historical_average': 'Trailing-average orders', 'forecast_order_up_to': 'Forecast order-up-to', 'optimized': 'Scenario-optimized orders'}
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
