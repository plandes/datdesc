"""Metadata container classes.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import (
    Tuple, Any, Dict, List, Set, Sequence,
    ClassVar, Optional, Iterable, Union, Type
)
from dataclasses import dataclass, field
import logging
import sys
from frozendict import frozendict
import itertools as it
import textwrap as tw
import parse
from io import StringIO, TextIOBase, TextIOWrapper
import json
from pathlib import Path
import pandas as pd
from tabulate import tabulate
from zensols.config import Dictable
from zensols.persist import PersistableContainer, persisted, FileTextUtil
from . import DataDescriptionError, Table, TableFactory

logger = logging.getLogger(__name__)


@dataclass(repr=False)
class DataFrameDescriber(PersistableContainer, Dictable):
    """A class that contains a Pandas dataframe, a description of the data, and
    descriptions of all the columns in that dataframe.

    """
    _PERSITABLE_PROPERTIES: ClassVar[Set[str]] = {'_meta_val'}
    _TABLE_FORMAT: ClassVar[str] = '{name}Tab'

    name: str = field()
    """The description of the data this describer holds."""

    df: pd.DataFrame = field()
    """The dataframe to describe."""

    desc: str = field()
    """The description of the data frame."""

    head: str = field(default=None)
    """A short summary of the table and used in :obj:`.Table.head`."""

    meta_path: Optional[Path] = field(default=None)
    """A path to use to create :obj:`meta` metadata.

    :see: :obj:`meta`

    """
    meta: pd.DataFrame = field(default=None)
    """The column metadata for :obj:`dataframe`, which needs columns ``name``
    and ``description``.  If this is not provided, it is read from file
    :obj:`meta_path`.  If this is set to a tuple of tuples, a dataframe is
    generated from the form::

        ((<column name 1>, <column description 1>),
         (<column name 2>, <column description 2>) ...

    If both this and :obj:`meta_path` are not provided, the following is used::

        (('description', 'Description'),
         ('value', 'Value')))

    """
    table_kwargs: Dict[str, Any] = field(default_factory=dict)
    """Additional key word arguments given when creating a table in
    :meth:`create_table`.

    """
    index_meta: Dict[Any, str] = field(default=None)
    """The index metadata, which maps index values to descriptions of the
    respective row.

    """
    mangle_file_names: bool = field(default=False)
    """Whether to normalize output file names."""

    def __post_init__(self):
        super().__init__()

    @classmethod
    def from_columns(cls: Type,
                     source: Union[pd.DataFrame, Sequence[Sequence[Any]]],
                     name: str = None, desc: str = None) -> DataFrameDescriber:
        """Create a new instance by transposing a column data into a new
        dataframe describer.  If ``source`` is a dataframe, it that has the
        following columns:

            * ``column``: the column names of the resulting describer
            * ``meta``: the description that makes up the :obj:`meta`
            * ``data``: :class:`~typing.Sequence`'s of the data

        Otherwise, each element of the sequence is a row of column, meta
        descriptions, and data sequences.

        :param source: the data as columns

        :param name: used for :obj:`name`

        :param desc: used for :obj:`desc`

        """
        df: pd.DataFrame
        if isinstance(source, pd.DataFrame):
            df = source
        else:
            df = pd.DataFrame(source, columns='column meta data'.split())
        data: pd.Series = df['data']
        max_rows = data.apply(len).max()
        rows: List[List[Any]] = list(it.repeat([], max_rows))
        for cix, col in enumerate(data):
            for rix, v in enumerate(col):
                row = rows[rix]
                while len(row) < cix:
                    row.append(None)
                row.append(v)
        return DataFrameDescriber(
            name=name,
            desc=desc,
            df=pd.DataFrame(data=rows, columns=df['column']),
            meta=tuple(df[['column', 'meta']].itertuples(
                index=False, name=None)))

    def _meta_dict_to_dataframe(self, meta: Tuple[Tuple[str, str]]):
        return pd.DataFrame(data=map(lambda t: t[1], meta),
                            index=map(lambda t: t[0], meta),
                            columns=['description'])

    @property
    def _meta(self) -> pd.DataFrame:
        if self._meta_val is None:
            self._meta_val = pd.read_csv(self.meta_path, index_col='name')
        return self._meta_val

    @_meta.setter
    def _meta(self, meta: Union[pd.DataFrame, Tuple[Tuple[str, str], ...]]):
        if meta is None:
            meta = (('description', 'Description'),
                    ('value', 'Value'))
        if isinstance(meta, (list, tuple)):
            self._meta_val = self._meta_dict_to_dataframe(meta)
        else:
            self._meta_val = meta

    @property
    @persisted('_csv_path', transient=True)
    def csv_path(self) -> Path:
        """The CVS file that contains the data this instance describes."""
        fname: str = self.name
        if self.mangle_file_names:
            fname = FileTextUtil.normalize_text(fname)
        fname = fname + '.csv'
        return Path(fname)

    def get_table_name(self, form: str) -> str:
        """The table derived from :obj:`name`.

        :param form: specifies the format: ``file`` means file-friendly,
                     ``camel`` is for reverse camel notation

        """
        name: str = self.csv_path.stem
        if form == 'file':
            pass
        elif form == 'camel':
            name = ''.join(map(str.capitalize, name.split('-')))
            name = name[0].lower() + name[1:]
        else:
            raise DataDescriptionError(f'No table form name: {form}')
        return name

    def derive(self, *,
               name: str = None,
               df: pd.DataFrame = None,
               desc: str = None,
               meta: Union[pd.DataFrame, Tuple[Tuple[str, str], ...]] = None,
               index_meta: Dict[Any, str] = None) -> DataFrameDescriber:
        """Create a new instance based on this instance and replace any
        non-``None`` kwargs.

        If ``meta`` is provided, it is merged with the metadata of this
        instance.  However, any metadata provided must match in both column
        names and descriptions.

        :param name: :obj:`name`

        :param df: :obj:`df`

        :param desc: :obj:`desc`

        :param meta: :obj:`meta`

        :raise DataDescriptionError: if multiple metadata columns with differing
                                     descriptions are found

        """
        name = self.name if name is None else name
        desc = self.desc if desc is None else desc
        index_meta = self.index_meta if index_meta is None else index_meta
        if meta is None:
            meta = self.meta.copy()
        elif not isinstance(meta, pd.DataFrame):
            meta = self._meta_dict_to_dataframe(meta)
        if df is not None:
            # overwrite passed in metadata with this instance's by name
            df_ovr: pd.DataFrame = self.meta[~self.meta.index.isin(meta.index)]
            meta = pd.concat((df_ovr.copy(), meta)).drop_duplicates()
        cols: Set[str] = set(df.columns)
        # stability requres filter instead rather than set operations
        idx = list(filter(lambda n: n in cols, meta.index))
        meta = meta.loc[idx]
        dup_cols: List[str] = meta[meta.index.duplicated()].\
            index.drop_duplicates().to_list()
        if len(dup_cols) > 0:
            m: pd.DataFrame = meta.drop_duplicates()
            s = ', '.join(map(
                lambda c: f"{c}: [{', '.join(m.loc[c]['description'])}]",
                dup_cols))
            raise DataDescriptionError(f'Metadata has duplicate columns: {s}')
        return self.__class__(
            name=name,
            df=df,
            desc=desc,
            meta=meta,
            index_meta=index_meta)

    def df_with_index_meta(self, index_format: str = None) -> pd.DataFrame:
        """Create a dataframe with the first column containing index metadata.
        This uses :obj:`index_meta` to create the column values.

        :param index_format: the new index column format using ``index`` and
                             ``value``, which defaults to ``{index}``

        :return: the dataframe with a new first column of the index metadata, or
                 :obj:`df` if :obj:`index_meta` is ``None``

        """
        df: pd.DataFrame = self.df
        meta: Dict[Any, str] = self.index_meta
        if meta is not None:
            ix: List[Any] = df.index.to_list()
            if index_format is None:
                ix = list(map(lambda i: meta[i], ix))
            else:
                ix = list(map(
                    lambda i: index_format.format(index=i, value=meta[i]), ix))
            df = df.copy()
            df.insert(0, str(df.index.name), ix)
        return df

    def derive_with_index_meta(self, index_format: str = None) -> \
            DataFrameDescriber:
        """Like :meth:`derive`, but the dataframe is generated with
        :meth:`df_with_index_meta` using ``index_format`` as a parameter.

        :param index_format: see :meth:`df_with_index_meta`

        """
        dfi: pd.DataFrame = self.df_with_index_meta(index_format)
        clone: DataFrameDescriber = self.derive(df=dfi.reset_index(drop=True))
        clone.index_meta = None
        return clone

    @property
    def T(self) -> DataFrameDescriber:
        """See :meth:`transpose`."""
        return self.transpose()

    def transpose(self,
                  row_names: Tuple[int, str, str] = ((0, 'value', 'Value'),),
                  name_column: str = 'name', name_description: str = 'Name',
                  index_column: str = 'description') -> DataFrameDescriber:
        """Transpose all data in this descriptor by transposing :obj:`df` and
        swapping :obj:`meta` with :obj:`index_meta` as a new instance.

        :param row_names: a tuple of (row index in :obj:`df`, the column in the
                          new :obj:`df` and the metadata description of that
                          column in the new :obj:`df`; the default takes only
                          the first row

        :param name_column: the column name this instance's :obj:`df`

        :param description_column: the column description this instance's
                                   :obj:`df`

        :param index_column: the name of the new index in the returned instance

        :return: a new derived instance of the transposed data

        """
        df: pd.DataFrame = self.df
        df = df.iloc[map(lambda t: t[0], row_names)]
        df = df.T
        df.columns = list(map(lambda t: t[1], row_names))
        df.insert(0, name_column, df.index)
        df.index.name = index_column
        prev_meta: pd.DataFrame = self.meta.loc[self.df.columns]
        index_meta: Dict[str, str] = dict(zip(
            prev_meta.index, prev_meta['description']))
        meta: List[str] = [(name_column, name_description)]
        meta.extend(map(lambda t: (t[1], t[2]), row_names))
        return self.derive(
            df=df,
            meta=tuple(meta),
            index_meta=index_meta)

    def save_csv(self, output_dir: Path = Path('.')) -> Path:
        """Save as a CSV file using :obj:`csv_path`."""
        out_file: Path = output_dir / self.csv_path
        self.df.to_csv(out_file)
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'wrote: {out_file}')
        return out_file

    def save_excel(self, output_dir: Path = Path('.')) -> Path:
        """Save as an Excel file using :obj:`csv_path`.  The same file naming
        semantics are used as with :meth:`.DataDescriber.save_excel`.

        :see: :meth:`.DataDescriber.save_excel`

        """
        out_file: Path = output_dir / self.name
        dd = DataDescriber((self,), name=self.name)
        return dd.save_excel(out_file)

    def create_table(self, **kwargs) -> Table:
        """Create a table from the metadata using:

          * :obj:`csv_path` as :obj:`.Table.path`
          * :obj:`df` as :obj:`.Table.dataframe`
          * :obj:`desc` as :obj:`.Table.caption`
          * :meth:`~zensols.config.dictable.Dictable.asdict` as
            :obj:`.Table.column_renames`

        :param kwargs: key word arguments that override the default
                       parameterized data passed to :class:`.Table`

        """
        fac: TableFactory = TableFactory.default_instance()
        params: Dict[str, Any] = dict(
            head=self.head,
            path=self.csv_path,
            caption=self.desc,
            column_renames=dict(filter(
                lambda x: x[1] is not None,
                self.column_descriptions.items())))
        params.update(self.table_kwargs)
        params.update(kwargs)
        table: Table = fac.create(**params)
        name: str = self.get_table_name('camel')
        table.name = self._TABLE_FORMAT.format(name=name)
        table.dataframe = self.df
        return table

    @classmethod
    def from_table(cls: Type, tab: Table) -> DataFrameDescriber:
        """Create a frame descriptor from a :class:`.Table`."""
        def filter_kwargs(t: Tuple[str, Any]) -> bool:
            k, v = t
            if v is None or k.startswith('_') or k in kw_skips:
                return False
            return not isinstance(v, (tuple, list, set, dict)) or len(v) > 0

        kw_skips: Set[str] = {'name', 'df', 'desc', 'meta'}
        res: parse.Result = parse.parse(cls._TABLE_FORMAT, tab.name)
        if res is None:
            raise DataDescriptionError(f"Bad table name: '{tab.name}'")
        df: pd.DataFrame = tab.dataframe
        renames: Dict[str, str] = tab.column_renames
        col: str
        for col in df.columns:
            if col not in renames:
                renames[col] = col
        meta = pd.DataFrame(renames.items(), columns='name description'.split())
        meta.index = meta['name']
        meta = meta.drop(columns=['name'])
        kws: Dict[str, Any] = dict(filter(filter_kwargs, tab.__dict__.items()))
        if len(kws) == 0:
            kws = None
        return DataFrameDescriber(
            name=res['name'],
            df=df,
            desc=tab.caption,
            meta=meta,
            table_kwargs=kws)

    def format_table(self):
        """Replace (in place) dataframe :obj:`df` with the formatted table
        obtained with :obj:`.Table.formatted_dataframe`.  The :class:`.Table` is
        created by with :meth:`create_table`.

        """
        self.df = self.create_table().formatted_dataframe

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout,
              df_params: Dict[str, Any] = None):
        """

        :param df_params: the formatting pandas options, which defaults to
                          ``max_colwidth=80``

        """
        if df_params is None:
            df_params = dict(max_colwidth=self.WRITABLE_MAX_COL)
        self._write_line(f'name: {self.name}', depth, writer, max_len=True)
        self._write_line(f'desc: {self.desc}', depth, writer, max_len=True)
        self._write_line('dataframe:', depth, writer)
        dfs: str = self.df.to_string(**df_params)
        self._write_block(dfs, depth + 1, writer)
        self._write_line('columns:', depth, writer)
        self._write_dict(self.column_descriptions, depth + 1, writer)
        if self.index_meta is not None:
            self._write_line('index:', depth, writer)
            self._write_dict(self.index_meta, depth + 1, writer)

    def write_pretty(self, depth: int = 0, writer: TextIOBase = sys.stdout,
                     include_metadata: bool = False,
                     title_format: str = '{name} ({desc})', **tabulate_params):
        """Like :meth:`write`, but generate a visually appealing table and
        optionally column metadata.

        """
        if 'showindex' not in tabulate_params:
            tabulate_params['showindex'] = False
        cols: Dict[str, Any] = self.column_descriptions
        title_meta: Dict[str, Any] = dict(
            name=self.name, desc=self.desc, columns=cols)
        title: str = title_format.format(**title_meta)
        table: str = tabulate(
            self.df,
            headers=self.df.columns,
            **tabulate_params)
        self._write_line(title, depth, writer, max_len=True)
        if include_metadata:
            self._write_line('columns:', depth, writer)
            self._write_dict(cols, depth + 1, writer)
        self._write_block(table, depth, writer)

    @property
    def column_descriptions(self) -> Dict[str, str]:
        """A dictionary of name to Descriptions of the column metadata created
        from :obj:`meta`.  Any missing column metadata will result in ``None``
        dictionary values.

        """
        dfm: pd.DataFrame = self.meta
        descs: Dict[str, str] = {}
        col: str
        for col in self.df.columns:
            if col in dfm.index:
                descs[col] = dfm.loc[col]['description']
            else:
                descs[col] = None
        return descs

    def _from_dictable(self, *args, **kwargs) -> Dict[str, str]:
        dct: Dict[str, Any] = super()._from_dictable(*args, **kwargs)
        dct.pop('df')
        dct.pop('meta')
        dct['df'] = json.loads(self.df.to_json())
        dct['meta'] = json.loads(self.meta.to_json())
        return dct

    @classmethod
    def _from_json(cls: Type, data: Dict[str, Any]):
        df: Dict[str, Any] = data.pop('df')
        meta: Dict[str, Any] = data.pop('meta')
        return DataFrameDescriber(
            df=pd.read_json(StringIO(json.dumps(df))),
            meta=pd.read_json(StringIO(json.dumps(meta))),
            **data)

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        sio = StringIO()
        sio.write(self.name)
        if self.head is not None:
            sio.write(f'[{self.head}]')
        if self.desc is not None:
            sio.write(f': {self.desc}')
        return sio.getvalue()


DataFrameDescriber.meta = DataFrameDescriber._meta


@dataclass(repr=False)
class DataDescriber(PersistableContainer, Dictable):
    """Container class for :class:`.DataFrameDescriber` instances.  It also
    saves their instances as CSV data files and YAML configuration files.

    """
    DEFAULT_CSV_DIR: ClassVar[Path] = Path('config/csv')
    DEFAULT_YAML_DIR: ClassVar[Path] = Path('results/config')
    DEFAULT_EXCEL_DIR: ClassVar[Path] = Path('results')

    SHEET_NAME_MAXLEN: ClassVar[int] = 31
    """Maximum allowed characters in an Excel spreadsheet's name."""

    describers: Tuple[DataFrameDescriber, ...] = field()
    """The contained dataframe and metadata."""

    name: str = field(default='default')
    """The name of the dataset."""

    mangle_sheet_name: bool = field(default=False)
    """Whether to normalize the Excel sheet names when
    :class:`xlsxwriter.exceptions.InvalidWorksheetName` is raised.

    """
    @property
    @persisted('_describers_by_name', transient=True)
    def describers_by_name(self) -> Dict[str, DataFrameDescriber]:
        """Data frame describers keyed by the describer name."""
        return frozendict(dict(map(lambda t: (t.name, t), self.describers)))

    def derive(self, **kwargs) -> DataDescriber:
        """Create a new instance based on this instance and replace any
        non-``None`` kwargs.

        :param kwargs: the key word arguments to replace any field data from
                       this instance

        :return: a new instance with replaced data, or a clone if called with no
                 key word arguments

        """
        params = dict(self.__dict__)
        params.update(kwargs)
        return self.__class__(**params)

    def derive_with_index_meta(self, index_format: str = None) -> \
            DataFrameDescriber:
        """Applies :meth:`.DataFrameDescriber.derive_with_index_meta` to each
        element of :obj:`describers`.

        """
        meth = DataFrameDescriber.derive_with_index_meta
        return self.derive(describers=tuple(map(meth, self.describers)))

    def add_summary(self) -> DataFrameDescriber:
        """Add a new metadata like :class:`.DataFrameDescriber` as a first entry
        in :obj:`describers` that describes what data this instance currently
        has.

        :return: the added metadata :class:`.DataFrameDescriber` instance

        """
        rows: List[Tuple[Any, ...]] = []
        dfd: DataFrameDescriber
        for dfd in self.describers:
            rows.append((dfd.name, dfd.desc, len(dfd.df), len(dfd.df.columns)))
        summary = DataFrameDescriber(
            name='data-summary',
            desc='Data summary',
            df=pd.DataFrame(
                data=rows,
                columns='name description rows columns'.split()),
            meta=(('name', 'data descriptor'),
                  ('description', 'data description'),
                  ('rows', 'number of rows in the dataset'),
                  ('columns', 'number of columns in the dataset')))
        self.describers = (summary, *self.describers)
        return summary

    @staticmethod
    def _get_col_widths(df: pd.DataFrame, min_col: int = 100):
        # we concatenate this to the max of the lengths of column name and
        # its values for each column, left to right
        return [max([min(min_col, len(str(s))) for s in df[col].values] +
                    [len(col)]) for col in df.columns]

    def save_excel(self, output_file: Path) -> Path:
        """Save all provided dataframe describers to an Excel file.

        :param output_file: the Excel file to write; ``.xlsx`` will be postpend
                            if no extension exists

        """
        from xlsxwriter.worksheet import Worksheet
        if len(output_file.suffix) == 0:
            output_file = output_file.parent / f'{output_file.name}.xlsx'
        # create a Pandas Excel writer using XlsxWriter as the engine.
        with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
            for desc in self.describers:
                sheet_name: str = desc.name
                if self.mangle_sheet_name:
                    sheet_name = FileTextUtil.normalize_text(sheet_name)
                # convert the dataframe to an XlsxWriter Excel object.
                if len(sheet_name) > self.SHEET_NAME_MAXLEN:
                    if logger.isEnabledFor(logging.WARNING):
                        logger.warning(
                            'truncating sheet name to Excel limit of ' +
                            f'{self.SHEET_NAME_MAXLEN}: {sheet_name}')
                    sheet_name = tw.shorten(
                        text=sheet_name,
                        width=self.SHEET_NAME_MAXLEN,
                        placeholder='...')
                desc.df.to_excel(writer, sheet_name=sheet_name, index=False)
                # set comments of header cells to descriptions
                worksheet: Worksheet = writer.sheets[sheet_name]
                cdesc: Dict[str, str] = desc.asdict()
                col: str
                for cix, col in enumerate(desc.df.columns):
                    comment: str = cdesc.get(col)
                    if comment is None:
                        if logger.isEnabledFor(logging.WARNING):
                            logger.warning(f"missing comment in '{col}' " +
                                           f"column in '{desc.name}'")
                        continue
                    worksheet.write_comment(0, cix, comment)
                # simulate column auto-fit
                for i, width in enumerate(self._get_col_widths(desc.df)):
                    worksheet.set_column(i, i, width)
        logger.info(f'wrote {output_file}')
        return output_file

    def save_csv(self, csv_dir: Path) -> List[Path]:
        """Save all provided dataframe describers to an CSV files.

        :param csv_dir: the directory of where to save the data

        """
        paths: List[Path] = []
        desc: DataFrameDescriber
        for desc in self.describers:
            out_file: Path = csv_dir / desc.csv_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
            desc.df.to_csv(out_file, index=False)
            logger.info(f'saved csv file to: {out_file}')
            paths.append(out_file)
        logger.info(f'saved csv files to directory: {csv_dir}')
        return paths

    def save_yaml(self, csv_dir: Path, yaml_dir: Path) -> List[Path]:
        """Save all provided dataframe describers YAML files used by the
        ``datdesc`` command.

        :param csv_dir: the directory of where to save the data

        :param yaml_dir: the directory where the YAML config files are saved

        """
        fac: TableFactory = TableFactory.default_instance()
        paths: List[Path] = []
        desc: DataFrameDescriber
        for desc in self.describers:
            csv_file: Path = csv_dir / desc.csv_path
            name: str = desc.get_table_name('file')
            out_file: Path = yaml_dir / f'{name}-table.yml'
            tab: Table = desc.create_table()
            tab.path = csv_file
            out_file.parent.mkdir(parents=True, exist_ok=True)
            fac.to_file(tab, out_file)
            logger.info(f'saved yml file to: {out_file}')
            paths.append(out_file)
        return paths

    def save(self, csv_dir: Path = None, yaml_dir: Path = None,
             excel_path: Union[bool, Path] = None) -> List[Path]:
        """Save both the CSV and YAML configuration file.

        :param csv_dir: the directory of where to save the data

        :param yaml_dir: the directory of where to save the YAML files

        :param excel_path: where to write the Excel file if not ``None`` or
                           ``False``, otherwise create in a new ``results``
                           directory with :obj:`name`

        :see: :meth:`save_csv`

        :see: :meth:`save_yaml`

        """
        csv_dir = self.DEFAULT_CSV_DIR if csv_dir is None else csv_dir
        yaml_dir = self.DEFAULT_YAML_DIR if yaml_dir is None else yaml_dir
        paths: List[Path] = self.save_csv(csv_dir)
        paths = paths + self.save_yaml(csv_dir, yaml_dir)
        if excel_path is False:
            excel_path = None
        elif excel_path is True:
            excel_path = self.DEFAULT_EXCEL_DIR / self.name
        if excel_path is not None:
            paths.append(self.save_excel(excel_path))
        return paths

    @classmethod
    def from_describer(cls: Type, dfd: DataFrameDescriber) -> DataDescriber:
        """Create a singleton describer.  The :obj:`name` is taken from the
        ``dfd`` :obj:`.DataFrameDescriber.name`.

        """
        return DataDescriber(describers=(dfd,), name=dfd.name)

    @classmethod
    def from_yaml_file(cls: Type, path: Path) -> DataDescriber:

        """Create a data descriptor from a previously written YAML/CSV files
        using :meth:`save`.

        :see: :meth:`save`

        :see: :meth:`DataFrameDescriber.from_table`

        """
        fac: TableFactory = TableFactory.default_instance()
        tables: Table[Table, ...] = tuple(fac.from_file(path))
        return DataDescriber(
            describers=tuple(map(DataFrameDescriber.from_table, tables)),
            name=path.name)

    def to_json(self, writer: TextIOBase):
        """Serialize the object to JSON that can be re-instantiated using
        :meth:`from_json`.

        :param writer: the data sink

        :param kwargs: the key word arguments to give to :func:`json.dump`

        """
        self.asjson(writer)

    @classmethod
    def from_json(cls: Type, reader: TextIOWrapper) -> DataDescriber:
        """Unserialize a JSON stream into a data descriptor.

        :param reader: the file / data stream

        """
        data: Dict[str, Any] = json.load(reader)
        describers: List[Dict[str, Any]] = data.pop('describers')
        return DataDescriber(
            describers=tuple(map(DataFrameDescriber._from_json, describers)),
            **data)

    def format_tables(self):
        """See :meth:`.DataFrameDescriber.format_table`."""
        desc: DataFrameDescriber
        for desc in self.describers:
            desc.format_table()

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout,
              df_params: Dict[str, Any] = None):
        """

        :param df_params: the formatting pandas options, which defaults to
                          ``max_colwidth=80``

        """
        desc: DataFrameDescriber
        for desc in self.describers:
            self._write_line(f'{desc.name}:', depth, writer)
            desc.write(depth + 1, writer, df_params=df_params)

    def __len__(self) -> int:
        return len(self.describers)

    def __iter__(self) -> Iterable[DataFrameDescriber]:
        return iter(self.describers)

    def keys(self) -> Sequence[str]:
        return self.describers_by_name.keys()

    def items(self) -> Iterable[Tuple[str, DataFrameDescriber]]:
        return self.describers_by_name.items()

    def __contains__(self, name: str) -> bool:
        return name in self.describers_by_name

    def __getitem__(self, name: str) -> DataFrameDescriber:
        return self.describers_by_name[name]

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f'{self.name}: describers={self.describers}'
