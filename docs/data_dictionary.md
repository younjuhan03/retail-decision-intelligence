# Data dictionary and lineage

Official schemas below come from M5 documentation; full source-file inspection remains pending access. The loader independently checks required fields and values on execution.

| Field | Source | Interpretation / availability |
|---|---|---|
| id | sales | Product-store series; evaluation suffix retained |
| item_id / dept_id / cat_id | sales | Product / department / category IDs |
| store_id / state_id | sales | Location IDs |
| d_1…d_1941 | evaluation sales | Observed integer daily unit sales, not unconstrained demand |
| d / date / wm_yr_wk | calendar | Day-to-date and retail week key |
| event_name_1 | calendar | Announced-calendar event indicator assumed known ahead |
| sell_price | weekly prices | Observed selling price, joined on store/item/week |
| sales | processed | Wide sales melted for selected series only |
| day | processed | Integer from d key; no date-based target shift |
| price_asof | forecast features | Last nonmissing selling price at or before origin |
| mean7/28/84, std28, zero28 | forecast features | Origin-ending active-history summaries |
| seasonal | forecast features | Repeated final observed seven-day sequence |
| origin / horizon | forecast rows | Last observed day / target offset 1–28 |
| unit_cost_assumed | scenario | cost_ratio × last observed selling price |
| initial_inventory_assumed | scenario | floor(initial_days × origin trailing mean) |
| order_units | solver or baseline | Nonnegative integer purchase recommendation |
| actual_proxy_28d | evaluation only | Held-out observed sales; never input to orders |
| procurement / holding_cost / lost_sales_penalty | replay | Modeled costs under documented assumptions |

Lineage: official local CSVs → schema/range checks → training-only series selection → calendar/price joins → SQLite audit → as-of features → chronological forecasts → earlier residual blocks → joint optimization/baselines → physical replay on held-out sales → CSV/JSON/Parquet → chart, HTML and dashboard.

Missing sales are errors, not zeros. Missing pre-activation prices remain missing. No forward price is used to set purchase cost. Event-name missingness means no first calendar event, not an unknown sales observation. The optional validation release must agree with shared selected evaluation-release history.
