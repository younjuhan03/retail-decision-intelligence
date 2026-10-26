import argparse
import json
from pathlib import Path
from .pipeline import run


def main():
    parser = argparse.ArgumentParser(description='RetailOS official M5 pipeline; no synthetic-sales fallback')
    parser.add_argument('command', choices=['audit', 'run'])
    parser.add_argument('--raw', default='data/raw')
    parser.add_argument('--out', default='results/local')
    parser.add_argument('--config', default='configs/compact.json')
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text())
    try:
        if args.command == 'audit':
            from .data import load_m5
            _, _, _, manifest = load_m5(args.raw, config)
            print(json.dumps(manifest, indent=2, default=str))
        else:
            print(json.dumps(run(args.raw, args.out, config), indent=2))
    except (FileNotFoundError, ValueError) as e:
        parser.exit(2, f'DATA / CONFIGURATION BLOCKER: {e}\n')

if __name__ == '__main__':
    main()
