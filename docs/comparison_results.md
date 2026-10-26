# Follow-up results: point forecasts versus scenario optimization

Status: computed; HUMAN REVIEW REQUIRED. This bounded experiment is complete; no further model search is planned merely to obtain a favorable headline.

## Decision

Retain trailing-average ordering as the practical benchmark. Point-forecast optimization has the lowest aggregate modeled cost, but its 0.51% advantage over the benchmark is small and it wins only 8 of 17 windows. Trailing-average ordering has a higher pooled unit fill rate. Scenario optimization has not established added value. Any deployment choice needs prospective validation and verified operating inputs.

## Scope

42 product–store series, 17 nonoverlapping 28-day episodes from February 2, 2015 through May 22, 2016 (19,992 SKU-days). Each episode resets stock. Twelve earlier residual blocks support eight sampled scenario paths; one earlier window selects the forecast model by MAE. This is a retrospective diagnostic, includes previously inspected periods, and is not a fresh holdout. Shared histories and seasons make results dependent.

Only 3 of 42 series are shared with V1 because selection uses an earlier cutoff. Do not describe V1's 11.97% cost increase and V2's 3.19% increase as a measured improvement from the revision: products and time periods changed.

## Four-policy comparison

| Policy | Total simulated cost | Change vs trailing average | Lower-cost windows vs trailing average | Pooled proxy fill rate |
|---|---:|---:|---:|---:|
| Trailing-average orders | $131,805.88 | reference | — | 79.87% |
| Forecast order-up-to | $131,858.29 | +0.04% | 7/17 | 79.06% |
| Point-forecast optimized orders | $131,127.83 | -0.51% | 8/17 | 79.35% |
| Scenario-optimized orders | $136,010.21 | +3.19% | 4/17 | 77.60% |

Point optimization has $678.05 less total modeled cost than trailing-average orders. It also beats forecast order-up-to in 15/17 windows and scenario optimization in 14/17. It is not consistently superior to the strongest simple benchmark. Aggregate cost and unit fill rate are different objectives because costs weight product units differently.

Gradient boosting's evaluation MAE is 1.645 versus 1.712 for the trailing mean (approximately 3.95% lower). This does not establish a similarly sized decision benefit. Empirical daily 10–90% scenario-envelope coverage is 52.42%; this remains uncalibrated and is not an 80% coverage guarantee.

## Interpretation and verification

Both optimizers use the same cost objective and constraints. The point optimizer uses a single forecast path; scenario optimization uses forecast-plus-residual paths. The comparison supports investigating the current scenario construction, but does not establish a unique causal explanation or show all uncertainty-aware methods are inferior.

An independent daily stock replay of saved orders matched all 68 policy-window costs (maximum absolute difference below $0.000001), with integer-order, budget, unmet-unit and ending-stock checks. Both solvers returned a numerical solution in all 17 windows; all business reviews remain REVIEW REQUIRED. This verifies saved-output accounting, not independent retraining from official raw CSVs.

Purchase cost, penalties, initial stock and holding cost are assumed; observed sales can be demand-censored; there is no terminal salvage credit. No actual Walmart savings, statistical significance, or production readiness is claimed.

## Evidence and reproduction

[Protocol and Windows commands](comparison_experiment.md) · [Policy totals](evidence/comparison_v2/policy_totals.csv) · [All 68 window results](evidence/comparison_v2/policy_windows.csv) · [Paired comparisons](evidence/comparison_v2/policy_comparison.csv) · [Forecast metrics](evidence/comparison_v2/forecast_metrics.csv) · [Metadata and source-result hashes](evidence/comparison_v2/metadata.json)

The public files are aggregate research results, not source observations or detailed SKU orders. V1 evidence is preserved. The app automatically prefers results/comparison_v2 when available unless RETAILOS_RESULTS explicitly selects another directory.
