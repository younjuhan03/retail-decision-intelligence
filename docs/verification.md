# Verification report — 2026-10-26

## Current verdict

**The first official-data study and local application run are complete. The optimizer remains REVIEW REQUIRED.** Gradient boosting improved point-forecast MAE, but scenario optimization did not improve the evaluated base-case inventory cost. This release documents that result and corrects display scope; it does not claim a better ordering algorithm.

## Evidence and verification boundaries

| Check | Evidence / result |
|---|---|
| Original official-data run | User executed the pipeline on Windows, Python 3.14.6; the complete `local2.zip` result archive was inspected |
| Real-data scope | 42 product–store series, 81,522 selected historical rows, two 28-day test episodes, 2,352 held-out SKU-days |
| Independent accounting replay | All six saved policy-window total costs reproduced; integer allocation and budget checks passed |
| Aggregate evidence export | Executed against the supplied official-data results; generates charts, JSON/CSV summaries and English case study |
| Baseline GitHub CI | Initial commit `cf931743482dc1ae0c50931419bb6cfd5798683b` completed successfully on GitHub Actions |
| Current software tests | 33 automated tests in the current revision; see test run evidence and live CI status below |
| Actual app screenshots | Captured from this revision's running Streamlit app using the inspected real results, not a mockup |
| Browser inspection | Executive overview and selected-window backtesting opened without an application exception |
| Missing-data state | Still displays DATA REQUIRED / HOLD when a fresh clone has no locally computed results |
| Raw-data exclusion | Source CSVs, processed Parquet, detailed SKU outputs, credentials and virtual environments remain outside the public commit |

The original result archive records NumPy 2.5.4, pandas 3.1.0, SciPy 1.18.1 and scikit-learn 1.9.1 on Python 3.14.6. These versions are reported by the original run, not claimed as the versions used for every subsequent verification. Aggregate evidence includes source-result hashes. The official CSVs themselves were not uploaded to this execution environment; training was not independently repeated on the complete raw files here.

The original Windows test screenshot showed 30 passing tests before the activation regression test and reporting tests were added. Current fixture tests cover the pipeline, deterministic decisions and all seven app sections. Fixture metrics are not used as project findings. They cannot prove forecast quality or business benefit.

Live checks: [GitHub Actions](https://github.com/younjuhan03/retail-decision-intelligence/actions/workflows/tests.yml). Only a successful run for the corresponding commit establishes that commit's CI status; the badge is not a claim about an unexecuted future revision.

## What changed after the first experiment

- Recorded actual first-run errors, simulated policy costs, uncertainty coverage and sensitivity findings.
- Added aggregate evidence export with a separate physical accounting replay.
- Renamed displayed policy labels to distinguish trailing-average orders from the all-history mean forecast.
- Replaced the ambiguous "80% interval coverage" label with "10–90% scenario-envelope coverage"; the legacy JSON key is retained for compatibility.
- Explicitly labeled the overview as pooled across all test episodes; backtesting and scenario detail tables now follow the selected origin.
- Disabled the detail-origin selector on the pooled overview.
- Added a regression test for late activation and tests for pooled display rates and forecast error aggregation.
- Replaced the pending case-study placeholder with an evidence-populated, print-aware English HTML page. No model retraining or test-period parameter tuning was performed.

## Remaining limitations

1. The optimizer's modeled cost is 11.97% above trailing-average orders and 11.60% above forecast order-up-to under the base assumptions. Do not label this as cost savings.
2. Three unique calibration time blocks and two held-out episodes are insufficient for robust tail-risk or population-effect claims. The scenario envelope's measured coverage is 38.52%, not evidence of calibrated 80% protection.
3. Inventory, purchase costs, shortages, budget and lead time are assumed. Observed sales can be demand-censored. Zero salvage and episode resets simplify operations.
4. Current competition data redistribution permissions remain unverified. The repository provides aggregate research summaries and original figures; this does not license or redistribute the M5 source data. Review source terms before adding any other assets.
5. The source snapshot and already-inspected final windows must be preserved. Revised methods need development-period selection and a clearly designated new holdout before a fresh confirmation claim.
6. No live external app deployment, production order placement, optional LLM provider or autonomous agent ordering is implemented.

## Completed bounded follow-up

The [17-window retrospective comparison](comparison_results.md) was supplied as a local Windows result archive. Independent daily replay matched all 68 policy-window costs and checked integer orders, budget feasibility, unmet units and ending inventory. This does not independently retrain from raw files. The updated app and matched-window display are covered by software tests; original V1 artifacts remain preserved.
