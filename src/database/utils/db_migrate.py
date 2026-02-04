from pathlib import Path

from alembic import command
from alembic.config import Config


def run_migrations(db_url: str):
    '''
     This function is called each time the CLI is started. It runs a
     command to check if a migration is necessary, and if it is,
     migrate the database using the most recent revision.
    '''
    ROOT_PATH = Path(__file__).resolve().parents[3]
    alembic_ini = ROOT_PATH / 'alembic.ini'

    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option(
        "script_location", str(ROOT_PATH / 'alembic'))

    alembic_cfg.set_main_option(
        "sqlalchemy.url", db_url)
    command.upgrade(alembic_cfg, "head")
