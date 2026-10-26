"""Artificial official-schema fixtures; no reported business evidence."""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import pytest
from retailos.data import load_m5
from retailos.pipeline import run


def official_shape_fixture(tmp_path, tiny_panel):
    panel, cal = tiny_panel
    raw = tmp_path / 'raw'; raw.mkdir()
    cal.drop(columns='day').to_csv(raw / 'calendar.csv', index=False)
    sales = panel.pivot(index='id', columns='d', values='sales')
    sales = sales[[f'd_{i}' for i in range(1, 1942)]].reset_index()
    for col, val in {'dept_id':'FOODS_1', 'cat_id':'FOODS', 'store_id':'TX_1', 'state_id':'TX'}.items():
        sales[col] = val
    sales['item_id'] = [f'fixture_{i}' for i in range(len(sales))]
    sales.to_csv(raw / 'sales_train_evaluation.csv', index=False)
    prices = panel[['store_id', 'item_id', 'wm_yr_wk', 'sell_price']].drop_duplicates()
    prices.to_csv(raw / 'sell_prices.csv', index=False)
    cfg = json.loads((Path(__file__).parents[1] / 'configs/compact.json').read_text())
    cfg['stores'] = ['TX_1']; cfg['scenario_count'] = 2
    return raw, cfg


def test_source_missing_is_hard_blocker(tmp_path):
    with pytest.raises(FileNotFoundError, match='official M5'):
        load_m5(tmp_path, {})


def test_schema_joins_and_duplicate_price_detection(tmp_path, tiny_panel):
    raw, cfg = official_shape_fixture(tmp_path, tiny_panel)
    panel, selected, cal, manifest = load_m5(raw, cfg)
    assert len(panel) == 2 * 1941
    assert manifest['audit']['missing_price_rows'] == 0
    assert not panel.duplicated(['id', 'day']).any()
    assert len(selected) == 2
    price = pd.read_csv(raw / 'sell_prices.csv')
    pd.concat([price, price.iloc[:1]]).to_csv(raw / 'sell_prices.csv', index=False)
    with pytest.raises(ValueError, match='Duplicate price'):
        load_m5(raw, cfg)


def test_full_pipeline_on_artificial_schema_fixture(tmp_path, tiny_panel, monkeypatch):
    raw, cfg = official_shape_fixture(tmp_path, tiny_panel)
    output = tmp_path / 'fixture_outputs'
    summary = run(raw, output, cfg)
    assert summary['test_origins'] == [1885, 1913]
    for filename in ['case_study.html', 'cost_composition.png', 'provenance.json']:
        assert (output / filename).exists()
    results = pd.read_csv(output / 'policy_evaluation.csv')
    assert set(results.policy) == {'optimized', 'historical_average', 'forecast_order_up_to'}
    assert len(results) == 6
    assert np.allclose(results.total_cost, results.procurement + results.holding_cost + results.lost_sales_penalty)
    assert (results.procurement <= results.budget + 1e-6).all()
    assert (results.fill_rate.between(0, 1)).all()
    assert all(d['review']['status'] in ['REVIEW REQUIRED', 'HOLD'] for d in json.loads((output / 'decisions.json').read_text()))
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('RETAILOS_RESULTS', str(output))
    app_path = str(Path(__file__).parents[1] / 'app/streamlit_app.py')
    for nav in ['Executive Overview', 'Demand Intelligence', 'Inventory Optimizer', 'Scenario Lab', 'Policy Backtesting', 'AI Decision Review', 'Methodology & Limitations']:
        app = AppTest.from_file(app_path, default_timeout=60).run()
        app.sidebar.radio[0].set_value(nav).run()
        if nav == 'Inventory Optimizer':
            app.button[0].click().run()
        assert not app.exception, [x.message for x in app.exception]


def test_app_honest_empty_state(tmp_path, monkeypatch):
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('RETAILOS_RESULTS', str(tmp_path / 'missing'))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app/streamlit_app.py')).run()
    assert not app.exception
    assert 'DATA REQUIRED' in app.warning[0].value
    assert app.metric[1].value == 'HOLD'


def test_missing_schema_column_is_rejected(tmp_path, tiny_panel):
    raw, cfg = official_shape_fixture(tmp_path, tiny_panel)
    pd.read_csv(raw / 'calendar.csv').drop(columns='date').to_csv(raw / 'calendar.csv', index=False)
    with pytest.raises(ValueError, match='missing columns'):
        load_m5(raw, cfg)


def test_negative_observed_sales_rejected(tmp_path, tiny_panel):
    raw, cfg = official_shape_fixture(tmp_path, tiny_panel)
    sales = pd.read_csv(raw / 'sales_train_evaluation.csv')
    sales.loc[0, 'd_100'] = -1
    sales.to_csv(raw / 'sales_train_evaluation.csv', index=False)
    with pytest.raises(ValueError, match='nonnegative integers'):
        load_m5(raw, cfg)


def test_validation_release_must_agree(tmp_path, tiny_panel):
    raw, cfg = official_shape_fixture(tmp_path, tiny_panel)
    sales = pd.read_csv(raw / 'sales_train_evaluation.csv')
    sales['id'] = sales.id.str.replace('_evaluation', '_validation', regex=False)
    sales.loc[0, 'd_100'] = 99
    sales.to_csv(raw / 'sales_train_validation.csv', index=False)
    with pytest.raises(ValueError, match='releases disagree'):
        load_m5(raw, cfg)
