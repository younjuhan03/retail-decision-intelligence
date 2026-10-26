### Data and interpretation
Official source: https://www.kaggle.com/competitions/m5-forecasting-accuracy/data
M5 contains unit sales, not latent unconstrained demand. Sell prices are observed revenues per unit, not purchase costs. Every cost and stock variable below is an assumption. No inventory history or actual Walmart cost savings can be inferred.

### Scope and selection
Default scope: TX_1, CA_1 and WI_1; two products per store/department (up to 42 series). Rank series within each group by the share of zero-sales days, then sales volume, then ID, using only the 364 days ending at d_1773. Select evenly spaced ranks. This deliberately contrasts intermittent and regular series, rather than estimating a representative population average. Exclude zero-volume training series. Do not interpret pooled results as retailer-wide effects.

Activation is proxied by first listed selling price **as known at each origin**. Preserve zeros after activation; they may represent true zero demand or unavailable inventory. Preserve missing prices, exclude pre-activation history, and never backfill from future prices. Sparse or late activation can fail the minimum 84-day history requirement; the pipeline fails visibly instead of silently imputing data. Historical training rows with insufficient active history are skipped.

### Forecast protocol
28-day nonoverlapping origins: 1773, 1801, 1829 (calibration); 1857 (model selection); 1885 and 1913 (test). A direct global histogram gradient boosting Poisson model uses origin-level sales summaries, repeated last-week sales, last observed selling price, SKU encoding and horizon-specific calendar features. The estimator's random early-stopping split is disabled. Fixed hyperparameters; no test tuning. Training examples have complete 28-day targets ending by the forecast origin. Calendar event flags are assumed announced in advance; actual future sales and prices are excluded. Retrain at each origin using only available history within a bounded training-origin range.

Baselines: all active-history mean; repeat last 7 days; trailing 28-day average. Select lowest cross-series MAE on selection origin d_1857; report every model on test origins regardless of winner. Metrics: MAE, pooled RMSE via mean MSE, signed bias (forecast minus sales), WAPE when actual total >0, and bottom-level unweighted RMSSE with leading zeros removed from training scale. Undefined zero-scale RMSSE is missing, never replaced by zero. This is **not** the full hierarchical competition WRMSSE. MAPE is omitted because zeros make percentage errors undefined or unstable.

### Uncertainty
Use full 28-day out-of-sample residual blocks from the first three origins. For each scenario sample one complete all-SKU residual block and add it to the point forecast, truncating at zero. This preserves observed within-block temporal and cross-product dependence. The seed is fixed. Three unique blocks provide very limited tail information; eight sampled scenarios do not create eight independent historical blocks. Report empirical coverage of nominal 10–90% envelopes on test observations. No calibration, confidence interval, independent-bootstrap significance, or probabilistic guarantee is claimed.

### Inventory decision model
One periodic review every 28 days; one integer order q_i at the start of each episode, arriving before sales on day lead_days + 1. Budget is shared across selected products and stores (a modeled central purchasing pool). Each test episode resets initial inventory, so this is not a continuous 56-day replenishment simulation. Default initial inventory: floor(3 × trailing daily average). Purchase unit cost: 65% of selling price last observed at the origin; fixed for the episode. Daily holding cost: 0.2% of assumed unit purchase cost per ending unit. Unmet sales-proxy penalty: 3 × assumed unit purchase cost per unit. Budget: 75% of the total assumed cost of 28 × trailing daily average. All inputs are exposed in config/scenario controls.

Minimize:

`sum_i c_i q_i + (1/S) sum_(s,i,t) [h_i I_sit + p_i L_sit]`

subject to:

`sum_i c_i q_i <= B`, `q_i >= 0 integer`, `I_sit >= 0`, `L_sit >= 0`,

`I_sit = I_si(t-1) + q_i * 1[t = lead_days] - D_sit + L_sit`.

I_si(-1) is initial stock. The daily recourse variables represent ending inventory and unmet sales under each forecast scenario. Positive holding/penalty costs yield physical lost-sales accounting at the optimum; ties are evaluated using the explicit physical simulator. Procurement is counted as cash expenditure plus holding and penalty. Initial stock is a common sunk endowment, not newly purchased. Orders arriving after the horizon provide no service. There is zero terminal salvage credit; ending stock has no credited continuation value, which may favor under-ordering. No expiration, storage capacity, order setup cost, inter-store transfer, or service-level constraint is modeled. Optional minimum quantities are supported by the solver API, not used in primary experiments.

### Baselines and evaluation
Historical-average order-up-to: ceil(max(0, 28 × trailing daily mean - initial stock)). Forecast order-up-to: ceil(max(0, sum of selected model's daily forecasts - initial stock)). If infeasible, both use identical proportional scaling, flooring, then feasible largest-remainder rounding; they never exceed budget. No target uses future actual sales. Optimized orders use the selected forecast plus earlier residual blocks. All policies share initial stock, purchasing budget, arrival time, holding rate, shortage penalty, and terminal treatment, and are replayed against identical held-out unit sales.

Fill rate = 1 - unmet proxy units / total held-out proxy units; missing if total is zero. Budget utilization = purchase expenditure / budget; zero by convention at zero budget. One-factor sensitivities vary budget, shortage penalty, holding cost, lead time, uncertainty multiplier and initial stock. Budget denominators remain tied to historical sales, so uncertainty changes do not silently relax cash constraints. Negative simulated improvements are retained. Improvement denominators are the matched baseline's total cost over paired test windows. Two test blocks cannot establish robust population effects: report the window-level and sensitivity tables and retain REVIEW REQUIRED.

### Decision support and status
Deterministic review only; no optional LLM provider implemented in this release. APPROVE means valid numeric allocation with adequate user-confirmed evidence and coverage, not authorization to place orders. Core experiments always require human review because independent evaluation is limited. HOLD means no orders; INFEASIBLE means constraints or allocation fail; solver timeout or unavailable output yields REVIEW REQUIRED. No real orders are submitted.
