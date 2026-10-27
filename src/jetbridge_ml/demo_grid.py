"""CLI bridge to the CFD-only report-grid exporter."""
import argparse
from pathlib import Path
from jetbridge_ml.cfd_interface.demo_support import export_report_grid


def main():
    """Export the fresh isothermal sampling table used by report graphics."""
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('case', 'dataset', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--time', required=True)
    args = parser.parse_args()
    export_report_grid(args.case, args.dataset, args.output, args.time)


if __name__ == '__main__':
    main()
