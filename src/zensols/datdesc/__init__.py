"""Generate Latex tables in a .sty file from CSV files.  The paths to the CSV
files to create tables from and their metadata is given as a YAML configuration
file.

Example::
    latextablenamehere:
        type: slack
        slack_col: 0
        path: ../config/table-name.csv
        caption: Some Caption
        placement: t!
        size: small
        single_column: true
        percent_column_names: ['Proportion']


"""

from zensols.util import APIError


class DataDescriptionError(APIError):
    """Thrown for any application level error.

    """
    pass


class LatexTableError(DataDescriptionError):
    """Thrown for any application level error related to creating tables.

    """
    def __init__(self, reason: str, table: str = None):
        if table is not None:
            reason = f'{reason} for table {table}'
        super().__init__(reason)
        self.table = table


class FigureError(DataDescriptionError):
    """Thrown for any application level error related to creating figures.

    """
    def __init__(self, reason: str, figure: str = None):
        if figure is not None:
            reason = f'{reason} for figure {figure}'
        super().__init__(reason)
        self.figure = figure


from .table import *
from .desc import *
from .app import *
from .cli import *
