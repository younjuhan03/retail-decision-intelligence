"""Artificial fixtures only for software verification, never primary M5 evidence."""
import numpy as np
import pandas as pd
import pytest

@pytest.fixture
def tiny_panel():
    days = np.arange(1, 1942)
    dates = pd.date_range('2011-01-29', periods=len(days))
    cal = pd.DataFrame({'d': [f'd_{x}' for x in days], 'day': days, 'date': dates, 'wm_yr_wk': (days - 1) // 7, 'event_name_1': np.nan})
    panels = []
    for i in range(2):
        p = cal.copy()
        p['id'] = f'fixture_{i}_evaluation'; p['sales'] = (days % 7 + i) % 5
        p['sell_price'] = 2. + i
        p['store_id'] = 'TX_1'; p['item_id'] = f'fixture_{i}'
        panels.append(p)
    return pd.concat(panels), cal
