from typing import Tuple, Iterable, Any, Dict, List, Set
from dataclasses import dataclass, field
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
from .process import OutputFormat, FileProcessor
from .app import Application


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
        dfd.write()
        dd.save_excel(Path('/d'))
        #dd.save()

    def _create_write_json_example(self):
        TableFactory.reset_default_instance()
        dfd: DataFrameDescriber = self.app._get_example()
        dd = DataDescriber.from_describer(dfd)
        with open('dd-table.json', 'w') as f:
            dd.to_json(f)

    def _restore_bar_figure_example(self):
        from .figure import FigureFactory, Figure
        FigureFactory.reset_default_instance()
        fig_file = Path('test-resources/fig/iris-bar-figure.yml')
        fac = FigureFactory.default_instance()
        fig: Figure = next(fac.from_file(fig_file))
        fig.image_file_norm = False
        fig.save()

    def _create_figure_example(self, name: str):
        from .figure import FigureFactory, Figure
        fig_file = Path(f'test-resources/fig/iris-{name}-figure.yml')
        fac = FigureFactory.default_instance()
        fig: Figure = next(fac.from_file(fig_file))
        fig.image_file_norm = False
        fig.save()

    def proto(self):
        """Prototype test."""
        self._create_save_example()
