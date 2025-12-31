
from alembic import command
from alembic.config import Config


def run_migrations():
    alembic_ini = '/workspaces/capstone-project-team-18/alembic.ini'
    alembic_cfg = Config(alembic_ini)
    alembic_cfg.set_main_option(
        "sqlalchemy.url", "sqlite:///src/database/data.db")
    command.upgrade(alembic_cfg, "head")
