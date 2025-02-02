"""A stash implementation that uses a Pandas dataframe and stored as a CSV file.

"""
__author__ = 'Paul Landes'

from typing import Tuple, Iterable, Any, Union, Optional
from dataclasses import dataclass, field
import logging
from pathlib import Path
import pandas as pd
from zensols.persist import PersistableError, CloseableStash

logger = logging.getLogger(__name__)


@dataclass
class DataFrameStash(CloseableStash):
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
    """The spreadsheet column name used to store stash keeys."""

    columns: Tuple[str, ...] = field(default=('value',))
    """The columns to create in the spreadsheet.  These must be consistent when
    the data is restored.

    """
    mkdirs: bool = field(default=True)
    """Whether to recusively create the directory where :obj:`path` is stored if
    it does not already exist.

    """
    auto_commit: bool = field(default=True)
    """Whether to save to the file system after any modification."""

    single_column_index: Optional[int] = field(default=0)
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

    def _set(self, dataframe: pd.DataFrame):
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

    def load(self, name: str) -> Union[Any, Tuple[Any, ...]]:
        if self.exists(name):
            df: pd.DataFrame = self._dataframe_val
            ret = tuple(df.loc[[name]].itertuples(index=False, name=None))[0]
            if self.single_column_index is not None:
                ret = ret[self.single_column_index]
            return ret

    def get(self, name: str, default: Any = None) -> \
            Union[Any, Tuple[Any, ...]]:
        if self.exists(name):
            item = self.load(name)
        else:
            item = default
        return item

    def exists(self, name: str) -> bool:
        return name in self._dataframe_val.index

    def dump(self, name: str, inst: Union[Any, Tuple[Any, ...]]):
        if self.single_column_index is not None:
            inst = (inst,)
        if self.exists(name):
            self._dataframe_val.loc[name] = inst
        else:
            self._append(name, inst)
        if self.auto_commit:
            self.commit()

    def _append(self, name: str, inst: Tuple[Any, ...]):
        if not isinstance(inst, (tuple, list)):
            raise PersistableError(
                f'Expecting a tuple or list instance by got {type(inst)}')
        df = self._dataframe_val
        if len(inst) != len(df.columns):
            raise PersistableError(
                f'Expecting input length ({len(inst)}) ' +
                f'alignment with columns length ({len(df.columns)})')
        row = pd.DataFrame([inst], columns=df.columns)
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

    def values(self) -> Iterable[Union[Any, Tuple[Any, ...]]]:
        vals = self.dataframe.itertuples(index=False, name=None)
        if self.single_column_index is not None:
            vals = map(lambda v: v[self.single_column_index], vals)
        return vals

    def close(self):
        self.commit()


DataFrameStash.dataframe = DataFrameStash._dataframe
