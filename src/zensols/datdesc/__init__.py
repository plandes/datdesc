"""Generate Latex tables in a .sty file from CSV files.  The paths to the CSV
files to create tables from and their metadata is given as a YAML configuration
file.

"""
from .domain import *
from .table import *
from .desc import *
from .app import *
from .cli import *
