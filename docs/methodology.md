# Methodology: V1 and V2

This page covers both saved studies. V1 uses `configs/compact.json`; V2 uses `configs/comparison.json`. The app can display either study, so use the corresponding column below.

| Protocol | V1: initial study | V2: retrospective follow-up |
|---|---|---|
| Product-selection cutoff | d_1773 | d_1101 |
| Residual blocks | 3 origins: d_1773, d_1801, d_1829 | 12 origins: d_1101–d_1409, every 28 days |
| Forecast-model selection | d_1857 | d_1437 |
| Evaluation origins | d_1885 and d_1913 | 17 origins: d_1465–d_1913, every 28 days |
| Evaluation dates | March 28–May 22, 2016 | February 2, 2015–May 22, 2016 |
| Ordering policies | 3 policies | Same 3 plus point-forecast optimization |
| Interpretation | Original held-out evaluation | Exploratory retrospective comparison, not a fresh holdout |

Only 3 of 42 product–store series overlap the studies because the selection cutoff changes. Do not interpret differences between their aggregate results as a controlled V1-to-V2 improvement. Both reset inventory at the start of each 28-day episode.

### Data and interpretation
Official source: https://www.kaggle.com/competitions/m5-forecasting-accuracy/data
M5 contains unit sales, not latent unconstrained demand. Sell prices are observed revenues per unit, not purchase costs. Every cost and stock variable below is an assumption. No inventory history or actual Walmart cost savings can be inferred.

### Scope and selection
Default scope: TX_1, CA_1 and WI_1; two products per store/department (up to 42 series). Rank series within each group by the share of zero-sales days, then sales volume, then ID, using only the 364 days ending at the first configured forecast origin (d_1773 for V1; d_1101 for V2). Select evenly spaced ranks. This deliberately contrasts intermittent and regular series, rather than estimating a representative population average. Exclude zero-volume training series and candidates without a price-listing week starting at least 83 days before the first forecast origin (84 days of active calendar history). Do not interpret pooled results as retailer-wide effects.

Activation is proxied by first listed selling price **as known at each origin**. Preserve zeros after activation; they may represent true zero demand or unavailable inventory. Preserve missing prices, exclude pre-activation history, and never backfill from future prices. Sparse or late activation can fail the minimum 84-day history requirement; the pipeline fails visibly instead of silently imputing data. Historical training rows with insufficient active history are skipped.

### Forecast protocol
Both studies use 28-day nonoverlapping forecast origins and the calibration, model-selection and evaluation split listed above. A direct global histogram gradient boosting Poisson model uses origin-level sales summaries, repeated last-week sales, last observed selling price, SKU encoding and horizon-specific calendar features. The estimator's random early-stopping split is disabled. Fixed hyperparameters; no automated tuning on evaluation outcomes. V2 is a follow-up designed after inspecting V1 and is therefore labeled exploratory. Training examples have complete 28-day targets ending by the forecast origin. Calendar event flags are assumed announced in advance; actual future sales and prices are excluded. Retrain at each origin using only available history within a bounded training-origin range.

Baselines: all active-history mean; repeat last 7 days; trailing 28-day average. Select lowest cross-series MAE on the study's selection origin (d_1857 for V1, d_1437 for V2); report every model on evaluation origins regardless of winner. Metrics: MAE, pooled RMSE via mean MSE, signed bias (forecast minus sales), WAPE when actual total >0, and bottom-level unweighted RMSSE with leading zeros removed from training scale. Undefined zero-scale RMSSE is missing, never replaced by zero. This is **not** the full hierarchical competition WRMSSE. MAPE is omitted because zeros make percentage errors undefined or unstable.

### Uncertainty
Use full 28-day out-of-sample residual blocks from the configured calibration origins (the first 3 in V1; the first 12 in V2). For each scenario sample one complete all-SKU residual block and add it to the point forecast, truncating at zero. This preserves observed within-block temporal and cross-product dependence. The seed is fixed. V1 has 3 unique historical blocks and V2 has 12. Both sample 8 paths with replacement; sampled paths may repeat and need not use every available block. Neither pool establishes calibrated tail coverage. Report empirical coverage of uncalibrated 10–90% scenario envelopes on test observations. No calibration, confidence interval, independent-bootstrap significance, or probabilistic guarantee is claimed.

