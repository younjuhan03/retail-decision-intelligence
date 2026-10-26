# Bounded follow-up comparison (not yet computed on official data)

Purpose: distinguish forecast-based proportional ordering, cost-aware point optimization, and scenario optimization across more historical windows. This is a retrospective diagnostic, not a promise of improved cost or a fresh holdout. Preserve the original published study and do not overwrite results/local.

## Frozen configuration

Use configs/comparison.json. It selects the same number of series (up to 42) using information available at its earlier first origin d_1101. Consequently the selected products can differ from V1; compare the four policies within this run, not its totals against V1 totals.

- Forecast origins: d_1101 through d_1913, spaced 28 days (30 origins).
- First 12 origins (d_1101–d_1409): frozen residual pool.
- d_1437: select the forecast model by MAE; no cost-based retuning in this bounded experiment.
- Remaining 17 origins (d_1465–d_1913): retrospective evaluation, including the two previously inspected V1 windows.
- Fixed scenario count/seed and economic assumptions match V1. Twelve residual blocks still do not establish calibrated uncertainty; eight sampled paths need not contain every block.
- Four policies: trailing-average orders, forecast order-up-to, point-forecast optimized orders, scenario-optimized orders. Both optimizers use the same cost objective and constraints; only demand paths differ.
- Sensitivity reruns are disabled to keep this follow-up bounded. No automated parameter search or favorable-assumption selection.

Product selection and model development already benefited from knowledge of V1. Earlier time windows are therefore not a genuinely untouched test. Shared products, histories and seasons also make window outcomes dependent. Do not infer statistical significance from the number of SKU-days.

## Run on Windows

From the project folder, with the existing official CSVs in data/raw:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m retailos.cli run --config configs/comparison.json --out results/comparison_v2
```

Use a new output directory if comparison_v2 already contains a run you want to preserve. Training 30 origins and solving four policies will take longer than V1; runtime depends on the computer. A missing or ineligible dataset is a visible blocker, never replaced by artificial sales.

Review policy_comparison.csv (positive cost_increase_fraction means worse than baseline), policy_evaluation.csv (window costs and fill rates), allocations.csv, summary.json, decisions.json and selected_series.csv. Solver failure omits that optimizer's allocation; inspect solver statuses and paired_windows rather than treating a missing result as success. The point optimizer's status is recorded separately in decisions.json. All results remain human-review-only.

To inspect the app against this separate run:

```powershell
$env:RETAILOS_RESULTS = "results/comparison_v2"
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

For review here, stop any process using output files and zip the local result folder:

```powershell
Compress-Archive -Path results/comparison_v2/* -DestinationPath comparison_v2.zip
```

Do not commit raw data or detailed outputs. Do not run scripts/export_evidence.py on V2: that exporter is tailored to the first published study and would overwrite its public evidence.

## Decision and stopping rule

Report paired total costs, cost differences per window, lower-cost window counts, fill rate, remaining stock and solver availability. If point optimization beats scenario optimization, that supports investigating uncertainty construction but does not isolate a unique cause. If neither beats simple ordering consistently, retain the simple benchmark and close this experiment. Preserve negative findings. No additional methods are added merely to obtain a positive headline.

Tests on artificial fixtures establish software behavior only. Official-data results for this follow-up are pending local execution; no new performance claim is made.
