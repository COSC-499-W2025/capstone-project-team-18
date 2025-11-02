"""
This file will run everytime pytest
starts running tests. It is used to
make global changes to the testing environment.
"""

import sys
from pathlib import Path

"""
When pytest runs, we consider capstone-project-team-18
to be the root of the project for imports.

However, when we run the application normally,
the src/ directory is considered to be the root
for imports.

This makes us run in to error in a situation
like this:

- pytest imports ArtifactMiner with:
    from src.classes.cli import ArtifactMiner

- but ArtifactMiner tries to import start_miner with:
    from app import start_miner

Error can't find app!

So here, we adjust sys.path to ensure that
imports work correctly in both scenarios.
"""
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
