"""Classes to create first class object and process files.

"""
from typing import Tuple, Iterable, Any, Dict
from dataclasses import dataclass, field
from enum import Enum, auto
import logging
import re
from pathlib import Path
from zensols.util import stdout
from zensols.cli import ApplicationError
from zensols.config import Settings, FactoryError, Dictable, ConfigFactory
from . import (
    LatexTableError, TableFactory, Table, DataFrameDescriber, DataDescriber
)

logger = logging.getLogger(__name__)


class OutputFormat(Enum):
    """The output format for hyperparameter data.

    """
    short = auto()
    full = auto()
    json = auto()
    yaml = auto()
    sphinx = auto()
    table = auto()


@dataclass
class FileProcessor(Dictable):
    """
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

    # NEED
    def _process_hyper_file(self, hyper_file: Path, output_file: Path,
                            output_format: OutputFormat):
        from .hyperparam import HyperparamSet, HyperparamSetLoader

        loader = HyperparamSetLoader(hyper_file)
        hset: HyperparamSet = loader.load()
        with stdout(output_file, 'w') as f:
            {OutputFormat.short: lambda: hset.write(
                writer=f, include_full=False),
             OutputFormat.full: lambda: hset.write(
                 writer=f, include_full=True),
             OutputFormat.json: lambda: hset.asjson(
                 writer=f, indent=4),
             OutputFormat.yaml: lambda: hset.asyaml(writer=f),
             OutputFormat.sphinx: lambda: hset.write_sphinx(writer=f),
             OutputFormat.table: lambda: self._write_hyper_table(
                 hset, output_file)
             }[output_format]()

    # NEED
    def _process_file(self, input_file: Path, output_file: Path,
                      file_type: str):
        try:
            if file_type == 'd':
                return self._process_data_file(input_file, output_file)
            elif file_type == 's':
                return self._process_serial_file(input_file, output_file)
            elif file_type == 'h':
                return self._process_hyper_file(
                    input_file, output_file, OutputFormat.table)
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

    # NEED
    def _process_figure_file(self, fig_config_file: Path, output_dir: Path,
                             output_image_format: str):
        from .figure import Figure
        fig: Figure
        for fig in self._get_figures(fig_config_file):
            fig.image_dir = output_dir
            if output_image_format is not None:
                fig.image_format = output_image_format
            fig.save()

    # NEED
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
