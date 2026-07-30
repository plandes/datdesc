
"""A stash implementation that uses a Pandas dataframe and stored as a CSV file.

"""
__author__ = 'Paul Landes'
from typing import Any
from collections.abc import Iterable
from dataclasses import dataclass, field
import dataclasses
from datetime import datetime
import logging
import re
from pathlib import Path
import pandas as pd
from zensols.config import Dictable
from zensols.persist import PersistableError, CloseableStash
from zensols.dataclasses.inspect import DataclassMetadata, ClassField
from .desc import DataFrameDescriber

logger = logging.getLogger(__name__)


@dataclass
class DataFrameStash(CloseableStash, Dictable):
    """A backing stash that persists to a CSV file via a Pandas dataframe.  All
    modification go through the :class:`pandas.DataFrame` and then saved with
    :meth:`commit` or :meth:`close`.

    """
    path: Path = field()
    """The path of the file from which to read and write."""

    dataframe: pd.DataFrame = field(default=None)
    """The dataframe to proxy in memory.  This is settable on instantiation but
    read-only afterward.  If this is not set an empty dataframe is created with
    the metadata in this class.

    """
    key_column: str = field(default='key')
    """The spreadsheet column name used to store stash keys."""

    columns: tuple[str, ...] = field(default=('value',))
    """The columns to create in the spreadsheet.  These must be consistent when
    the data is restored.

    """
    sort_columns: tuple[str, ...] = field(default=())
    """If none-``None``, sort rows by the given column."""

    mkdirs: bool = field(default=True)
    """Whether to recusively create the directory where :obj:`path` is stored if
    it does not already exist.

    """
    auto_commit: bool = field(default=True)
    """Whether to save to the file system after any modification."""

    single_column_index: int | None = field(default=0)
    """If this is set, then a single type is assumed for loads and restores.
    Otherwise, if set to ``None``, multiple columns are saved and retrieved.

    """
    def __post_init__(self):
        if self.dataframe is None:
            if self.path.exists():
                self._revert()
            else:
                self._new_instance()
        else:
            self._set(self.dataframe)

    def _new_instance(self):
        self._dataframe_val = pd.DataFrame(columns=self.columns)
        self._dataframe_val.index.name = self.key_column

    def _sort(self, dataframe: pd.DataFrame):
        if len(self.sort_columns) > 0 and len(dataframe) > 0:
            dataframe.sort_values(list(self.sort_columns), inplace=True)

    def _set(self, dataframe: pd.DataFrame):
        self._sort(dataframe)
        self._dataframe_val = dataframe
        self.columns = tuple(self._dataframe_val.columns)
        self.key_column = self._dataframe_val.index.name

    @property
    def _dataframe(self) -> pd.DataFrame:
        return self._dataframe_val

    @_dataframe.setter
    def _dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        if hasattr(self, '_dataframe_val'):
            raise PersistableError(
                'Attempt to modify immutable attribte: dataframe')
        self._dataframe_val = dataframe

    def _revert(self):
        df: pd.DataFrame = pd.read_csv(self.path, index_col=0)
        if self.key_column != df.index.name:
            raise PersistableError(
                f'Instance key column ({self.key_column}) to be equal to ' +
                f'persisted column ({df.index.name})')
        self._set(df)

    def commit(self):
        """Commit changes to the file system."""
        if self.mkdirs:
            self.path.parent.mkdir(parents=True, exist_ok=True)
        df: pd.DataFrame = self._dataframe_val
        df.to_csv(self.path, index_label=df.index.name)

    def _row_to_object(self, name: str, row: tuple[Any, ...]) -> Any:
        if self.single_column_index is not None:
            row = row[self.single_column_index]
        return row

    def _object_to_row(self, name: str, inst: Any) -> \
            tuple[str, tuple[Any, ...]]:
        if self.single_column_index is not None:
            inst = (inst,)
        return inst

    def load(self, name: str) -> Any | tuple[Any, ...]:
        if self.exists(name):
            df: pd.DataFrame = self._dataframe_val
            row = tuple(df.loc[[name]].itertuples(index=False, name=None))[0]
            return self._row_to_object(name, row)

    def get(self, name: str, default: Any = None) -> Any | tuple[Any, ...]:
        if self.exists(name):
            item = self.load(name)
        else:
            item = default
        return item

    def exists(self, name: str) -> bool:
        return name in self._dataframe_val.index

    def dump(self, name: str, inst: Any | tuple[Any, ...]):
        inst = self._object_to_row(name, inst)
        if self.exists(name):
            self._dataframe_val.loc[name] = inst
        else:
            self._append(name, inst)
        if self.auto_commit:
            self.commit()
        else:
            self._sort(self._dataframe)

    def _append(self, name: str, inst: tuple[Any, ...]):
        if not isinstance(inst, (tuple, list)):
            raise PersistableError(
                f'Expecting a tuple or list instance by got {type(inst)}')
        df = self._dataframe_val
        if len(inst) != len(df.columns):
            raise PersistableError(
                f'Expecting input length ({len(inst)}) ' +
                f'alignment with columns length ({len(df.columns)})')
        row = pd.DataFrame([inst], columns=df.columns)
        row = row.astype(df.dtypes.to_dict())
        row.index = [name]
        self._dataframe_val = pd.concat((df, row))
        self._dataframe_val.index.name = df.index.name

    def delete(self, name: str = None):
        if name in self._dataframe_val.index:
            self._dataframe_val = self._dataframe_val.drop(index=[name])
        else:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning(f'does not exist: {name}')
        if self.auto_commit:
            self.commit()

    def clear(self):
        if self.path.exists():
            self.path.unlink()
        self._new_instance()

    def keys(self) -> Iterable[str]:
        return self.dataframe.index

    def values(self) -> Iterable[Any | tuple[Any, ...]]:
        vals = self.dataframe.itertuples(index=True, name=None)
        vals = map(lambda t: self._row_to_object(t[0], t[1:]), vals)
        return vals

    def close(self):
        self._sort(self._dataframe)
        self.commit()


