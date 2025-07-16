"""Generate LaTeX tables in a .sty file from CSV files.  The paths to the CSV
files to create tables from and their metadata is given as a YAML configuration
file.  Paraemters are both files or both directories.  When using directories,
only files that match *-table.yml are considered.

"""
__author__ = 'Paul Landes'

from typing import Tuple, Iterable, Any, Dict, List, Set
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
import re
from itertools import chain
from pathlib import Path
from zensols.util import stdout
from zensols.cli import ApplicationError
from zensols.config import Settings, FactoryError, ConfigFactory
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
    config_factory: ConfigFactory = field()
    """Creates table and figure factories."""

    table_factory_name: str = field()
    """The section name of the table factory (see :obj:`table_factory`)."""

    figure_factory_name: str = field()
    """The section name of the figure factory (see :obj:`figure_factory`)."""

    data_file_regex: re.Pattern = field(
        default=re.compile(r'^.+-table\.yml$'))
    """Matches file names of table definitions."""

    serial_file_regex: re.Pattern = field(
        default=re.compile(r'^.+-table\.json$'))
    """Matches file names of serialized dataframe."""

    figure_file_regex: re.Pattern = field(
        default=re.compile(r'^.+-figure\.yml$'))
    """Matches file names of figure definitions."""

    hyperparam_file_regex: re.Pattern = field(
        default=re.compile(r'^.+-hyperparam\.yml$'))
    """Matches file names of tables process in the LaTeX output."""

    hyperparam_table_default: Settings = field(default=None)
    """Default settings for hyperparameter :class:`.Table` instances."""

    @property
    def table_factory(self) -> 'TableFactory':
        """Reads the table definitions file and writes a Latex .sty file of the
        generated tables from the CSV data.

        """
        return self.config_factory(self.table_factory_name)

    @property
    def figure_factory(self) -> 'FigureFactory':
        """Reads the figure definitions file and writes ``eps`` figures..

        """
        return self.config_factory(self.figure_factory_name)

    def _process_data_file(self, data_file: Path, output_file: Path):
        from .latex import CsvToLatexTable

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

    def _process_serial_file(self, data_file: Path, output_file: Path):
        with open(data_file) as f:
            dd: DataDescriber = DataDescriber.from_json(f)
        dd.save(
            csv_dir=output_file / DataDescriber.DEFAULT_CSV_DIR,
            yaml_dir=output_file / DataDescriber.DEFAULT_YAML_DIR,
            excel_path=output_file / DataDescriber.DEFAULT_EXCEL_DIR / dd.name)

    def _write_hyper_table(self, hset: 'HyperparamSet', table_file: Path):
        from .hyperparam import HyperparamModel
        from .latex import CsvToLatexTable

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
        from .hyperparam import HyperparamSet, HyperparamSetLoader

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
            elif file_type == 's':
                return self._process_serial_file(input_file, output_file)
            elif file_type == 'h':
                return self._process_hyper_file(
                    input_file, output_file, _OutputFormat.table)
            else:
                raise ValueError(f'Unknown file type: {file_type}')
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

    def _get_figures(self, fig_config_file: Path) -> Iterable['Figure']:
        from .figure import FigureFactory, Figure
        fac: FigureFactory = self.figure_factory
        fig: Figure
        for fig in fac.from_file(fig_config_file):
            fig.image_file_norm = False
            yield fig

    def _process_figure_file(self, fig_config_file: Path, output_dir: Path,
                             output_image_format: str):
        from .figure import Figure
        fig: Figure
        for fig in self._get_figures(fig_config_file):
            fig.image_dir = output_dir
            if output_image_format is not None:
                fig.image_format = output_image_format
            fig.save()

    def _get_paths(self, input_path: Path, output_path: Path) -> \
            Iterable[Tuple[str, Path]]:
        if input_path.is_dir() and \
           output_path is not None and \
           not output_path.exists():
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
            elif self.figure_file_regex.match(path.name) is not None:
                t = 'f'
            elif self.serial_file_regex.match(path.name) is not None:
                t = 's'
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
        import pandas as pd
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

        :param input_path: YAML definitions or JSON serialized file

        :param output_path: output file or directory

        """
        paths: Iterable[str, Path] = self._get_paths(input_path, output_path)
        table_types: Set[str] = {'h', 'd', 's'}
        file_type: str
        path: Path
        for file_type, path in filter(lambda x: x[0] in table_types, paths):
            if input_path.is_dir():
                ofile: Path = output_path / f'{path.stem}.sty'
                self._process_file(path, ofile, file_type)
            else:
                self._process_file(input_path, output_path, file_type)

    def generate_hyperparam(self, input_path: Path, output_path: Path,
                            output_format: _OutputFormat = _OutputFormat.short):
        """Write hyperparameter formatted data.

        :param input_path: YAML definitions or JSON serialized file

        :param output_path: output file or directory

        :param output_format: output format of the hyperparameter metadata

        """
        paths: Iterable[str, Path] = self._get_paths(input_path, output_path)
        path: Path
        for _, path in filter(lambda x: x[0] == 'h', paths):
            self._process_hyper_file(path, output_path, output_format)

    def generate_figures(self, input_path: Path, output_path: Path,
                         output_image_format: str = None):
        """Generate figures.

        :param input_path: YAML definitions or JSON serialized file

        :param output_path: output file or directory

        :param output_image_format: the output format (defaults to ``svg``)

        """
        paths: Iterable[str, Path] = self._get_paths(input_path, output_path)
        path: Path
        for _, path in filter(lambda x: x[0] == 'f', paths):
            self._process_figure_file(path, output_path, output_image_format)

    def list_figures(self, input_path: Path):
        """Generate figures.

        :param input_path: YAML definitions or JSON serialized file

        :param output_path: output file or directory

        :param output_image_format: the output format (defaults to ``svg``)

        """
        from .figure import Figure
        logging.getLogger('zensols.datdesc').setLevel(logging.WARNING)
        paths: Iterable[str, Path] = self._get_paths(input_path, None)
        path: Path
        for _, path in filter(lambda x: x[0] == 'f', paths):
            fig: Figure
            for fig in self._get_figures(path):
                path: Path = fig.path
                print(path.stem)

    def write_excel(self, input_path: Path, output_file: Path = None,
                    output_latex_format: bool = False):
        """Create an Excel file from table data.

        :param input_path: YAML definitions or JSON serialized file

        :param output_file: the output file, which defaults to the input prefix
                            with the approproate extension

        :param output_latex_format: whether to output with LaTeX commands

        """
        if input_path.is_file() and \
           self.serial_file_regex.match(input_path.name):
            with open(input_path) as f:
                desc = DataDescriber.from_json(f)
            if output_file is None:
                output_file = Path(desc.name)
        else:
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

    def _create_save_example(self):
        TableFactory.reset_default_instance()
        dfd: DataFrameDescriber = self.app._get_example()
        dd = DataDescriber.from_describer(dfd)
        dd.save()

    def _create_write_json_example(self):
        TableFactory.reset_default_instance()
        dfd: DataFrameDescriber = self.app._get_example()
        dd = DataDescriber.from_describer(dfd)
        with open('dd-table.json', 'w') as f:
            dd.to_json(f)

    def _create_figure_example(self):
        from .figure import FigureFactory, Figure
        FigureFactory.reset_default_instance()
        fig_file = Path('test-resources/fig/iris-figure.yml')
        fac = FigureFactory.default_instance()
        fig: Figure = next(fac.from_file(fig_file))
        fig.image_file_norm = False
        #fig.write()
        #print(type(fig.image_dir))
        fig.save()

    def proto(self):
        """Prototype test."""
        #self._create_example()
        #self._create_write_example()
        #self._from_file_example()
        #self._create_save_example()
        #self._create_write_json_example()
        #self.app.generate_tables(Path('dd-table.json'), Path('target'))
        #self.app.list_figures(Path('test-resources/fig'))
        #self._create_figure_example()
        self.app.write_excel(Path('dd-table.json'))
