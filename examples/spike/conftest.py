"""pytest dla examples/spike — ścieżki: shim + vendored validators."""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
for p in [
    os.path.join(_HERE, "python"),
    os.path.normpath(os.path.join(_HERE, "..", "targets", "validators", "src")),
]:
    if p not in sys.path:
        sys.path.insert(0, p)
