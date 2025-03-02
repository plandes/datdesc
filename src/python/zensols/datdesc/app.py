"""Generate LaTeX tables in a .sty file from CSV files.  The paths to the CSV
files to create tables from and their metadata is given as a YAML configuration
file.  Paraemters are both files or both directories.  When using directories,
only files that match *-table.yml are considered.

"""
__author__ = 'Paul Landes'

from typing import Tuple, Iterable, Any, Dict, List
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
import re
from itertools import chain
from pathlib import Path
import pandas as pd
from zensols.util import stdout
from zensols.cli import ApplicationError
from zensols.config import Settings, FactoryError
from .hyperparam import HyperparamModel, HyperparamSet, HyperparamSetLoader
from .latex import CsvToLatexTable
from . import (
    LatexTableError, TableFactory, Table, DataFrameDescriber, DataDescriber
)

logger = logging.getLogger(__name__)


class _OutputFormat(Enum):
    """The output format for hyperparameter data.

    """
    short = auto()
    full = auto()
    json = auto()
    yaml = auto()
    sphinx = auto()
    table = auto()


@dataclass
class Application(object):
    """Generate LaTeX tables files from CSV files and hyperparameter .sty files.

    """
    table_factory: TableFactory = field()
    """Reads the table definitions file and writes a Latex .sty file of the
    generated tables from the CSV data.

    """
    hyperparam_file_regex: re.Pattern = field(
        default=re.compile(r'^.+-hyperparam\.yml$'))
    """Matches file names of tables process in the LaTeX output."""

    hyperparam_table_default: Settings = field(default=None)
    """Default settings for hyperparameter :class:`.Table` instances."""

    data_file_regex: re.Pattern = field(default=re.compile(r'^.+-table\.yml$'))
    """Matches file names of tables process in the LaTeX output."""

    def _process_data_file(self, data_file: Path, output_file: Path):
        tables: Tuple[Table, ...] = \
            tuple(self.table_factory.from_file(data_file))
        if len(tables) == 0:
            raise LatexTableError(f'No tables found: {data_file}')
        package_name: str = tables[0].package_name
        logger.info(f'{data_file} -> {output_file}, pkg={package_name}')
        with stdout(output_file, 'w') as f:
            tab = CsvToLatexTable(tables, package_name)
            tab.write(writer=f)
        logger.info(f'wrote {output_file}')

    def _write_hyper_table(self, hset: HyperparamSet, table_file: Path):
        def map_table(dd: DataFrameDescriber, hp: HyperparamModel) -> Table:
            hmtab: Dict[str, Any] = hp.table
            params: Dict[str, Any] = dict(**table_defs, **hmtab) \
                if hmtab is not None else table_defs
            return dd.create_table(**params)

        table_defs: Dict[str, Any] = self.hyperparam_table_default.asdict()
        tables: Tuple[Table] = tuple(
            map(lambda x: map_table(*x),
                zip(hset.create_describer().describers, hset.models.values())))
        with open(table_file, 'w') as f:
            tab = CsvToLatexTable(tables, table_file.stem)
            tab.write(writer=f)
        logger.info(f'wrote: {table_file}')

    def _process_hyper_file(self, hyper_file: Path, output_file: Path,
                            output_format: _OutputFormat):
        loader = HyperparamSetLoader(hyper_file)
        hset: HyperparamSet = loader.load()
        with stdout(output_file, 'w') as f:
            {_OutputFormat.short: lambda: hset.write(
                writer=f, include_full=False),
             _OutputFormat.full: lambda: hset.write(
                 writer=f, include_full=True),
             _OutputFormat.json: lambda: hset.asjson(
                 writer=f, indent=4),
             _OutputFormat.yaml: lambda: hset.asyaml(writer=f),
             _OutputFormat.sphinx: lambda: hset.write_sphinx(writer=f),
             _OutputFormat.table: lambda: self._write_hyper_table(
                 hset, output_file)
             }[output_format]()

    def _process_file(self, input_file: Path, output_file: Path,
                      file_type: str):
        try:
            if file_type == 'd':
                return self._process_data_file(input_file, output_file)
            else:
                return self._process_hyper_file(
                    input_file, output_file, _OutputFormat.table)
        except FileNotFoundError as e:
            raise ApplicationError(str(e)) from e
        except LatexTableError as e:
            reason: str = str(e)
            c: Exception = e.__cause__
            if isinstance(c, FactoryError):
                table: str = e.table
                table = f"'{table}'" if len(table) > 0 else table
                reason = (
                    f"Can not process table {table} " +
                    f"in {c.config_file}: {c.__cause__} ")
            raise ApplicationError(reason)

    def _get_paths(self, input_path: Path, output_path: Path) -> \
            Iterable[Tuple[str, Path]]:
        if input_path.is_dir() and not output_path.exists():
            output_path.mkdir(parents=True)
        if output_path is not None and \
           ((input_path.is_dir() and not output_path.is_dir()) or
               (not input_path.is_dir() and output_path.is_dir())):
            raise ApplicationError(
                'Both parameters must both be either files or directories, ' +
                f"got: '{input_path}', and '{output_path}'")

        def _map_file_type(path: Path) -> Tuple[str, Path]:
            t: str = None
            if self.data_file_regex.match(path.name) is not None:
                t = 'd'
            elif self.hyperparam_file_regex.match(path.name) is not None:
                t = 'h'
            return (t, path)

        paths: Iterable[str, Path]
        if input_path.is_dir():
            paths = filter(lambda t: t[0] is not None,
                           map(_map_file_type, input_path.iterdir()))
        elif input_path.exists():
            paths = (_map_file_type(input_path),)
        else:
            raise ApplicationError(f'No such file for directory: {input_path}')
        return paths

    def _get_example(self) -> DataFrameDescriber:
        return DataFrameDescriber(
            name='roster',
            desc='Example dataframe using mock roster data.',
            head='Mock Roster',
            df=pd.DataFrame(
                data={'name': ['Stan', 'Kyle', 'Cartman', 'Kenny'],
                      'age': [16, 20, 19, 18]}),
            meta=(('name', 'the person\'s name'),
                  ('age', 'the age of the individual')))

    def show_table(self, name: str = None):
        """Print a list of example LaTeX tables.

        :param name: the name of the example table or a listing of tables if
                     omitted

        """
        if name is None:
            print('\n'.join(self.table_factory.get_table_names()))
        else:
            dfd: DataFrameDescriber = self._get_example()
            table: Table = dfd.create_table(name=name)
            table.write()

    def generate_tables(self, input_path: Path, output_path: Path):
        """Create LaTeX tables.

        :param input_path: definitions YAML path location or directory

        :param output_path: output file or directory

        """
        paths: Iterable[str, Path] = self._get_paths(input_path, output_path)
        file_type: str
        path: Path
        for file_type, path in paths:
            if input_path.is_dir():
                ofile: Path = output_path / f'{path.stem}.sty'
                self._process_file(path, ofile, file_type)
            else:
                self._process_file(input_path, output_path, file_type)

    def generate_hyperparam(self, input_path: Path, output_path: Path,
                            output_format: _OutputFormat = _OutputFormat.short):
        """Write hyperparameter formatted data

        :param input_path: definitions YAML path location or directory

        :param output_path: output file or directory

        :param output_format: output format of the hyperparameter metadata

        """
        paths: Iterable[str, Path] = self._get_paths(input_path, output_path)
        path: Path
        for _, path in filter(lambda x: x[0] == 'h', paths):
            self._process_hyper_file(path, output_path, output_format)

    def write_excel(self, input_path: Path, output_file: Path = None,
                    output_latex_format: bool = False):
        """Create an Excel file from table data.

        :param input_path: definitions YAML path location or directory

        :param output_file: the output file, which defaults to the input prefix
                            with the approproate extension

        :param output_latex_format: whether to output with LaTeX commands

        """
        paths: Tuple[Path] = (input_path,)
        descs: List[DataDescriber] = []
        name: str = input_path.name
        if output_file is None:
            output_file = Path(f'{input_path.stem}.xlsx')
        if input_path.is_dir():
            paths = tuple(filter(lambda p: p.suffix == '.yml',
                                 input_path.iterdir()))
        descs: Tuple[DataDescriber] = tuple(map(
            DataDescriber.from_yaml_file, paths))
        if len(descs) == 1:
            name = descs[0].name
        desc = DataDescriber(
            describers=tuple(chain.from_iterable(
                map(lambda d: d.describers, descs))),
            name=name)
        if output_latex_format:
            desc.format_tables()
        desc.save_excel(output_file)


@dataclass
class PrototypeApplication(object):
    CLI_META = {'is_usage_visible': False}

    app: Application = field()

    def _create_example(self):
        TableFactory.reset_default_instance()
        dfd: DataFrameDescriber = self.app._get_example()
        table: Table = dfd.create_table(type='one_column')
        table.write()

    def _create_write_example(self):
        TableFactory.reset_default_instance()
        dfd: DataFrameDescriber = self.app._get_example()
        table: Table = dfd.create_table(type='one_column')
        ofile = Path('example.yml')
        TableFactory.default_instance().to_file(table, ofile)
        with open(ofile) as f:
            print(f.read().strip())
        #table2 = next(TableFactory.default_instance().from_file(ofile))

    def _from_file_example(self):
        tab_file = Path('test-resources/config/sections-table.yml')
        ofile = Path('example.yml')
        table = next(TableFactory.default_instance().from_file(tab_file))
        TableFactory.default_instance().to_file(table, ofile)
        with open(ofile) as f:
            print(f.read().strip())

    def proto(self):
        """Prototype test."""
        #self._create_example()
        self._create_write_example()
        #self._from_file_example()
