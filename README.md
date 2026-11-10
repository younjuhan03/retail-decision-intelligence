# RetailOS
### Does a better forecast lead to a better inventory decision?

[![Software verification](https://github.com/younjuhan03/retail-decision-intelligence/actions/workflows/tests.yml/badge.svg)](https://github.com/younjuhan03/retail-decision-intelligence/actions/workflows/tests.yml)

**My finding:** point-forecast optimization reduced total modeled cost by 0.51% versus trailing-average orders, but won only 8 of 17 periods and had a lower unit fill rate. I would retain the simple benchmark until prospective evaluation supports a change.

I compared four ordering policies across **42 product–store series and 17 historical 28-day episodes** using M5 retail sales. My question was how to allocate a limited purchasing budget—not simply which model predicts sales most accurately.

**Explore:** [one-minute overview](docs/project_overview.html) · [two-page PDF](docs/comparison_case_study.pdf) · [detailed findings](docs/comparison_results.md) · [implementation](src/retailos/pipeline.py)

## My project in plain English

I studied a store's ordering decision: **how much of each product should I buy when my purchasing budget is limited?** I used historical M5 sales to compare a simple recent-sales rule with three forecast-based ordering policies.

- **What I built:** I connected sales forecasting, budget-constrained order calculations and a dashboard for comparing inventory policies.
- **How I evaluated it:** I replayed 17 historical periods with the same starting conditions for each policy, then compared cost and the share of sales covered by stock.
- **What I learned:** I found a small overall cost advantage for point-forecast optimization, but inconsistent results and weaker service. I would keep the simple rule as my reference while gathering stronger evidence.

I use **unit fill rate** to mean the share of evaluated sales quantities I could fulfill in the simulation. I report modeled costs under stated assumptions; I have not measured savings at a real retailer.

## What I compared

| Ordering policy | Modeled cost | Change vs. trailing average | Lower-cost periods | Unit fill rate |
|---|---:|---:|---:|---:|
| Trailing-average orders | $131,805.88 | Reference | — | 79.87% |
| Forecast order-up-to | $131,858.29 | +0.04% | 7/17 | 79.06% |
| Point-forecast optimization | $131,127.83 | -0.51% | 8/17 | 79.35% |
| Scenario optimization | $136,010.21 | +3.19% | 4/17 | 77.60% |

These are retrospective simulations under assumed operating costs, not measured retailer savings. Within each episode, I compare policies using the same budget, initial stock, lead time and evaluation sales.

## My analytical decisions

- **Evaluate decisions as well as predictions.** Lower forecast error is useful only if it improves the ordering outcome under the objective I chose.
- **Keep the comparison fair.** Shared constraints let me compare how each policy allocates the same resources. A separate daily replay checks the accounting for all 68 policy-period results.
- **Read aggregate cost alongside consistency and service.** A $678.05 pooled advantage is not enough for me to prefer point optimization when it wins fewer than half the periods and fills a smaller share of sales.
- **Retain an unfavorable result.** Scenario optimization cost 3.19% more than the benchmark. I would investigate its uncertainty representation before adding complexity.

## What I learned and want to deepen

A small pooled cost advantage was not enough for me to recommend changing the ordering policy. I also had to consider service levels and how often the policy performed better. I can compare those outcomes under fixed assumptions; my next learning goal is to formulate the operating problem more carefully, using constrained optimization to express which service requirements must be met and which costs can be traded off.

## My next validation step

For my next evaluation, I would fix the ordering rules, cost assumptions and a minimum service requirement before observing new periods, then compare cost and fill rate against the trailing-average policy.

## Methods and evidence

My workflow connects source validation, time-ordered forecasting, shared-budget integer optimization, policy replay and a Streamlit dashboard.

- [Experiment and reproduction commands](docs/comparison_experiment.md)
- [Methods, initial study and local setup](docs/technical_notes.md)
- [Technical methodology](docs/methodology.md) · [software verification](docs/verification.md)
- [Aggregate evidence](docs/evidence/comparison_v2/) · [data dictionary](docs/data_dictionary.md)

I use official [M5 source files](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data) locally; the repository contains aggregate findings rather than redistributed source data. HTML reports can be downloaded and opened in a browser. The PDF can be viewed directly on GitHub.

## Boundaries of my conclusion

Operating costs and initial stock are assumptions, observed sales may understate demand, and inventory resets each episode. The follow-up is exploratory and includes previously inspected periods. Only 3 of 42 series overlap the initial study, so I report the studies separately rather than claim a controlled performance improvement. I have not established statistical significance or validated a deployment decision.

## AI-assisted development

I used AI tools to support project development, including code and documentation. I take responsibility for the analytical choices and interpretations presented here, and I document the data, comparisons, assumptions and limitations behind my conclusions. I distinguish AI assistance during development from the models I actually implement; I describe those models in the methods rather than imply that I built an LLM-based system.
