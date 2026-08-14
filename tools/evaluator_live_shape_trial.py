"""Compatibility entry point for the full exact-artifact GenVM proof."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.full_genvm_release_proof import main


if __name__ == "__main__":
    main()
