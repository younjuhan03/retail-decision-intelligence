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
    # Aggregate exporter is independently replayed before public evidence is written.
    import importlib.util
    module_path = Path(__file__).parents[1] / 'scripts/export_evidence.py'
    spec = importlib.util.spec_from_file_location('evidence_export', module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    export_dir = tmp_path / 'exported_docs'
    evidence = module.export(output, export_dir)
    assert evidence['independently_replayed_policy_windows'] == 6
    assert (export_dir / 'case_study.html').is_file()
    assert (export_dir / 'evidence/first_run.json').is_file()
    assert not list(export_dir.rglob('*.parquet'))
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


def test_late_activation_excluded_before_rank_selection(tmp_path, tiny_panel):
    raw, cfg = official_shape_fixture(tmp_path, tiny_panel)
    prices = pd.read_csv(raw / 'sell_prices.csv')
    late_week = (min(cfg['origins']) - 60) // 7
    prices = prices[(prices.item_id != 'fixture_1') | (prices.wm_yr_wk >= late_week)]
    prices.to_csv(raw / 'sell_prices.csv', index=False)
    sales = pd.read_csv(raw / 'sales_train_evaluation.csv')
    early_days = [f'd_{i}' for i in range(1, late_week * 7 + 1)]
    sales.loc[sales.item_id == 'fixture_1', early_days] = 0
    sales.to_csv(raw / 'sales_train_evaluation.csv', index=False)
    panel, selected, cal, manifest = load_m5(raw, cfg)
    assert list(selected.item_id) == ['fixture_0']
    assert manifest['excluded_short_history_candidates'] == 1
    from retailos.forecast import features
    assert len(features(panel, cal, min(cfg['origins']))) == 28


def test_expanded_comparison_four_policies(tmp_path, tiny_panel, monkeypatch):
    raw, cfg = official_shape_fixture(tmp_path, tiny_panel)
    cfg.update(origins=[1605, 1633, 1661, 1689, 1717, 1745, 1773, 1801],
               calibration_count=4, include_point_optimizer=True, run_sensitivity=False,
               evaluation_role='exploratory retrospective comparison')
    out = tmp_path / 'comparison'
    summary = run(raw, out, cfg)
    assert summary['calibration_origins'] == [1605, 1633, 1661, 1689]
    assert summary['selection_origin'] == 1717
    assert summary['test_origins'] == [1745, 1773, 1801]
    results = pd.read_csv(out / 'policy_evaluation.csv')
    assert len(results) == 12
    assert set(results.policy) == {'historical_average', 'forecast_order_up_to', 'point_optimized', 'optimized'}
    assert (results.procurement <= results.budget + 1e-6).all()
    assert np.allclose(results.total_cost, results.procurement + results.holding_cost + results.lost_sales_penalty)
    comparison = pd.read_csv(out / 'policy_comparison.csv')
    assert len(comparison) == 4
    assert comparison.paired_windows.eq(3).all()
    assert pd.read_csv(out / 'sensitivity.csv').variant.eq('base').all()
    from streamlit.testing.v1 import AppTest
    monkeypatch.setenv('RETAILOS_RESULTS', str(out))
    app = AppTest.from_file(str(Path(__file__).parents[1] / 'app/streamlit_app.py'), default_timeout=60).run()
    assert not app.exception
    app.sidebar.radio[0].set_value('Inventory Optimizer').run()
    app.button[0].click().run()
    assert not app.exception



def test_point_orders_ignore_future_sales(tiny_panel):
    from retailos.forecast import predict
    from retailos.pipeline import evaluate_window
    panel, cal = tiny_panel
    cfg = json.loads((Path(__file__).parents[1] / 'configs/compact.json').read_text())
    cfg.update(include_point_optimizer=True, scenario_count=2)
    past, _ = predict(panel, cal, 1773)
    pred, _ = predict(panel, cal, 1885)
    _, first, _, _ = evaluate_window(pred, past, 'rolling_mean', cfg)
    changed = pred.copy()
    changed['sales'] = changed.sales + 100
    _, second, _, _ = evaluate_window(changed, past, 'rolling_mean', cfg)
    for policy in ['point_optimized', 'optimized']:
        assert [r['order_units'] for r in first if r['policy'] == policy] == [r['order_units'] for r in second if r['policy'] == policy]
