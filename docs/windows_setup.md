# Windows setup and reproduction

1. Open `retail-decision-intelligence` in VS Code and open a PowerShell terminal.
2. Check Python with `python --version`. The user completed the original real-data run on Python 3.14.6; CI targets Python 3.11.
3. Run:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
```

If `python` is not recognized, install Python and reopen VS Code. A `py` command is not required. Using the environment's executable directly avoids changing PowerShell activation policy.

4. Download the official M5 competition files using your Kaggle account after reviewing its terms. Extract the CSVs directly into `data/raw/`, not a nested subfolder. Keep credentials outside Git.
5. Execute:

```powershell
.\.venv\Scripts\python.exe -m retailos.cli audit
.\.venv\Scripts\python.exe -m retailos.cli run
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py
```

6. Open Streamlit's printed localhost URL. Completed quantitative results live in `results/local/`. Read `summary.json`, `policy_evaluation.csv` and `sensitivity.csv` before making any performance claim.
7. Export aggregate documentation:

```powershell
.\.venv\Scripts\python.exe scripts/export_evidence.py --results results/local
```

The generated English page is `docs/case_study.html`. GitHub displays its source; download it and open in a browser for the formatted view. The exporter verifies saved costs using a separate physical replay and excludes source-level rows from its public outputs. Publication rights for any additional data assets still need review.

If the app is still running after you receive a source update, stop it with Ctrl+C and run the Streamlit command again. A fresh clone without local data/results should display DATA REQUIRED, even though committed documentation contains a completed research snapshot.

Memory: filter sales while wide and stream price input. The optional validation-release comparison loads the earlier CSV in memory; omit this optional file on constrained machines if needed. Solver runtime depends on scope and scenario count. Missing data and failed solves remain explicit errors or REVIEW REQUIRED, not fabricated results.
