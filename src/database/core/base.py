'''
This file initializes `Base`, a class that all of our models (tables)
inherit and defines a function to use the database's `engine`.
'''

from sqlmodel import create_engine

# for DB migration via alembic
DB_PATH = "sqlite:///src/database/data.db"

ENGINE_CACHE = None


def get_engine():
    '''
    The engine acts as a central sources of all connections to the DB.
    It is a factory & also manages a connection pool for the connections
    '''

    global ENGINE_CACHE

    if not ENGINE_CACHE:
        ENGINE_CACHE = create_engine(DB_PATH, future=True)

    return ENGINE_CACHE
