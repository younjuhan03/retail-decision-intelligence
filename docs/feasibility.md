# Feasibility and data-access record — 2026-10-26

**Current state: first real-data pipeline completed; initial access blocker resolved by the user's official Kaggle download.**

## Access history

Initial unauthenticated Kaggle API probes returned HTTP 401 in the build environment. The user subsequently downloaded the official competition files through their Kaggle account, placed the CSVs in `data/raw`, passed the source audit and executed the complete pipeline on Windows. The user supplied the completed result archive for independent inspection; no alternate sales dataset was substituted.

The raw official CSVs were not sent to the current execution environment. Independent checks here replay saved decisions against the supplied selected panel and verify aggregate outputs. This is distinct from an independent raw-to-results training replication.

## Source audit from the final inspected run

- 42 selected product–store series and 81,522 historical selected rows.
- 17 candidate series excluded by the minimum early price-listing history rule.
- 16,002 selected rows have no price; missing prices remain unfilled from future observations.
- Zero positive-sales rows lack a matching price.
- Validation/evaluation releases agree on common selected observations.

The pre-fix audit used a different subset and its missing-price count must not be substituted for the final provenance.

## Data rights and assumptions

The official rules page did not expose a readable body through the retrieval path. Current usage and redistribution terms have not been comprehensively verified. Raw data, detailed SKU forecasts/orders and processed panels are not included in the public repository. Only aggregate research summaries, original plots and actual app screenshots are deliberately added. The software license does not grant rights to M5 source data.

Purchase cost, holding rates, shortage penalties, initial stock and lead times are explicit modeled inputs; none are asserted as Walmart's actual operating inputs. The first simulation does not establish inventory savings.

Sources:

- https://www.kaggle.com/competitions/m5-forecasting-accuracy/data
- https://www.kaggle.com/competitions/m5-forecasting-accuracy/rules
- https://storage.googleapis.com/kaggle-forum-message-attachments/772349/15032/M5-Competitors-Guide-Final-10-March-2020.pdf
- https://github.com/Kaggle/kaggle-cli
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html
- https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html
