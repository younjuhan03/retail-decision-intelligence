# Actual application screenshots

The committed images were captured from the updated running Streamlit application using the user's inspected first real-data result archive. They are not generated UI mockups. No personal browser tabs, local usernames, credentials or raw SKU observations are shown.

- [Executive overview](../assets/screenshots/executive_overview.png): pools the two held-out episodes and shows the negative simulated optimization result.
- [Policy backtesting](../assets/screenshots/policy_backtesting.png): the selected d_1885 episode only.

Screenshots document the UI revision; the calculations and ordering policies are unchanged from the first study. Screenshots are not evidence of production deployment or of independently repeated training.

To reproduce after creating `results/local`:

```powershell
.\.venv\Scripts\python.exe -m pip install playwright
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts/capture_app.py --results results/local
```

Browser tooling is optional and not required for forecasting, optimization or tests. The script starts a local-only server, captures the actual result pages and terminates the server. It fails if complete local results are absent. Rendering can differ slightly by platform or package version.
