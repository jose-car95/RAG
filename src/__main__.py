"""Entry point for ``python -m src``."""

import sys

from src.adapters.cli import main


if __name__ == "__main__":
    sys.exit(main())
