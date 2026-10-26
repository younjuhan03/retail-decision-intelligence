# Feasibility audit — 2026-10-26

**Verdict: software feasible; primary empirical work blocked by official data access.**

Evidence inspected: official Kaggle competition landing/data page; official M5 Competitors' Guide (16-page PDF); official Kaggle CLI instructions; SciPy milp and scikit-learn histogram boosting documentation.

- Official M5 framing: daily Walmart unit sales and a 28-day forecast horizon. Documentation describes grouped sales, selling prices and calendar effects.
- Local attempts to list and download competition files using unauthenticated Kaggle API both returned HTTP 401 Unauthorized. No configured Kaggle token or credentials file was detected. No third-party mirror or alternate sales dataset was used.
- The official rules URL returned no readable body in the retrieval tool. Licensing, any redistribution rights, and present account-specific access conditions remain **unverified**, not presumed prohibited or allowed.
- Actual source file hashes, missing-value rates, exact current downloadable-file shapes and price completeness cannot be audited before download. Implemented checks produce them when the files are supplied.
- A histogram gradient boosting model was chosen instead of requiring LightGBM: both are suitable ML candidates, and the former uses the already available scikit-learn runtime. No accuracy advantage is assumed.
- Scenario costs/stock/budgets are explicit hypothetical inputs, never represented as actual Walmart operating inputs.

Smallest next action: use your Kaggle account to review the official data/rules and download the competition archive; provide the archive or its required CSVs. No API key needs to be shared. Do not publish raw or derived data until usage rights are verified.

Sources:
- https://www.kaggle.com/competitions/m5-forecasting-accuracy/data
- https://www.kaggle.com/competitions/m5-forecasting-accuracy/rules
- https://storage.googleapis.com/kaggle-forum-message-attachments/772349/15032/M5-Competitors-Guide-Final-10-March-2020.pdf
- https://github.com/Kaggle/kaggle-cli
- https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.milp.html
- https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html
