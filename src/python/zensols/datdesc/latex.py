"""Contains the manager classes that invoke the tables to generate.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import Sequence, Set, Iterable, ClassVar
from dataclasses import dataclass, field
import sys
import logging
from itertools import chain
from io import StringIO
from datetime import datetime
from pathlib import Path
from io import TextIOWrapper
import yaml
from zensols.util import Failure
from zensols.config import (
    Writable, Dictable, ConfigFactory, ImportIniConfig, ImportConfigFactory
)
from . import LatexTableError, Table

logger = logging.getLogger(__name__)

_TABLE_FACTORY_CONFIG: str = """
[import]
config_file = resource(zensols.datdesc): resources/obj.yml
"""


@dataclass
class TableFactory(Dictable):
    """Reads the table definitions file and writes a Latex .sty file of the
    generated tables from the CSV data.

    """
    _DEFAULT_INSTANCE: ClassVar[TableFactory] = None
    """The singleton instance when not created from a configuration factory."""

    config_factory: ConfigFactory = field(repr=False)
    """The configuration factory used to create :class:`.Table` instances."""

    @classmethod
    def default_instance(cls: TableFactory) -> TableFactory:
        if cls._DEFAULT_INSTANCE is None:
            config = ImportIniConfig(StringIO(_TABLE_FACTORY_CONFIG))
            fac = ImportConfigFactory(config)
            try:
                cls._DEFAULT_INSTANCE = fac('datdesc_table_factory')
            except Exception as e:
                fail = Failure(
                    exception=e,
                    message='Can not create stand-alone template factory')
                fail.rethrow()
        return cls._DEFAULT_INSTANCE

    def _fix_path(self, tab: Table):
        """When the CSV path in the table doesn't exist, replace it with a
        relative file from the YAML file if it exists.

        """
        tab_path = Path(tab.path)
        if not tab_path.is_file():
            rel_path = Path(tab.definition_file.parent, tab_path).resolve()
            if rel_path.is_file():
                tab.path = rel_path

    def from_file(self, table_path: Path) -> Iterable[Table]:
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'reading table definitions file {table_path}')
        with open(table_path) as f:
            content = f.read()
        tdefs = yaml.load(content, yaml.FullLoader)
        for name, td in tdefs.items():
            table_name: str = td.get('type')
            if table_name is None:
                raise LatexTableError(
                    f"No 'type' given for '{name}' in file '{table_path}'")
            del td['type']
            td['definition_file'] = table_path
            sec: str = f'datdesc_table_{table_name}'
            inst: Table = self.config_factory.new_instance(sec, **td)
            inst.name = name
            self._fix_path(inst)
            yield inst


@dataclass
class CsvToLatexTable(Writable):
    """Generate a Latex table from a CSV file.

    """
    tables: Sequence[Table] = field()
    """A list of table instances to create Latex table definitions."""

    package_name: str = field()
    """The name Latex .sty package."""

    def _write_header(self, depth: int, writer: TextIOWrapper):
        date = datetime.now().strftime('%Y/%m/%d')
        writer.write("""\\NeedsTeXFormat{LaTeX2e}
\\ProvidesPackage{%(package_name)s}[%(date)s Tables]

""" % {'date': date, 'package_name': self.package_name})
        uses: Set[str] = set(chain.from_iterable(
            map(lambda t: t.uses, self.tables)))
        for use in sorted(uses):
            writer.write(f'\\usepackage{{{use}}}\n')

    def write(self, depth: int = 0, writer: TextIOWrapper = sys.stdout):
        """Write the Latex table to the writer given in the initializer.

        """
        self._write_header(depth, writer)
        for table in self.tables:
            table.write(depth, writer)