DataFrameStash.dataframe = DataFrameStash._dataframe


@dataclass
class DataclassStash(DataFrameStash):
    """Map CSV rows in :class:`~zensols.datdesc.dfstash.DataFrameStash` stashes
    to Python dataclasses.

    """
    _DICTABLE_ATTRIBUTES = {'metadata'}

    data_name: str = field(default=None)
    """The name used for :obj:`describer`.  If not provided, taken from the
    class name.

    """
    desc: str = field(default=None)
    """The description used in :obj:`describer`.  If not provided, it is taken
    from the class docstring.

    """
    metadata: DataclassMetadata = field(default=None)
    """Get the metadata of dataclass :obj:`data_class`."""

    def __post_init__(self):
        meta: tuple[ClassField, ...] = self.metadata.fields_by_order
        self.columns = tuple(map(lambda m: m.name, meta[1:]))
        super().__post_init__()

    def _set(self, dataframe: pd.DataFrame):
        df: pd.DataFrame = dataframe
        if df.shape[1] > 1 and self.single_column_index is not None:
            raise PersistableError(
                'single_column_index must be None if columns are > 1')
        super()._set(df)
        # convert all NAs to Nones
        df.where(pd.notna(df), None, inplace=True)
        # convert dates for the in-memory instance
        ci: int
        col: ClassField
        for ci, col in enumerate(self.metadata.fields_by_order):
            if issubclass(col.dtype, datetime):
                df[col.name] = pd.to_datetime(df[col.name])
            elif ci > 0 and len(df) > 0 and issubclass(col.dtype, str):
                df[col.name] = df[col.name].apply(
                    lambda s: None if pd.isna(s) else str(s))

    def _object_to_row(self, name: str, obj: Any) -> \
            tuple[str, tuple[Any, ...]]:
        row: tuple[Any, ...] = tuple(
            map(lambda f: getattr(obj, f.name),
                filter(lambda f: f.repr, dataclasses.fields(obj))))
        return row[1:]

    def _row_to_object(self, name: str, row: tuple[Any, ...]) -> Any:
        cls: type = self.metadata.class_type
        return cls(name, *row)

    @staticmethod
    def _to_c_const(name: type | str) -> str:
        if isinstance(name, type):
            name = name.__name__
        return re.sub(
            r'(?<!^)(?=[A-Z][a-z])|(?<=[a-z0-9])(?=[A-Z])',
            '_',
            name,
        ).lower()

    def get_describer(self) -> DataFrameDescriber:
        meta: tuple[tuple[str, str], ...] = tuple(map(
            lambda f: (f.name, f.doc.text), self.metadata.fields_by_order))
        return DataFrameDescriber(
            name=self._to_c_const(self.metadata.class_type),
            desc=None if self.metadata.doc is None else self.metadata.doc.text,
            df=self._dataframe,
            meta=meta)
