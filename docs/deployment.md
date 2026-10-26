# Deployment

No external hosting or GitHub publication has been performed.

Local service:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app/streamlit_app.py --server.address 127.0.0.1
```

For an authorized private server, install the package, provision official data under permitted use, execute the pipeline, set `RETAILOS_RESULTS` to the absolute result directory, and run Streamlit behind the host's authentication and HTTPS controls. Do not make licensed source or derived data publicly downloadable before checking terms.

Streamlit-hosted services can launch with `app/streamlit_app.py` as entrypoint after installing dependencies. The app adds the repository src directory to its import path. The compact package starts in an honest missing-data state if results are absent. Private hosting support and data terms must be checked with the selected provider before deployment; no provider account or deployment was configured here.

Before publishing additional changes: review `git status`, exclude raw data, derived outputs and credentials, confirm data publication rights for every image/table added, run tests, and keep the documented research status aligned with verified execution and distinguish deployment from a source-code upload.
