"""Generate LaTeX tables in a .sty file from CSV files.  The paths to the CSV
files to create tables from and their metadata is given as a YAML configuration
file.  Paraemters are both files or both directories.  When using directories,
only files that match *-table.yml are considered.

"""
__author__ = 'Paul Landes'
from typing import Iterable
from dataclasses import dataclass, field
import logging
from itertools import chain
from pathlib import Path
from zensols.config import ConfigFactory
from . import Table, DataFrameDescriber, DataDescriber
from .process import OutputFormat, FileProcessor

logger = logging.getLogger(__name__)


@dataclass
class Application(object):
    """Generate LaTeX tables files from CSV files and hyperparameter .sty files.

    """
    config_factory: ConfigFactory = field()
    """Creates table and figure factories."""

    processor: FileProcessor = field()
    """The name of the file processor config object."""

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
            print('\n'.join(self.processor.table_factory.get_table_names()))
        else:
            dfd: DataFrameDescriber = self._get_example()
            table: Table = dfd.create_table(type=name)
            table.write()

    def _get_paths(self, input_path: Path, output_path: Path) -> \
            Iterable[tuple[str, Path]]:
        return self.processor._get_paths(input_path, output_path)

    def generate_tables(self, input_path: Path, output_path: Path):
        """Create LaTeX tables.

        :param input_path: YAML definitions or JSON serialized file

        :param output_path: output file or directory

        """
        paths: Iterable[str, Path] = self._get_paths(input_path, output_path)
        table_types: set[str] = {'h', 'd', 's'}
        file_type: str
        path: Path
        for file_type, path in filter(lambda x: x[0] in table_types, paths):
            if input_path.is_dir():
                ofile: Path = output_path / f'{path.stem}.sty'
                self.processor._process_file(path, ofile, file_type)
            else:
                self.processor._process_file(input_path, output_path, file_type)

    def generate_hyperparam(self, input_path: Path, output_path: Path,
                            output_format: OutputFormat = OutputFormat.short):
        """Write hyperparameter formatted data.

        :param input_path: YAML definitions or JSON serialized file

        :param output_path: output file or directory

        :param output_format: output format of the hyperparameter metadata

        """
        paths: Iterable[str, Path] = self._get_paths(input_path, output_path)
        path: Path
        for _, path in filter(lambda x: x[0] == 'h', paths):
            self.processor._process_hyper_file(path, output_path, output_format)

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
            self.processor._process_figure_file(path, output_path, output_image_format)

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
