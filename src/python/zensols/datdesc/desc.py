"""Metadata container classes.

"""
__author__ = 'Paul Landes'

from typing import (
    Tuple, Any, Dict, List, Set, ClassVar, Optional, Iterable, Union
)
from dataclasses import dataclass, field
import logging
import sys
from frozendict import frozendict
from collections import OrderedDict
from io import TextIOBase
from pathlib import Path
import yaml
import pandas as pd
from zensols.config import Dictable
from zensols.persist import PersistableContainer, persisted, FileTextUtil
from . import Table

logger = logging.getLogger(__name__)


@dataclass
class DataFrameDescriber(PersistableContainer, Dictable):
    """A class that contains a Pandas dataframe, a description of the data, and
    descriptions of all the columns in that dataframe.

    """
    _PERSITABLE_PROPERTIES: ClassVar[Set[str]] = {'_metadata_val'}

    name: str = field()
    """The description of the data this describer holds."""

    df: pd.DataFrame = field()
    """The dataframe to describe."""

    desc: str = field()
    """The description of the data frame."""

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
    def __post_init__(self):
        super().__init__()

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
        fname: str = FileTextUtil.normalize_text(self.name) + '.csv'
        return Path(fname)

    @property
    @persisted('_tab_name', transient=True)
    def tab_name(self) -> str:
        """The table derived from :obj:`name`."""
        return self.csv_path.stem.replace('-', '')

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
        params: Dict[str, Any] = dict(
            path=self.csv_path,
            name=f'{self.tab_name}tab',
            caption=self.desc,
            column_renames=dict(filter(lambda x: x[1] is not None,
                                       self.asdict().items())))
        params.update(kwargs)
        table = Table(**params)
        table.dataframe = self.df
        return table

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
        self._write_dict(self.asdict(), depth + 1, writer)

    def _from_dictable(self, *args, **kwargs) -> Dict[str, str]:
        dfm: pd.DataFrame = self.meta
        descs: Dict[str, str] = OrderedDict()
        col: str
        for col in self.df.columns:
            if col in dfm.index:
                descs[col] = dfm.loc[col]['description']
            else:
                descs[col] = None
        return descs


DataFrameDescriber.meta = DataFrameDescriber._meta


@dataclass
class DataDescriber(PersistableContainer, Dictable):
    """Container class for :class:`.DataFrameDescriber` instances.  It also
    saves their instances as CSV data files and YAML configuration files.

    """
    describers: Tuple[DataFrameDescriber] = field()
    """The contained dataframe and metadata.

    """
    name: str = field(default='default')
    """The name of the dataset."""

    output_dir: Path = field(default=Path('results'))
    """The directory where to write the results."""

    csv_dir: Path = field(default=Path('csv'))
    """The directory where to write the CSV files."""

    yaml_dir: Path = field(default=Path('config'))
    """The directory where to write the CSV files."""

    mangle_sheet_name: bool = field(default=False)
    """Whether to normalize the Excel sheet names when
    :class:`xlsxwriter.exceptions.InvalidWorksheetName` is raised.

    """
    def _create_path(self, fname: Union[Path, str]) -> Path:
        return self.output_dir / fname

    @property
    def describers_by_name(self) -> Dict[str, DataFrameDescriber]:
        """Data frame describers keyed by the describer name."""
        return frozendict(dict(map(lambda t: (t.name, t), self.describers)))

    @staticmethod
    def _get_col_widths(df: pd.DataFrame, min_col: int = 100):
        # we concatenate this to the max of the lengths of column name and
        # its values for each column, left to right
        return [max([min(min_col, len(str(s))) for s in df[col].values] +
                    [len(col)]) for col in df.columns]

    def save_excel(self, output_file: Path = None) -> Path:
        """Save all provided dataframe describers to an Excel file.

        :param output_file: the Excel file to write, which needs an ``.xlsx``
                            extension; this defaults to a path created from
                            :obj:`output_dir` and :obj:`name`

        """
        from xlsxwriter.worksheet import Worksheet
        if output_file is None:
            fname: str = FileTextUtil.normalize_text(self.name)
            output_file = self._create_path(f'{fname}.xlsx')
        # create a Pandas Excel writer using XlsxWriter as the engine.
        writer = pd.ExcelWriter(output_file, engine='xlsxwriter')
        for desc in self.describers:
            sheet_name: str = desc.name
            if self.mangle_sheet_name:
                sheet_name = FileTextUtil.normalize_text(sheet_name)
            # convert the dataframe to an XlsxWriter Excel object.
            desc.df.to_excel(writer, sheet_name=sheet_name, index=False)
            # set comments of header cells to descriptions
            worksheet: Worksheet = writer.sheets[sheet_name]
            cdesc: Dict[str, str] = desc.asdict()
            col: str
            for cix, col in enumerate(desc.df.columns):
                comment: str = cdesc[col]
                if comment is None:
                    logger.warning(f'missing column {col} in {desc.name}')
                    continue
                worksheet.write_comment(0, cix, comment)
            # simulate column auto-fit
            for i, width in enumerate(self._get_col_widths(desc.df)):
                worksheet.set_column(i, i, width)
        writer.save()
        logger.info(f'wrote {output_file}')
        return output_file

    def save_csv(self, output_dir: Path = None) -> List[Path]:
        """Save all provided dataframe describers to an CSV files.

        :param output_dir: the directory of where to save the data

        """
        if output_dir is None:
            output_dir = self._create_path(self.csv_dir)
        paths: List[Path] = []
        desc: DataFrameDescriber
        for desc in self.describers:
            out_file: Path = output_dir / desc.csv_path
            out_file.parent.mkdir(parents=True, exist_ok=True)
            desc.df.to_csv(out_file, index=False)
            logger.info(f'saved csv file to: {out_file}')
            paths.append(out_file)
        logger.info(f'saved csv files to directory: {output_dir}')
        return paths

    def save_yaml(self, output_dir: Path = None,
                  yaml_dir: Path = None) -> List[Path]:
        """Save all provided dataframe describers YAML files used by the
        ``datdesc`` command.

        :param output_dir: the directory of where to save the data

        """
        if output_dir is None:
            output_dir = self._create_path(self.csv_dir)
        if yaml_dir is None:
            yaml_dir = self._create_path(self.yaml_dir)
        paths: List[Path] = []
        desc: DataFrameDescriber
        for desc in self.describers:
            csv_file: Path = output_dir / desc.csv_path
            out_file: Path = yaml_dir / f'{desc.tab_name}-table.yml'
            tab: Table = desc.create_table()
            tab.path = csv_file
            tab_def: Dict[str, Any] = tab.serialize()
            out_file.parent.mkdir(parents=True, exist_ok=True)
            with open(out_file, 'w') as f:
                yaml.dump(tab_def, f)
            logger.info(f'saved yml file to: {out_file}')
            paths.append(out_file)
        return paths

    def save(self, output_dir: Path = None,
             yaml_dir: Path = None, include_excel: bool = False) -> List[Path]:
        """Save both the CSV and YAML configuration file.

        :param include_excel: whether to also write the Excel file to its
                              default output file name

        :see: :meth:`save_csv`

        :see :meth:`save_yaml`

        """
        paths: List[Path] = self.save_csv(output_dir)
        paths = paths + self.save_yaml(output_dir, yaml_dir)
        if include_excel:
            paths.append(self.save_excel())
        return paths

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

    def __getitem__(self, name: str) -> DataFrameDescriber:
        return self.describers_by_name[name]
