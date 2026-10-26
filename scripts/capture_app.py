"""Capture the actual running app, not a mockup. Optional: pip install playwright.
python -m playwright install chromium
python scripts/capture_app.py --results results/local
"""
import argparse
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--results', default='results/local')
    parser.add_argument('--out', default='assets/screenshots')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    results = Path(args.results).resolve()
    if not (results / 'summary.json').is_file():
        parser.error('A completed quantitative result directory is required; no mock data is used.')
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    env = dict(os.environ, RETAILOS_RESULTS=str(results))
    server = subprocess.Popen([sys.executable, '-m', 'streamlit', 'run', 'app/streamlit_app.py',
                               '--server.address', '127.0.0.1', '--server.port', str(port),
                               '--server.headless', 'true', '--browser.gatherUsageStats', 'false'],
                              cwd=root, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/_stcore/health', timeout=1) as response:
                    if response.status == 200: break
            except OSError:
                time.sleep(.2)
        else:
            raise RuntimeError('Streamlit did not start')
        with sync_playwright() as browser_runtime:
            browser = browser_runtime.chromium.launch(headless=True, args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': 1500, 'height': 2100}, device_scale_factor=1)
            page.goto(f'http://127.0.0.1:{port}/', wait_until='networkidle')
            page.get_by_text('First real-data study • all held-out windows', exact=True).wait_for(timeout=60000)
            page.get_by_text('Forecast errors · the same held-out windows', exact=True).wait_for(timeout=60000)
            page.screenshot(path=str(out / 'executive_overview.png'), full_page=True)
            page.set_viewport_size({'width': 1500, 'height': 1150})
            page.get_by_text('Policy Backtesting', exact=True).click()
            page.get_by_text('Same budget. Same lead time. Same held-out proxy.', exact=True).wait_for()
            page.screenshot(path=str(out / 'policy_backtesting.png'), full_page=True)
            if page.get_by_test_id('stException').count():
                raise RuntimeError('Application exception during browser verification')
            browser.close()
        print(f'Captured actual application screens in {out}')
    finally:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill(); server.wait()

if __name__ == '__main__': main()
