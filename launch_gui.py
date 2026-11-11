"""Launch the local jet-bridge desktop GUI (Python with Tk required)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'src'))

if __name__ == '__main__':
    from jetbridge_ml.gui.app import main
    main(ROOT)
