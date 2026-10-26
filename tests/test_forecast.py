import numpy as np
import pandas as pd
import pytest
from retailos.forecast import features, predict, score, residual_paths, MODELS


def test_origin_features_ignore_all_future_observations(tiny_panel):
    panel, cal = tiny_panel
    original = features(panel, cal, 1000)
    changed = panel.copy()
    changed.loc[changed.day > 1000, ['sales', 'sell_price']] = 99999.
    pd.testing.assert_frame_equal(original, features(changed, cal, 1000))
    assert len(original) == 56 and set(original.horizon) == set(range(1, 29))


def test_model_forecast_is_invariant_to_future_sales_and_prices(tiny_panel):
    panel, cal = tiny_panel
    pred, _ = predict(panel, cal, 1000)
    changed = panel.copy()
    changed.loc[changed.day > 1000, ['sales', 'sell_price']] = 9999.
    second, _ = predict(changed, cal, 1000)
    np.testing.assert_array_equal(pred.gradient_boosting, second.gradient_boosting)
    assert (pred[MODELS] >= 0).all().all()
    metrics = score(pred, panel)
    assert set(metrics.model) == set(MODELS) and np.isfinite(metrics.mae).all()


def test_missing_origin_price_fails(tiny_panel):
    panel, cal = tiny_panel
    panel.loc[panel.day <= 1000, 'sell_price'] = np.nan
    with pytest.raises(ValueError, match='as-of price'):
        features(panel, cal, 1000)


def test_residuals_use_completed_earlier_windows_only(tiny_panel):
    panel, cal = tiny_panel
    pred, _ = predict(panel, cal, 1000)
    ids = sorted(panel.id.unique())
    with pytest.raises(ValueError, match='No earlier'):
        residual_paths(pred, 'rolling_mean', ids, 1027)
    r = residual_paths(pred, 'rolling_mean', ids, 1028)
    np.testing.assert_array_equal(r, residual_paths(pred, 'rolling_mean', ids, 1028))
    assert r.shape == (8, 2, 28)


def test_horizon_guard(tiny_panel):
    with pytest.raises(ValueError):
        features(*tiny_panel, 1000, horizon=7)
