"""`python -m harness ...` entry point."""
import sys

from .interface.cli import main

if __name__ == "__main__":
    sys.exit(main())
