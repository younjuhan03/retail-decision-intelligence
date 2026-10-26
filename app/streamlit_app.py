"""Run: python -m streamlit run app/streamlit_app.py"""
from pathlib import Path
import sys
import json
import os
import pandas as pd
import streamlit as st
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from retailos.pipeline import evaluate_window

st.set_page_config(page_title='RetailOS | Inventory Intelligence', page_icon='◈', layout='wide')
st.markdown('''<style>.stApp{background:#f5f7fb}h1{letter-spacing:-1.5px}div[data-testid="stMetric"]{background:white;border:1px solid #dce4ef;padding:18px;border-radius:12px}.eyebrow{color:#2563eb;font-size:13px;font-weight:700;letter-spacing:3px}.hero{background:#102a43;color:white;border-radius:18px;padding:34px;margin-bottom:24px}.hero h1{color:white}.hero p{color:#bcd1e6}</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><div class="eyebrow">RETAILOS / DECISION INTELLIGENCE</div><h1>From forecasts to inventory decisions.</h1><p>Understand the cost of uncertainty. Allocate a shared budget. Review the evidence.</p></div>', unsafe_allow_html=True)
root = Path(__file__).resolve().parents[1]
output = Path(os.environ.get('RETAILOS_RESULTS', str(root / 'results/local')))
nav = st.sidebar.radio('Workspace', ['Executive Overview', 'Demand Intelligence', 'Inventory Optimizer', 'Scenario Lab', 'Policy Backtesting', 'AI Decision Review', 'Methodology & Limitations'])
st.sidebar.caption('Observed M5 sales • Assumed operations • Counterfactual costs')
if not (output / 'summary.json').exists():
    st.warning('DATA REQUIRED — official M5 results have not been computed.')
    c1, c2, c3 = st.columns(3)
    c1.metric('Data status', 'Awaiting M5')
    c2.metric('Decision status', 'HOLD')
    c3.metric('Business impact', 'Not evaluated')
    st.subheader('Connect the evidence before making a decision')
    st.write('Download the official M5 files from Kaggle after reviewing its access and usage terms. Place them in data/raw and run the pipeline. No artificial sales or savings are displayed.')
    st.code('python -m retailos.cli audit\npython -m retailos.cli run', language='powershell')
    st.link_button('Official M5 dataset', 'https://www.kaggle.com/competitions/m5-forecasting-accuracy/data')
    st.info('The quantitative engine and automated tests can run independently of an AI API. Actual model comparisons, order allocations and business findings require the official files.')
    st.stop()

@st.cache_data
def read_results(folder):
    p = Path(folder)
    return (json.loads((p / 'summary.json').read_text()), json.loads((p / 'config.json').read_text()),
            pd.read_parquet(p / 'forecasts.parquet'), pd.read_csv(p / 'policy_evaluation.csv'),
            pd.read_csv(p / 'forecast_metrics.csv'), pd.read_csv(p / 'sensitivity.csv'))

summary, cfg, forecasts, policies, metrics, sensitivity = read_results(str(output))
st.caption('All costs below are simulation estimates conditional on operating assumptions. No Walmart implementation or endorsement.')
origin = st.sidebar.selectbox('Held-out forecast origin (M5 day)', summary['test_origins'])
current = forecasts[forecasts.origin == origin]
calibration = forecasts[forecasts.origin.isin(cfg['origins'][:3])]
if nav == 'Executive Overview':
    st.subheader('Evidence, before action')
    c1, c2, c3 = st.columns(3)
    c1.metric('Product–store series', summary['series_count'])
    c2.metric('Selected forecast', summary['selected_model'])
    c3.metric('Measured 80% interval coverage', f"{summary['empirical_80pct_coverage']:.1%}")
    st.warning('REVIEW REQUIRED — limited calibration and held-out time blocks; operating assumptions require review.')
    st.dataframe(pd.DataFrame(summary['improvements']), hide_index=True, use_container_width=True)
    st.image(str(output / 'cost_composition.png'))
    st.write(summary['uncertainty_warning'])
elif nav == 'Demand Intelligence':
    sku = st.selectbox('Product–store', sorted(current.id.unique()))
    subset = current[current.id == sku].set_index('day')
    st.line_chart(subset[['sales', 'historical_mean', 'seasonal_naive', 'rolling_mean', 'gradient_boosting']])
    st.caption('Sales is the held-out observed-sales proxy, not unconstrained demand.')
    st.dataframe(metrics[(metrics.id == sku) & (metrics.origin == origin)], hide_index=True)
    intervals = pd.read_csv(output / 'interval_coverage.csv')
    st.line_chart(intervals[(intervals.id == sku) & (intervals.origin == origin)].set_index('day')[['lower_10', 'upper_90', 'observed_proxy']])
elif nav in ['Inventory Optimizer', 'Scenario Lab']:
    st.subheader('Change assumptions. Recompute the decision.')
    a, b, c = st.columns(3)
    ratio = a.slider('Budget / historical 28-day purchasing need', 0., 1.5, float(cfg['budget_ratio']), .05)
    penalty = b.slider('Unmet-proxy penalty / assumed unit cost', 0., 8., float(cfg['penalty_cost_multiple']), .5)
    lead = c.slider('Lead time (days)', 0, 28, int(cfg['lead_days']))
    initial = a.slider('Initial inventory (historical average days)', 0., 14., float(cfg['initial_days']), .5)
    holding = b.number_input('Daily holding cost / assumed unit cost', 0., .1, float(cfg['holding_daily_ratio']), .001, format='%.3f')
    uncertainty = c.slider('Residual uncertainty multiplier', 0., 2., float(cfg['uncertainty_scale']), .1)
    if st.button('Solve and compare policies', type='primary'):
        with st.spinner('Solving integer allocation and replaying the same held-out sales proxy…'):
            rows, alloc, decision, _ = evaluate_window(current, calibration, summary['selected_model'], cfg,
                {'budget_ratio': ratio, 'penalty_cost_multiple': penalty, 'lead_days': lead,
                 'initial_days': initial, 'holding_daily_ratio': holding, 'uncertainty_scale': uncertainty})
        st.warning(decision['review']['explanation'])
        st.dataframe(pd.DataFrame(rows), hide_index=True)
        st.dataframe(pd.DataFrame(alloc), hide_index=True)
        st.caption('The replay uses held-out sales only for evaluation. Recommendations use forecasts and earlier residuals.')
    if nav == 'Scenario Lab':
        st.subheader('Precomputed one-factor sensitivity')
        st.dataframe(sensitivity, hide_index=True, use_container_width=True)
elif nav == 'Policy Backtesting':
    st.subheader('Same budget. Same lead time. Same held-out proxy.')
    st.dataframe(policies, hide_index=True, use_container_width=True)
    st.bar_chart(policies.groupby('policy')[['procurement', 'holding_cost', 'lost_sales_penalty']].sum())
    st.caption('Each window resets to the same assumed inventory. This is a repeated episode study, not continuous Walmart replenishment history.')
elif nav == 'AI Decision Review':
    st.subheader('Grounded review • deterministic mode')
    decisions = json.loads((output / 'decisions.json').read_text())
    decision = next(x for x in decisions if x['origin'] == origin)
    st.warning(decision['review']['explanation'])
    st.json(decision)
    st.write('Advisor: explains verified spend and constraints. Challenger: flags limited evidence and assumed inputs. Coordinator: uses the same validated status. No LLM or invented confidence score is used.')
else:
    st.subheader('What this experiment can establish')
    st.markdown((root / 'docs/methodology.md').read_text())
