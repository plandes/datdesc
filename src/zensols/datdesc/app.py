"""Generate LaTeX tables in a .sty file from CSV files.  The paths to the CSV
files to create tables from and their metadata is given as a YAML configuration
file.  Paraemters are both files or both directories.  When using directories,
only files that match *-table.yml are considered.

"""
__author__ = 'Paul Landes'
from typing import Iterable
from dataclasses import dataclass, field
from collections.abc import Callable
import logging
from itertools import chain
from pathlib import Path
from zensols.config import ConfigFactory
from zensols.cli import ApplicationError
from .render import Renderable, RenderableFactory
from . import OutputFormat, Table, DataFrameDescriber, DataDescriber

logger = logging.getLogger(__name__)


@dataclass
class Application(object):
    """Generate LaTeX tables files from CSV files and hyperparameter .sty files.

    """
    config_factory: ConfigFactory = field()
    """Creates table and figure factories."""

    renderable_factory: RenderableFactory = field()
    """Creates instances of :class:`.Renderable` from file paths."""

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

    def _is_one_of(self, rend_type: type[Renderable] | set = None) -> bool:
        def is_in(obj) -> bool:
            return obj.__class__.__name__ in types

        if not isinstance(rend_type, set):
            rend_type = [rend_type]
        types: set[str] = set(map(lambda rt: rt.__name__, rend_type))
        return is_in

    def _get_renderables(self, input_path: Path, output_path: Path,
                         rend_type: type[Renderable] | set = None) -> \
            tuple[Renderable]:
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
        rends: Iterable[Renderable] = self.renderable_factory(input_path)
        if rend_type is not None:
            is_type: Callable = self._is_one_of(rend_type)
            rends = filter(is_type, rends)
        rends = tuple(rends)
        if not input_path.is_dir() and len(rends) == 0:
            raise ApplicationError(f'Unknown file type: {input_path}')
        return rends

    def show_table(self, name: str = None):
        """Print a list of example LaTeX tables.

        :param name: the name of the example table or a listing of tables if
                     omitted

        """
        if name is None:
            print('\n'.join(self.processor.table_factory.get_table_names()))
        else:
            dfd: DataFrameDescriber = self._get_example()
            table: Table = dfd.create_table(type=name)
            table.write()

    def _map_table_out_path(self, input_path: Path, output_path: Path,
                            renderable: Renderable) -> Path:
        rend_out_path: Path = output_path
        if input_path.is_dir():
            rend_out_path = output_path / f'{renderable.path.stem}.sty'
        return rend_out_path

    def generate_tables(self, input_path: Path, output_path: Path,
                        output_format: OutputFormat = OutputFormat.table):
        """Create LaTeX tables.

        :param input_path: YAML definitions or JSON serialized file

        :param output_path: output file or directory

        """
        from .latex import RenderableLatexTable
        from .hyperparam import RenderableHyperparamSet
        from .desc import RenderableDataFrameDescriber
        rts: type[Renderable] = {
            RenderableLatexTable,
            RenderableHyperparamSet,
            RenderableDataFrameDescriber}
        is_hyper: Callable = self._is_one_of(RenderableHyperparamSet)
        renderable: Renderable
        for renderable in self._get_renderables(input_path, output_path, rts):
            rend_out_path: Path = self._map_table_out_path(
                input_path, output_path, renderable)
            if is_hyper(renderable):
                hyper_renderable = self.renderable_factory('hyperparam')
                hyper_renderable.path = renderable.path
                hyper_renderable.write(rend_out_path, output_format)
            else:
                renderable.write(rend_out_path)

    def generate_figures(self, input_path: Path, output_path: Path,
                         output_image_format: str = None):
        """Generate figures.

        :param input_path: YAML definitions or JSON serialized file

        :param output_path: output file or directory

        :param output_image_format: the output format (defaults to ``svg``)

        """
        from .figure import RenderableFigure as RType
        renderable: RType
        for renderable in self._get_renderables(input_path, output_path, RType):
            renderable.write(output_path, image_format=output_image_format)

    def list_figures(self, input_path: Path):
        """List figures.

        :param input_path: YAML definitions or JSON serialized file

        :param output_path: output file or directory

        :param output_image_format: the output format (defaults to ``svg``)

        """
        from .figure import RenderableFigure as RType
        logging.getLogger('zensols.datdesc').setLevel(logging.WARNING)
        renderable: RType
        for renderable in self._get_renderables(input_path, None, RType):
            for fig in renderable.get_figures():
                print(fig.name)

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
            paths: tuple[Path, ...] = (input_path,)
            descs: list[DataDescriber] = []
            name: str = input_path.name
            if output_file is None:
                output_file = Path(f'{input_path.stem}.xlsx')
            if input_path.is_dir():
                paths = tuple(filter(lambda p: p.suffix == '.yml',
                                     input_path.iterdir()))
            descs: tuple[DataDescriber, ...] = tuple(map(
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
