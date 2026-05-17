"""Simple runner script for BCB when CLI command isn't in PATH."""

import sys
from bcb.cli import main

if __name__ == '__main__':
    sys.exit(main())
