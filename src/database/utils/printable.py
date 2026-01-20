'''
This file contains functions for printing data
retrieved from the database.
'''

from database.models import FileReportTable, ProjectReportTable, UserReportTable


def __repr__(table: FileReportTable | ProjectReportTable | UserReportTable):
    '''
    Prints all rows of a given table in a dict-like format.
    '''
    cols = table.__table__.columns.keys()
    d = {c: getattr(table, c) for c in cols}
    return str(d)
