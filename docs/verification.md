# Final verification report — 2026-10-26

## Verdict

**Software implementation delivered; empirical project remains incomplete until official M5 data is supplied and executed.** Do not call this a finished M5 impact study or submit simulated fixture findings as business results.

## Executed checks

| Check | Observed outcome |
|---|---|
| `python -m pip install -e '.[dev]'` | Successful editable package installation |
| `python -m pytest -q` | **30 passed in 8.14 seconds** on the final tested code |
| `python -m compileall -q src app` | Successful compilation |
| CLI audit with no data | Expected exit code 2, names missing official sales file; no fallback |
| Actual Streamlit server start | Successful; localhost health endpoint returned HTTP 200 `ok`, root returned HTTP 200 HTML |
| Streamlit AppTest | Seven navigation sections and scenario solve exercised on artificial official-schema fixtures; missing-data HOLD state exercised separately |
| Complete pipeline | Executed using artificial two-SKU official-schema fixtures in pytest temporary directories, including training, policy replay, sensitivity, Parquet, CSV, chart and HTML generation |
| Optimizer correctness | Objective and replay compared with exhaustive feasible integer enumeration on a tiny scenario problem |
| Cost accounting | Independently hand-checked daily arrival, stock, shortage and holding arithmetic |
| Leakage checks | Future sales/prices altered; origin features and ML forecasts unchanged |
| Edge cases | Zero budget/sales, empty candidates, huge demand, delayed arrival, negative/non-finite data, infeasible minimum orders, solver timeout, invalid orders |
| Data checks | Missing schema fields, duplicate price keys, negative sales and validation-release disagreements rejected |
| Grounded review | APPROVE/HOLD/REVIEW REQUIRED/INFEASIBLE checked; numeric spend matches orders |

Fixture results are not bundled as project evidence. Fixture tests validate program behavior, not M5 accuracy, real-data compatibility at scale, business benefit or statistical robustness. Testing was performed on Linux with Python 3.12; Windows commands and Python 3.11 CI configuration have not been executed on their target platforms here. The GitHub Actions file is provided but has not run on GitHub.

## Actual blockers / unresolved work

1. Official Kaggle list and download API probes returned HTTP 401; credentials were not configured. The final real M5 pipeline, model comparisons, subset quality audit and quantitative business conclusions have not run.
2. Official competition rules were not readable through the retrieval path. Current data-use/redistribution permissions are unverified. Raw/derived data is excluded from the repository; publishing outputs requires checking the applicable terms.
3. Browser-based screenshot capture is incomplete. Playwright's Chromium archive download failed; no screenshot or fabricated UI image is supplied. AppTest and actual HTTP startup checks do not replace pixel-level visual QA.
4. The result-populated case study is generated only after real-data execution. `docs/case_study_pending.html` is an honest interim implementation brief. Resume bullets describe software accomplishments only.
5. Default evaluation has only three calibration blocks and two held-out test blocks. Review remains required, even after a successful run; no inferential confidence interval or calibrated uncertainty claim is supplied.
6. Scenario optimization runtime, missing price patterns and activation eligibility on the full official dataset remain unbenchmarked. Late activation fails explicitly if insufficient history is available; no silent replacement occurs.
7. External GitHub publication, cloud deployment, real order placement and optional LLM integration were not performed. Deterministic quantitative/review mode is implemented.

## Scope of release

Included: source, automatic tests, compact configuration, README, software license excluding third-party data, Windows instructions, data dictionary/lineage, mathematical methodology, deployment guide, feasibility audit, honest interim English HTML brief and result-page generator, implementation-only resume draft.

Next action: download the official archive using your own Kaggle account after reviewing its terms, then supply the archive or required CSVs. No API credential needs to be disclosed. Run the audit first; only then run and inspect the primary analysis, sensitivity tables and real app screenshots.
