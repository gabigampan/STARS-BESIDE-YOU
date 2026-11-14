"""Entry point: ``python -m engine <command>``."""
import sys

from engine.cli import main

if __name__ == "__main__":
    sys.exit(main())
