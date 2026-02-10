from pathlib import Path

# Allow for non-revealing ease of retrieval for any development paths
ROOT_PATH: Path = Path(__file__).resolve().parents[3]
SRC_PATH: Path = Path(__file__).resolve().parents[2]


# other paths
ALEMBIC_PATH = ROOT_PATH
