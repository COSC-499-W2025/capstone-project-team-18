"""conftest.py
Ensure tests can import the package layout used by the application.

When running the app directly (for example via ``python src/app.py``) the
current working directory may be ``src/``, which makes local imports resolve
quite differently than when pytest runs from the repository root. Add the
repository root and the ``src/`` directory to ``sys.path`` so tests that do
``from src.classes...`` work the same way pytest runs them as when running
the app.

"""

import sys
from pathlib import Path

# Repository root (this file is at the repo root)
REPO_ROOT = Path(__file__).resolve().parent
SRC_DIR = REPO_ROOT / "src"

# Ensure the repository root is on sys.path so imports like `import src...`
# resolve consistently when pytest runs from the project root.
sys.path.insert(0, str(REPO_ROOT))

# Also ensure the src/ directory itself is on sys.path. This helps in cases
# where code or tests expect modules to be importable directly from src.
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
