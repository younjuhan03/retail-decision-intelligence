import numpy as np
import pandas as pd
import pytest
from retailos.reporting import policy_totals, forecast_totals


def test_pooled_rates_use_units_not_average_percentages():
    frame = pd.DataFrame([
        dict(policy='optimized', total_cost=10, procurement=5, holding_cost=1, lost_sales_penalty=4, unmet_units=1, proxy_units=2, ending_inventory=0, budget=10),
        dict(policy='optimized', total_cost=90, procurement=40, holding_cost=10, lost_sales_penalty=40, unmet_units=1, proxy_units=98, ending_inventory=3, budget=40)])
    row = policy_totals(frame).iloc[0]
    assert row.fill_rate == pytest.approx(.98)
    assert row.budget_utilization == pytest.approx(.9)
    assert row.total_cost == row.procurement + row.holding_cost + row.lost_sales_penalty


def test_forecast_rmse_uses_mean_squared_error_and_wape_uses_pooled_denominator():
    frame = pd.DataFrame([
        dict(model='rolling_mean', mae=1, mse=1, abs_error=2, actual_units=2, bias=1),
        dict(model='rolling_mean', mae=3, mse=9, abs_error=6, actual_units=98, bias=-1)])
    row = forecast_totals(frame).iloc[0]
    assert row.rmse == pytest.approx(np.sqrt(5))
    assert row.wape == pytest.approx(.08)
    assert row.bias == 0
