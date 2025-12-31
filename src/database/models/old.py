'''Contains the ORM modles for our database's tables and a __repr__ function to print a row of data'''
from typing import List

from sqlalchemy import ForeignKey, Table, Column, Integer, String
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.classes.statistic import FileStatCollection, ProjectStatCollection, UserStatCollection

from ..utils.init_columns import make_columns

from src.database.base import Base

"""
def __repr__(table: FileReportTable | ProjectReportTable | UserReportTable):
    '''
    Prints the rows of a given table in a dict-like format.
    '''
    cols = table.__table__.columns.keys()
    d = {c: getattr(table, c) for c in cols}
    return str(d)
"""
