"""Official-file loader. No network fallback, imputation of sales, or synthetic data."""
from pathlib import Path
import hashlib
import sqlite3
import numpy as np
import pandas as pd

META = ['id', 'item_id', 'dept_id', 'cat_id', 'store_id', 'state_id']


def require_columns(frame, names, label):
    missing = set(names) - set(frame.columns)
    if missing:
        raise ValueError(f'{label}: missing columns {sorted(missing)}')


def load_m5(root, config):
    root = Path(root)
    sales_path = root / 'sales_train_evaluation.csv'
    required = [sales_path, root / 'calendar.csv', root / 'sell_prices.csv']
    for p in required:
        if not p.is_file():
            raise FileNotFoundError(f'Missing official M5 file: {p}. Download from Kaggle; no substitute is used.')
    cal = pd.read_csv(root / 'calendar.csv')
    require_columns(cal, ['d', 'date', 'wm_yr_wk', 'event_name_1'], 'calendar')
    if cal.d.duplicated().any():
        raise ValueError('Duplicate calendar day')
    cal['day'] = cal.d.str.removeprefix('d_').astype(int)
    cal['date'] = pd.to_datetime(cal.date, errors='raise')
    cal = cal.sort_values('day')
    if cal[['day', 'date', 'wm_yr_wk']].isna().any().any():
        raise ValueError('Missing calendar key')
    if not np.array_equal(cal.day.to_numpy(), np.arange(1, len(cal) + 1)):
        raise ValueError('Calendar days must be contiguous from d_1')
    if not cal.date.diff().dropna().eq(pd.Timedelta(days=1)).all():
        raise ValueError('Non-contiguous calendar dates')
    # Filter while wide: avoids melting 59 million rows.
    chunks = []
    for chunk in pd.read_csv(sales_path, chunksize=512):
        require_columns(chunk, META, 'sales')
        chunk = chunk[chunk.store_id.isin(config['stores'])]
        chunks.append(chunk)
    sales = pd.concat(chunks, ignore_index=True)
    if sales.empty or sales.id.duplicated().any():
        raise ValueError('Empty selection or duplicate series IDs')
    days = sorted([c for c in sales if c.startswith('d_')], key=lambda x: int(x[2:]))
    if days != [f'd_{i}' for i in range(1, len(days) + 1)]:
        raise ValueError('Sales days must be contiguous')
    if len(days) < max(config['origins']) + config['horizon']:
        raise ValueError('Insufficient evaluation-file history for configured windows')
    values = sales[days].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any() or not np.equal(values, np.floor(values)).all():
        raise ValueError('Sales must be finite nonnegative integers; never imputed')
    cutoff = min(config['origins'])
    # A price-listing week must start at least 83 days before the first origin,
    # providing >=84 calendar days of active history. Determine eligibility
    # before selecting ranks; use no post-origin sales or future price weeks.
    early_weeks = set(cal.loc[cal.day <= cutoff - 83, 'wm_yr_wk'])
    eligible_keys = set()
    for price_chunk in pd.read_csv(root / 'sell_prices.csv', chunksize=100000):
        require_columns(price_chunk, ['store_id', 'item_id', 'wm_yr_wk', 'sell_price'], 'prices')
        early = price_chunk[price_chunk.store_id.isin(config['stores'])
                            & price_chunk.wm_yr_wk.isin(early_weeks)
                            & price_chunk.sell_price.gt(0)]
        eligible_keys.update(zip(early.store_id, early.item_id))
    eligibility = [(store, item) in eligible_keys for store, item in zip(sales.store_id, sales.item_id)]
    excluded_short_history = int(len(sales) - sum(eligibility))
    sales = sales.copy()  # consolidate wide chunks before adding feature columns
    sales['training_mean'] = values[:, cutoff - 364:cutoff].mean(axis=1)
    sales['zero_share'] = (values[:, cutoff - 364:cutoff] == 0).mean(axis=1)
    sales = sales.loc[eligibility].copy()
    # Within store/department: sort on training zero-share, then training volume,
    # select evenly spaced ranks (including the intermittent and regular ends).
    chosen = []
    for _, group in sales.groupby(['store_id', 'dept_id'], sort=True):
        group = group[group.training_mean > 0].sort_values(['zero_share', 'training_mean', 'id'])
        if len(group):
            idx = np.unique(np.linspace(0, len(group) - 1, min(config['per_store_department'], len(group))).astype(int))
            chosen.append(group.iloc[idx])
    if not chosen:
        raise ValueError('No active positive-sales candidates')
    sales = pd.concat(chosen).sort_values('id').reset_index(drop=True)
    prices = []
    keys = set(zip(sales.store_id, sales.item_id))
    for p in pd.read_csv(root / 'sell_prices.csv', chunksize=100000):
        require_columns(p, ['store_id', 'item_id', 'wm_yr_wk', 'sell_price'], 'prices')
        mask = [(s, i) in keys for s, i in zip(p.store_id, p.item_id)]
        prices.append(p.loc[mask])
    prices = pd.concat(prices, ignore_index=True)
    if prices.duplicated(['store_id', 'item_id', 'wm_yr_wk']).any():
        raise ValueError('Duplicate price key')
    if not np.isfinite(prices.sell_price).all() or (prices.sell_price <= 0).any():
        raise ValueError('Invalid unit selling price')
    long = sales[META + days].melt(id_vars=META, var_name='d', value_name='sales')
    long = long.merge(cal[['d', 'day', 'date', 'wm_yr_wk', 'event_name_1']], on='d', how='left', validate='many_to_one')
    long = long.merge(prices, on=['store_id', 'item_id', 'wm_yr_wk'], how='left', validate='many_to_one')
    if long[['day', 'date']].isna().any().any():
        raise ValueError('Missing calendar joins')
    # Activation proxy: first listed price, computed separately at each origin by features().
    # Missing price is preserved, never backfilled from future weeks.
    with sqlite3.connect(':memory:') as con:
        long[['id', 'day', 'sales', 'sell_price']].to_sql('sales', con, index=False)
        audit = pd.read_sql_query('SELECT COUNT(*) AS rows, SUM(CASE WHEN sell_price IS NULL THEN 1 ELSE 0 END) AS missing_price_rows, SUM(CASE WHEN sales>0 AND sell_price IS NULL THEN 1 ELSE 0 END) AS positive_sales_without_price FROM sales', con).iloc[0].to_dict()
    if audit['positive_sales_without_price']:
        raise ValueError('Positive sales without matching price; inspect official files')
    manifest = {'source': 'https://www.kaggle.com/competitions/m5-forecasting-accuracy/data', 'files': {}, 'audit': audit,
                'selected_series': len(sales), 'selection_cutoff_day': cutoff,
                'minimum_active_history_days': 84, 'excluded_short_history_candidates': excluded_short_history,
                'eligibility_rule': 'At least one listed-price week starts on or before first_origin minus 83 days; selection uses only origin-available history.', 'missing_prices': 'Preserved; origin features use only last observed price.'}
    for p in required:
        digest = hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                digest.update(block)
        manifest['files'][p.name] = {'sha256': digest.hexdigest(), 'bytes': p.stat().st_size}
    validation = root / 'sales_train_validation.csv'
    if validation.exists():
        # Optional earlier release must agree with the evaluation release on shared days.
        v = pd.read_csv(validation)
        v['id'] = v.id.str.replace('_validation$', '_evaluation', regex=True)
        v = v.set_index('id').reindex(sales.id)
        common = [c for c in days if c in v]
        if v[common].isna().any().any() or not np.array_equal(v[common].to_numpy(), sales[common].to_numpy()):
            raise ValueError('Validation and evaluation sales releases disagree')
        manifest['validation_release_check'] = 'Shared selected-series observations identical'
    return long.sort_values(['id', 'day']).reset_index(drop=True), sales[META + ['training_mean', 'zero_share']], cal, manifest
