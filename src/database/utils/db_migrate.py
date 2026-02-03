from pathlib import Path

from alembic import command
from alembic.config import Config
from src.utils.errors import AlembicMigrationError
from src.infrastructure.log.logging import get_logger

logger = get_logger(__name__)


def run_migrations():
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
        "sqlalchemy.url", "sqlite:///src/database/data.db")

    try:
        command.upgrade(alembic_cfg, "head")
    except Exception:
        print("\n!!! Migrations failed !!!")
        logger.critical("Alembic migration failed")

        error_msg = "It is likely you added/changed a database-tracked object " \
            "without handling it in `alembic/versions`. " \
            "Check `alembic/README.md` for guidance."

        raise AlembicMigrationError(error_msg)