### Inventory decision model
One periodic review every 28 days; one integer order q_i at the start of each episode, arriving before sales on day lead_days + 1. Budget is shared across selected products and stores (a modeled central purchasing pool). Each test episode resets initial inventory, so neither study is a continuous replenishment simulation. Default initial inventory: floor(3 × trailing daily average). Purchase unit cost: 65% of selling price last observed at the origin; fixed for the episode. Daily holding cost: 0.2% of assumed unit purchase cost per ending unit. Unmet sales-proxy penalty: 3 × assumed unit purchase cost per unit. Budget: 75% of the total assumed cost of 28 × trailing daily average. All inputs are exposed in config/scenario controls.

Minimize:

`sum_i c_i q_i + (1/S) sum_(s,i,t) [h_i I_sit + p_i L_sit]`

subject to:

`sum_i c_i q_i <= B`, `q_i >= 0 integer`, `I_sit >= 0`, `L_sit >= 0`,

`I_sit = I_si(t-1) + q_i * 1[t = lead_days] - D_sit + L_sit`.

I_si(-1) is initial stock. The daily recourse variables represent ending inventory and unmet sales under each forecast scenario. Positive holding/penalty costs yield physical lost-sales accounting at the optimum; ties are evaluated using the explicit physical simulator. Procurement is counted as cash expenditure plus holding and penalty. Initial stock is a common sunk endowment, not newly purchased. Orders arriving after the horizon provide no service. There is zero terminal salvage credit; ending stock has no credited continuation value, which may favor under-ordering. No expiration, storage capacity, order setup cost, inter-store transfer, or service-level constraint is modeled. Optional minimum quantities are supported by the solver API, not used in primary experiments.

### Baselines and evaluation
Historical-average order-up-to: ceil(max(0, 28 × trailing daily mean - initial stock)). Forecast order-up-to: ceil(max(0, sum of selected model's daily forecasts - initial stock)). If infeasible, both use identical proportional scaling, flooring, then feasible largest-remainder rounding; they never exceed budget. No target uses future actual sales. Scenario-optimized orders use the selected forecast plus earlier residual blocks. V2 additionally evaluates point-forecast optimization using the same objective and constraints with one forecast path and no residual perturbations. All policies share initial stock, purchasing budget, arrival time, holding rate, shortage penalty, and terminal treatment, and are replayed against identical held-out unit sales.

Fill rate = 1 - unmet proxy units / total held-out proxy units; missing if total is zero. Budget utilization = purchase expenditure / budget; zero by convention at zero budget. V1 one-factor sensitivities vary budget, shortage penalty, holding cost, lead time, uncertainty multiplier and initial stock. V2 disables these extra reruns to keep the follow-up bounded; its sensitivity file contains base-case rows only. Budget denominators remain tied to historical sales, so uncertainty changes do not silently relax cash constraints. Negative simulated improvements are retained. Improvement denominators are the matched baseline's total cost over paired test windows. V1's two test blocks do not establish robust population effects. V2's 17 retrospective windows also do not establish independent population evidence because histories and seasons are shared and the design follows V1 inspection. Report window-level results and retain REVIEW REQUIRED.

### Decision support and status
Deterministic review only; no optional LLM provider implemented in this release. APPROVE means valid numeric allocation with adequate user-confirmed evidence and coverage, not authorization to place orders. Core experiments always require human review because independent evaluation is limited. HOLD means no orders; INFEASIBLE means constraints or allocation fail; solver timeout or unavailable output yields REVIEW REQUIRED. No real orders are submitted.


### First real-data study
The initial official-data run is complete. See [first-run results](first_run_results.md) for verified metrics and [aggregate evidence](evidence/first_run.json) for assumptions, original runtime versions and result-file hashes. The optimizer increased modeled cost; it is not approved for use. Documentation/UI updates do not retrain models or change the first-run decisions.


### Retrospective follow-up
See [V2 results](comparison_results.md) and [V2 protocol](comparison_experiment.md). Point optimization had 0.51% lower aggregate modeled cost than trailing-average orders but won only 8/17 windows; scenario optimization cost 3.19% more. These findings do not justify a production recommendation. This documentation correction does not change either study's calculations or saved results.
