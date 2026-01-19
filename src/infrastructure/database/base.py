'''
This file initializes `Base`, a class that all of our models (tables)
inherit and defines a function to use the database's `engine`.
'''

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base

# for DB migration via alembic
DB_PATH = "sqlite:///src/infrastructure/database/data.db"

Base = declarative_base()


def get_engine():
    '''
    The engine acts as a central sources of all connections to the DB.
    It is a factory & also manages a connection pool for the connections
    '''
    return create_engine(DB_PATH, future=True)
