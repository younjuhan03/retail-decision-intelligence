# Windows setup and reproduction

1. Extract the archive. Open `retail-decision-intelligence` in VS Code. Open a PowerShell terminal.
2. Install Python 3.11 with the Windows Python launcher.
3. Run:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

4. Download the official M5 competition archive using Kaggle's authenticated website. Review access and data terms. Do not share credentials. Extract required CSVs into `data/raw/` directly (not another nested folder).
5. Execute:

```powershell
.\.venv\Scripts\python.exe -m retailos.cli audit
.\.venv\Scripts\python.exe -m retailos.cli run
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

6. Open the localhost URL printed by Streamlit. Open `results/local/case_study.html` in a browser after a successful real-data run.
7. Read `results/local/summary.json`, the window tables and `sensitivity.csv` before drafting resume claims. Never replace missing real-data outputs with test fixtures.

Memory: the loader filters sales while wide and melts only selected series. Price input is streamed. The optional validation-release comparison loads that earlier CSV in memory; omit this optional file on constrained machines if needed. Optimization runtime depends on scenario count and SKU count. Failed or time-limited solves remain REVIEW REQUIRED. Runtime on a normal Windows laptop has not been benchmarked.

Troubleshooting: missing data errors list the required filename; calendar and price duplicate errors require inspecting source files rather than dropping records silently. An app saying DATA REQUIRED means the pipeline has not completed at the configured output location. No LLM configuration is required.
