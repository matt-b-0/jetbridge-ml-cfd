"""Generate every current API module, including modules hidden by __all__.

The headless scientific environment need not provide Tk. Two Tk-only modules
are documented from current source by build_presentation_guide.py instead.
"""

import importlib.util
from pathlib import Path
import subprocess
import sys


def main():
    """Pass all current module names explicitly to pdoc; fail on build errors."""
    root = Path(__file__).resolve().parents[1]
    source = root / 'src'
    modules = set()
    has_tk = importlib.util.find_spec('tkinter') is not None
    for file in (source / 'jetbridge_ml').rglob('*.py'):
        parts = file.relative_to(source).with_suffix('').parts
        if parts[-1] == '__init__':
            parts = parts[:-1]
        name = '.'.join(parts)
        if not has_tk and name in {'jetbridge_ml.gui.app', 'jetbridge_ml.gui.progress'}:
            continue
        modules.add(name)
    args = [sys.executable, '-m', 'pdoc', *sorted(modules)]
    if not has_tk:
        args.extend(['!jetbridge_ml.gui.app', '!jetbridge_ml.gui.progress'])
    args.extend(['-d', 'numpy', '-o', str(root / 'docs/html')])
    subprocess.run(args, cwd=root, check=True)
    print(f'Generated {len(modules)} explicitly named API modules; Tk import available: {has_tk}')


if __name__ == '__main__':
    main()
