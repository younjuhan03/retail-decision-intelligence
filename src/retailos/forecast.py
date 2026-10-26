"""Direct 28-day global forecasts: each training row has an explicit as-of origin."""
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from threadpoolctl import threadpool_limits

MODELS = ['historical_mean', 'seasonal_naive', 'rolling_mean', 'gradient_boosting']
FEATURES = ['sku', 'horizon', 'dow', 'month', 'event', 'mean7', 'mean28', 'mean84', 'std28', 'zero28', 'seasonal', 'price_asof']


def features(panel, calendar, origin, horizon=28, allow_partial=False):
    if origin < 84 or horizon != 28:
        raise ValueError('At least 84 history days and exactly 28 forecast days required')
    future = calendar.set_index('day').reindex(range(origin + 1, origin + horizon + 1))
    if future.date.isna().any():
        raise ValueError('Calendar does not cover horizon')
    rows = []
    for sku, (key, group) in enumerate(panel.groupby('id', sort=True)):
        hist = group[group.day <= origin].sort_values('day')
        listed = hist[hist.sell_price.notna()]
        if listed.empty and allow_partial:
            continue
        if listed.empty:
            raise ValueError(f'No as-of price for {key} at day {origin}')
        # Never compute activation from a future first sale or future first price.
        active = hist[hist.day >= listed.day.min()]
        y = active.sales.to_numpy(dtype=float)
        if len(y) < 84 and allow_partial:
            continue
        if len(y) < 84:
            raise ValueError(f'Insufficient active history for {key} at day {origin}')
        for h in range(1, horizon + 1):
            c = future.loc[origin + h]
            rows.append({'id': key, 'origin': origin, 'day': origin + h,
                         'sku': sku, 'horizon': h, 'dow': c.date.dayofweek, 'month': c.date.month,
                         'event': int(pd.notna(c.event_name_1)),
                         'mean7': y[-7:].mean(), 'mean28': y[-28:].mean(), 'mean84': y[-84:].mean(),
                         'std28': y[-28:].std(), 'zero28': (y[-28:] == 0).mean(),
                         'seasonal': y[-7 + (h - 1) % 7], 'price_asof': float(listed.sell_price.iloc[-1]),
                         'historical_mean': y.mean(), 'seasonal_naive': y[-7 + (h - 1) % 7], 'rolling_mean': y[-28:].mean()})
    return pd.DataFrame(rows)


def predict(panel, calendar, origin, horizon=28, seed=42):
    # Training targets end at or before origin. No recursive use of actual intermediate targets.
    training = []
    for train_origin in range(max(365, origin - 560), origin - horizon + 1, horizon):
        f = features(panel, calendar, train_origin, horizon, allow_partial=True)
        if f.empty:
            continue
        f = f.merge(panel[['id', 'day', 'sales']], on=['id', 'day'], validate='one_to_one')
        if f.day.max() > origin:
            raise AssertionError('Training target crosses forecast origin')
        training.append(f)
    if not training:
        raise ValueError('No complete active training examples')
    train = pd.concat(training, ignore_index=True)
    out = features(panel, calendar, origin, horizon)
    model = HistGradientBoostingRegressor(loss='poisson', max_iter=80, max_leaf_nodes=15,
                                         l2_regularization=1.0, early_stopping=False, random_state=seed)
    with threadpool_limits(limits=2):
        model.fit(train[FEATURES], train.sales)
        out['gradient_boosting'] = np.maximum(0, model.predict(out[FEATURES]))
    out = out.merge(panel[['id', 'day', 'sales']], on=['id', 'day'], validate='one_to_one')
    if out.sales.isna().any():
        raise ValueError('Missing held-out observations')
    return out, model


def score(predictions, panel):
    rows = []
    for (origin, key), g in predictions.groupby(['origin', 'id']):
        history = panel[(panel.id == key) & (panel.day <= origin)].sort_values('day')
        ytrain = history.sales.to_numpy(dtype=float)
        nz = np.flatnonzero(ytrain)
        ytrain = ytrain[nz[0]:] if len(nz) else np.array([])
        scale = np.mean(np.diff(ytrain) ** 2) if len(ytrain) > 1 else np.nan
        zero_share = (history.sales.tail(84) == 0).mean()
        for model in MODELS:
            err = g[model].to_numpy() - g.sales.to_numpy()
            rows.append({'origin': int(origin), 'id': key, 'model': model,
                         'segment': 'intermittent' if zero_share >= .5 else 'regular',
                         'mae': np.abs(err).mean(), 'mse': np.square(err).mean(), 'rmse': np.sqrt(np.square(err).mean()),
                         'abs_error': np.abs(err).sum(), 'actual_units': g.sales.sum(),
                         'wape': np.abs(err).sum() / g.sales.sum() if g.sales.sum() > 0 else np.nan,
                         'bias': err.mean(), 'rmsse': np.sqrt(np.square(err).mean() / scale) if scale > 0 else np.nan})
    return pd.DataFrame(rows)


def residual_paths(predictions, model, ids, before_origin, count=8, scale=1.0, seed=42):
    eligible = predictions[predictions.origin + 28 <= before_origin]
    blocks = []
    for _, g in eligible.groupby('origin', sort=True):
        ordered = g.sort_values(['id', 'day'])
        if list(ordered.id.unique()) != list(ids) or len(ordered) != len(ids) * 28:
            raise ValueError('Incomplete residual block')
        blocks.append((ordered.sales - ordered[model]).to_numpy().reshape(len(ids), 28))
    if not blocks:
        raise ValueError('No earlier out-of-sample residual blocks; uncertainty unavailable')
    rng = np.random.default_rng(seed)
    # Whole-origin, all-SKU paths preserve observed within-block temporal and cross-SKU dependence.
    return np.stack([blocks[j] * scale for j in rng.integers(0, len(blocks), count)])
