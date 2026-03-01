from typing import Any
from collections.abc import Iterable
import sys
from io import StringIO
import unittest
from pathlib import Path
from zensols.datdesc import ApplicationFactory
from zensols.datdesc.render import RenderableFactory, Renderable


class TestRenderable(unittest.TestCase):
    def setUp(self):
        self.maxDiff = sys.maxsize
        self.fac: RenderableFactory = \
            ApplicationFactory.get_renderable_factory()
        self.rend_dir = Path('test-resources/renderables')

    def _test_file(self, name: str, rend_type: type, art_type: type):
        path: Path = self.rend_dir / name
        rend_iter: Iterable[Any] = self.fac(path)
        self.assertTrue(isinstance(rend_iter, Iterable))
        rends: tuple[Renderable, ...] = tuple(rend_iter)
        self.assertEqual(1, len(rends))
        self.assertEqual(rend_type, type(rends[0]))
        arts: tuple[Any] = tuple(rends[0])
        self.assertEqual(1, len(arts))
        self.assertEqual(art_type, type(arts[0]))
        return arts[0]

    def test_table(self):
        from zensols.datdesc.latex import LatexTable, RenderableLatexTable
        table: LatexTable = self._test_file(
            'roster-table.yml', RenderableLatexTable, LatexTable)
        self.assertEqual('rosterTab', table.name)
        sio = StringIO()
        table.write(writer=sio)
        self.assertEqual(21, len(sio.getvalue().split('\n')))

    def test_data_describer(self):
        from zensols.datdesc import \
            DataDescriber, DataFrameDescriber, RenderableDataFrameDescriber
        dd: DataDescriber = self._test_file(
            'roster-table.json', RenderableDataFrameDescriber, DataDescriber)
        self.assertEqual('roster', dd.name)
        self.assertEqual(('roster',), tuple(dd.keys()))
        self.assertEqual(DataFrameDescriber, type(dd['roster']))
        self.assertEqual(4, len(dd['roster'].df))
        sio = StringIO()
        dd.write(writer=sio)
        self.assertEqual(13, len(sio.getvalue().split('\n')))

    def test_figure(self):
        from zensols.datdesc.figure import Figure, RenderableFigure
        fig: Figure = self._test_file(
            'roster-figure.yml', RenderableFigure, Figure)
        self.assertEqual('rosterFig', fig.name)

    def test_iterate(self):
        rend_iter: Iterable[Any] = self.fac(self.rend_dir)
        self.assertTrue(isinstance(rend_iter, Iterable))
        rend: Renderable
        for rend in rend_iter:
            self.assertTrue(isinstance(rend, Renderable),
                            f'not a renderable: {rend}')
