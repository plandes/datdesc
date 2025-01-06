"""Contains the manager classes that invoke the tables to generate.

"""
__author__ = 'Paul Landes'

from typing import Sequence, Set, Iterable, List, Dict, Any
from dataclasses import dataclass, field
import sys
import logging
import itertools as it
from itertools import chain
from datetime import datetime
from io import TextIOWrapper
import pandas as pd
from zensols.config import Writable
from . import Table

logger = logging.getLogger(__name__)


@dataclass
class LatexTable(Table):
    """This subclass generates LaTeX tables.

    """
    def format_scientific(self, x: float, sig_digits: int = 1) -> str:
        nstr: str = f'{{0:.{sig_digits}e}}'.format(x)
        if 'e' in nstr:
            base, exponent = nstr.split('e')
            base = base[:-2] if base.endswith('.0') else base
            nstr = f'{base} \\times 10^{{{int(exponent)}}}'
        return f'${nstr}$'

    def _get_table_rows(self, df: pd.DataFrame) -> Iterable[List[Any]]:
        """Return the rows/columns of the table given to :mod:``tabulate``."""
        cols = [tuple(map(lambda c: f'\\textbf{{{c}}}', df.columns))]
        return it.chain(cols, map(lambda x: x[1].tolist(), df.iterrows()))

    def _get_tabulate_params(self) -> Dict[str, Any]:
        params: Dict[str, Any] = super()._get_tabulate_params()
        params['tablefmt'] = 'latex_raw'
        return params

    def _write_table(self, depth: int, writer: TextIOWrapper,
                     content: List[str]):
        """Write the text of the table's rows and columns."""
        for lix, ln in enumerate(content[1:-1]):
            self._write_line(ln.strip(), depth, writer)
            if (lix - 2) in self.hlines:
                self._write_line('\\hline', depth, writer)
            if (lix - 2) in self.double_hlines:
                self._write_line('\\hline \\hline', depth, writer)


@dataclass
class SlackTable(LatexTable):
    """An instance of the table that fills up space based on the widest column.

    """
    slack_column: int = field(default=0)
    """Which column elastically grows or shrinks to make the table fit."""

    def __post_init__(self):
        super().__post_init__()
        self.uses.append('tabularx')

    @property
    def columns(self) -> str:
        cols: str = self.column_aligns
        if cols is None:
            df: pd.DataFrame = self.formatted_dataframe
            i: int = self.slack_column
            cols = ('l' * (df.shape[1] - 1))
            cols = cols[:i] + 'X' + cols[i:]
            cols = '|' + '|'.join(cols) + '|'
        return cols


@dataclass
class CsvToLatexTable(Writable):
    """Generate a Latex table from a CSV file.

    """
    tables: Sequence[Table] = field()
    """A list of table instances to create Latex table definitions."""

    package_name: str = field()
    """The name Latex .sty package."""

    def _write_header(self, depth: int, writer: TextIOWrapper):
        date = datetime.now().strftime('%Y/%m/%d')
        writer.write("""\\NeedsTeXFormat{LaTeX2e}
\\ProvidesPackage{%(package_name)s}[%(date)s Tables]

""" % {'date': date, 'package_name': self.package_name})
        uses: Set[str] = set(chain.from_iterable(
            map(lambda t: t.uses, self.tables)))
        for use in sorted(uses):
            writer.write(f'\\usepackage{{{use}}}\n')
        if len(uses) > 0:
            writer.write('\n')

    def write(self, depth: int = 0, writer: TextIOWrapper = sys.stdout):
        """Write the Latex table to the writer given in the initializer.

        """
        tlen: int = len(self.tables)
        self._write_header(depth, writer)
        for i, table in enumerate(self.tables):
            table.write(depth, writer)
            if i < tlen:
                writer.write('\n')
