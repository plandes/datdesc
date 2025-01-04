"""This module contains classes that generate tables.

"""
__author__ = 'Paul Landes'

from typing import (
    Dict, List, Sequence, Tuple, Any, Iterable, Set,
    ClassVar, Optional, Callable, Union
)
from dataclasses import dataclass, field
import logging
import sys
import re
import string
import itertools as it
from io import TextIOWrapper, StringIO
from pathlib import Path
import pandas as pd
from tabulate import tabulate
from zensols.persist import persisted, PersistedWork, PersistableContainer
from zensols.config import Dictable
from . import LatexTableError

logger = logging.getLogger(__name__)


@dataclass
class Table(PersistableContainer, Dictable):
    """Generates a Zensols styled Latex table from a CSV file.

    """
    _DICTABLE_ATTRIBUTES: ClassVar[Set[str]] = {'columns'}

    _FILE_NAME_REGEX: ClassVar[re.Pattern] = re.compile(r'(.+)\.yml')
    """Used to narrow down to a :obj:`package_name`."""

    path: Union[Path, str] = field()
    """The path to the CSV file to make a latex table."""

    name: str = field()
    """The name of the table, also used as the label."""

    template: str = field()
    """The table template, which lives in the application configuraiton
    ``obj.yml``.

    """
    caption: str = field()
    """The human readable string used to the caption in the table."""

    definition_file: Path = field(default=None)
    """The YAML file from which this instance was created."""

    uses: Sequence[str] = field(default=())
    """Comma separated list of packages to use."""

    single_column: bool = field(default=True)
    """Makes the table one column wide in a two column.  Setting this to false
    generates a ``table*`` two column table, which won't work in beamer
    (slides) document types.

    """
    hlines: Sequence[int] = field(default_factory=set)
    """Indexes of rows to put horizontal line breaks."""

    double_hlines: Sequence[int] = field(default_factory=set)
    """Indexes of rows to put double horizontal line breaks."""

    column_keeps: Optional[List[str]] = field(default=None)
    """If provided, only keep the columns in the list"""

    column_removes: List[str] = field(default_factory=list)
    """The name of the columns to remove from the table, if any."""

    column_renames: Dict[str, str] = field(default_factory=dict)
    """Columns to rename, if any."""

    column_value_replaces: Dict[str, Dict[Any, Any]] = \
        field(default_factory=dict)
    """Data values to replace in the dataframe.  It is keyed by the column name
    and values are the replacements.  Each value is a ``dict`` with orignal
    value keys and the replacements as values.

    """
    column_aligns: str = field(default=None)
    """The alignment/justification (i.e. ``|l|l|`` for two columns).  If not
    provided, they are automatically generated based on the columns of the
    table.

    """
    percent_column_names: Sequence[str] = field(default=())
    """Column names that have a percent sign to be escaped."""

    make_percent_column_names: Dict[str, int] = field(default_factory=dict)
    """Each columnn in the map will get rounded to the value * 100 of the name.
    For example, ``{'ann_per': 3}`` will round column ``ann_per`` to 3 decimal
    places.

    """
    format_thousands_column_names: Dict[str, Optional[Dict[str, Any]]] = \
        field(default_factory=dict)
    """Columns to format using thousands.  The keys are the column names of the
    table and the values are either ``None`` or the keyword arguments to
    :meth:`format_thousand`.

    """
    format_scientific_column_names: Dict[str, Optional[int]] = \
        field(default_factory=dict)
    """Format a column using LaTeX formatted scientific notation using
    :meth:`format_scientific`.  Keys are column names and values is the mantissa
    length or 1 if ``None``.

    """
    column_evals: Dict[str, str] = field(default_factory=dict)
    """Keys are column names with values as functions (i.e. lambda expressions)
    evaluated with a single column value parameter.  The return value replaces
    the column identified by the key.

    """
    read_kwargs: Dict[str, str] = field(default_factory=dict)
    """Keyword arguments used in the :meth:`~pandas.read_csv` call when reading
    the CSV file.

    """
    write_kwargs: Dict[str, str] = field(
        default_factory=lambda: {'disable_numparse': True})
    """Keyword arguments used in the :meth:`~tabulate.tabulate` call when
    writing the table.  The default tells :mod:`tabulate` to not parse/format
    numerical data.

    """
    replace_nan: str = field(default=None)
    """Replace NaN values with a the value of this field as :meth:`tabulate` is
    not using the missing value due to some bug I assume.

    """
    blank_columns: List[int] = field(default_factory=list)
    """A list of column indexes to set to the empty string (i.e. 0th to fixed
    the ``Unnamed: 0`` issues).

    """
    bold_cells: List[Tuple[int, int]] = field(default_factory=list)
    """A list of row/column cells to bold."""

    bold_max_columns: List[str] = field(default_factory=list)
    """A list of column names that will have its max value bolded."""

    capitalize_columns: Dict[str, bool] = field(default_factory=dict)
    """Capitalize either sentences (``False`` values) or every word (``True``
    values).  The keys are column names.

    """
    index_col_name: str = field(default=None)
    """If set, add an index column with the given name."""

    code_pre: str = field(default=None)
    """Python code executed that manipulates the table's dataframe before
    modifications made by this class.  The code has a local ``df`` variable and
    the returned value is used as the replacement.  This is usually a one-liner
    used to subset the data etc.  The code is evaluated with :func:`eval`.

    """
    code_post: str = field(default=None)
    """Like :obj:`code_pre` but modifies the table after this class's
    modifications of the table.

    """
    def __post_init__(self):
        super().__init__()
        if isinstance(self.uses, str):
            self.uses = re.split(r'\s*,\s*', self.uses)
        if isinstance(self.hlines, (tuple, list)):
            self.hlines = set(self.hlines)
        if isinstance(self.double_hlines, (tuple, list)):
            self.double_hlines = set(self.double_hlines)
        self._formatted_dataframe = PersistedWork(
            '_formatted_dataframe', self, transient=True)

    @property
    def package_name(self) -> str:
        """Return the package name for the table in ``table_path``."""
        fname = self.definition_file.name
        m = self._FILE_NAME_REGEX.match(fname)
        if m is None:
            raise LatexTableError(f'does not appear to be a YAML file: {fname}')
        return m.group(1)

    @property
    def columns(self) -> str:
        """Return the columns field in the Latex environment header."""
        cols: str = self.column_aligns
        if cols is None:
            df = self.formatted_dataframe
            cols = 'l' * df.shape[1]
            cols = '|' + '|'.join(cols) + '|'
        return cols

    @staticmethod
    def format_thousand(x: int, apply_k: bool = True,
                        add_comma: bool = True) -> str:
        """Format a number as a string with comma separating thousands.

        :param x: the number to format

        :param apply_k: add a ``K`` to the end of large numbers

        :param add_comma: whether to add a comma

        """
        add_k = False
        if x > 10000:
            if apply_k:
                x = round(x / 1000)
                add_k = True
        if add_comma:
            x = f'{x:,}'
        else:
            x = str(x)
        if add_k:
            x += 'K'
        return x

    @staticmethod
    def format_scientific(x: float, sig_digits: int = 1) -> str:
        nstr: str = f'{{0:.{sig_digits}e}}'.format(x)
        if 'e' in nstr:
            base, exponent = nstr.split('e')
            base = base[:-2] if base.endswith('.0') else base
            nstr = f'{base} \\times 10^{{{int(exponent)}}}'
        return f'${nstr}$'

    def _apply_df_eval_pre(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.code_pre is not None:
            _locs = locals()
            exec(self.code_pre)
            df = _locs['df']
        return df

    def _apply_df_number_format(self, df: pd.DataFrame) -> pd.DataFrame:
        col: str
        for col in self.percent_column_names:
            df[col] = df[col].apply(lambda s: s.replace('%', '\\%'))
        kwargs: Optional[Dict[str, Any]]
        for col, kwargs in self.format_thousands_column_names.items():
            kwargs = {} if kwargs is None else kwargs
            df[col] = df[col].apply(lambda x: self.format_thousand(x, **kwargs))
        for col, mlen in self.format_scientific_column_names.items():
            mlen = 1 if mlen is None else mlen
            df[col] = df[col].apply(lambda x: self.format_scientific(x, mlen))
        for col, rnd in self.make_percent_column_names.items():
            fmt = f'{{v:.{rnd}f}}\\%'
            df[col] = df[col].apply(
                lambda v: fmt.format(v=round(v * 100, rnd), rnd=rnd))
        return df

    def _apply_df_eval_post(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.code_post is not None:
            exec(self.code_post)
        for col, code, in self.column_evals.items():
            func = eval(code)
            df[col] = df[col].apply(func)
        return df

    def _apply_df_add_indexes(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.index_col_name is not None:
            df[self.index_col_name] = range(1, len(df) + 1)
            cols = df.columns.to_list()
            cols = [cols[-1]] + cols[:-1]
            df = df[cols]
        return df

    def _apply_df_column_modifies(self, df: pd.DataFrame) -> pd.DataFrame:
        col: str
        repl: Dict[Any, Any]
        for col, repl in self.column_value_replaces.items():
            df[col] = df[col].apply(lambda v: repl.get(v, v))
        df = df.drop(columns=self.column_removes)
        if self.column_keeps is not None:
            df = df[self.column_keeps]
        df = df.rename(columns=self.column_renames)
        return df

    def _apply_df_font_format(self, df: pd.DataFrame) -> pd.DataFrame:
        if self.replace_nan is not None:
            df = df.fillna(self.replace_nan)
        if len(self.blank_columns) > 0:
            cols = df.columns.to_list()
            for i in self.blank_columns:
                cols[i] = ''
            df.columns = cols
        if len(self.bold_cells) > 0:
            df = self._apply_df_bold_cells(df, self.bold_cells)
        return df

    def _apply_df_bold_cells(self, df: pd.DataFrame,
                             cells: Sequence[Tuple[int, int]]):
        str_cols: bool = len(cells) > 0 and isinstance(cells[0][1], str)
        cixs: Dict[str, int] = dict(zip(df.columns, it.count()))
        r: int
        c: int
        for r, c in cells:
            val: Any = df[c].iloc[r] if str_cols else df.iloc[r, c]
            fmt: str = '\\textbf{' + str(val) + '}'
            if str_cols:
                c = cixs[c]
            df.iloc[r, c] = fmt
        return df

    def _apply_df_capitalize(self, df: pd.DataFrame):
        for col, capwords in self.capitalize_columns.items():
            fn: Callable = string.capwords if capwords else str.capitalize
            df[col] = df[col].apply(fn)
        return df

    def _get_bold_columns(self, df: pd.DataFrame) -> Tuple[Tuple[int, int]]:
        if len(self.bold_max_columns) > 0:
            cixs: List[str] = self.bold_max_columns
            return tuple(zip(
                map(lambda cix: df.index.get_loc(df[cix].idxmax()), cixs),
                cixs))
        else:
            return ()

    @property
    def dataframe(self) -> pd.DataFrame:
        """The Pandas dataframe that holds the CSV data."""
        if not hasattr(self, '_dataframe_val'):
            self._dataframe_val = pd.read_csv(self.path, **self.read_kwargs)
        return self._dataframe_val

    @dataframe.setter
    def dataframe(self, dataframe: pd.DataFrame):
        """The Pandas dataframe that holds the CSV data."""
        self._dataframe_val = dataframe
        self._formatted_dataframe.clear()

    @property
    @persisted('_formatted_dataframe')
    def formatted_dataframe(self) -> pd.DataFrame:
        """The :obj:`dataframe` with the formatting applied to it used to create
        the Latex table.  Modifications such as string replacements for adding
        percents is done.

        """
        df: pd.DataFrame = self.dataframe
        # Pandas 2.x dislikes mixed float with string dtypes
        df = df.astype(object)
        df = self._apply_df_eval_pre(df)
        bold_cols: Tuple[Tuple[int, int]] = self._get_bold_columns(df)
        df = self._apply_df_number_format(df)
        df = self._apply_df_eval_post(df)
        df = self._apply_df_bold_cells(df, bold_cols)
        df = self._apply_df_capitalize(df)
        df = self._apply_df_add_indexes(df)
        df = self._apply_df_column_modifies(df)
        df = self._apply_df_font_format(df)
        return df

    def _get_table_rows(self, df: pd.DataFrame) -> Iterable[List[Any]]:
        cols = [tuple(map(lambda c: f'\\textbf{{{c}}}', df.columns))]
        return it.chain(cols, map(lambda x: x[1].tolist(), df.iterrows()))

    def _get_tabulate_params(self) -> Dict[str, Any]:
        params = dict(tablefmt='latex_raw', headers='firstrow')
        params.update(self.write_kwargs)
        return params

    def _write_table(self, depth: int, writer: TextIOWrapper):
        df: pd.DataFrame = self.formatted_dataframe
        table_rows: Iterable[List[Any]] = self._get_table_rows(df)
        params: Dict[str, Any] = self._get_tabulate_params()
        tab_lines: List[str] = tabulate(table_rows, **params).split('\n')
        for lix, ln in enumerate(tab_lines[1:-1]):
            self._write_line(ln.strip(), depth, writer)
            if (lix - 2) in self.hlines:
                self._write_line('\\hline', depth, writer)
            if (lix - 2) in self.double_hlines:
                self._write_line('\\hline \\hline', depth, writer)

    def write(self, depth: int = 0, writer: TextIOWrapper = sys.stdout):
        params: Dict[str, Any] = dict(self.asdict())
        table = StringIO()
        self._write_table(2, table)
        params['table'] = table.getvalue().rstrip()
        self._write_block(self.template % params, depth, writer)

    def _serialize_dict(self) -> Dict[str, Any]:
        dct = self.asdict()
        def_inst = self.__class__(
            path=None,
            name=None,
            template=self.template,
            caption=None)
        dels: List[str] = []
        for k, v in dct.items():
            if (not hasattr(def_inst, k) or v == getattr(def_inst, k)) or \
               (isinstance(v, (list, set, tuple, dict)) and len(v) == 0):
                dels.append(k)
        for k in dels:
            del dct[k]
        return dct

    def serialize(self) -> Dict[str, Any]:
        """Return a data structure usable for YAML or JSON output by flattening
        Python objects.

        """
        tab_name: str = self.name
        # using json to recursively convert OrderedDict to dicts
        tab_def: Dict[str, Any] = self._serialize_dict()
        del tab_def['name']
        return {tab_name: tab_def}

    def __str__(self):
        return self.name
