"""NWWS-OI - A Python package for the NWWS-OI project."""

import sys
from pathlib import Path

# Ensure the package root is in the system path
package_root = str(Path(__file__).resolve().parents[2])
if package_root not in sys.path:
    sys.path.insert(0, package_root)
