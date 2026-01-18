
from alembic import command
from alembic.config import Config


def run_migrations():
    '''
     This function is called each time the CLI is started. It runs a
     command to check if a migration is necessary, and if it is,
     migrate the database using the most recent revision.
    '''
    ROOT_PATH = Path(__file__).resolve().parents[4]
    alembic_ini = ROOT_PATH / 'alembic.ini'
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option(
        "sqlalchemy.url", "sqlite:///src/database/data.db")
    command.upgrade(alembic_cfg, "head")
