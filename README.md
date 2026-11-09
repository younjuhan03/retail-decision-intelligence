# RetailOS
### Does a better forecast lead to a better inventory decision?

[![Software verification](https://github.com/younjuhan03/retail-decision-intelligence/actions/workflows/tests.yml/badge.svg)](https://github.com/younjuhan03/retail-decision-intelligence/actions/workflows/tests.yml)

**My finding:** point-forecast optimization reduced total modeled cost by 0.51% versus trailing-average orders, but won only 8 of 17 periods and had a lower unit fill rate. I would retain the simple benchmark until prospective evaluation supports a change.

I compared four ordering policies across **42 product–store series and 17 historical 28-day episodes** using M5 retail sales. My question was how to allocate a limited purchasing budget—not simply which model predicts sales most accurately.

**Explore:** [one-minute overview](docs/project_overview.html) · [two-page PDF](docs/comparison_case_study.pdf) · [detailed findings](docs/comparison_results.md) · [implementation](src/retailos/pipeline.py)

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

## What I want to study next

I want to connect forecasting, optimization and business objectives more rigorously. How should an operating decision weigh a small cost advantage against service levels, unstable performance and uncertain inputs? That is the kind of decision evaluation I want to pursue in graduate study in business analytics.

## Methods and evidence

My workflow connects source validation, time-ordered forecasting, shared-budget integer optimization, policy replay and a Streamlit dashboard.

- [Experiment and reproduction commands](docs/comparison_experiment.md)
- [Methods, initial study and local setup](docs/technical_notes.md)
- [Technical methodology](docs/methodology.md) · [software verification](docs/verification.md)
- [Aggregate evidence](docs/evidence/comparison_v2/) · [data dictionary](docs/data_dictionary.md)

I use official [M5 source files](https://www.kaggle.com/competitions/m5-forecasting-accuracy/data) locally; the repository contains aggregate findings rather than redistributed source data. HTML reports can be downloaded and opened in a browser. The PDF can be viewed directly on GitHub.

## Boundaries of my conclusion

Operating costs and initial stock are assumptions, observed sales may understate demand, and inventory resets each episode. The follow-up is exploratory and includes previously inspected periods. Only 3 of 42 series overlap the initial study, so I report the studies separately rather than claim a controlled performance improvement. I have not established statistical significance or validated a deployment decision.

## Development note

I used AI tools to support project development, including code and documentation.
