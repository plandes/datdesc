import unittest
from pathlib import Path
import shutil
import pandas as pd
from zensols.config import ImportYamlConfig, ImportConfigFactory
from zensols.datdesc.plots import BarPlot


class TestPlot(unittest.TestCase):
    def setUp(self):
        target = Path('target')
        if target.is_dir():
            shutil.rmtree(target)

    def test_bar(self):
        fac = ImportConfigFactory(ImportYamlConfig('test-resources/fig/bar-plot.yml'))
        fig = fac('note_event_figure')
        df: pd.DataFrame = pd.read_csv('test-resources/fig/iris.csv')
        df = df['species ds_type'.split()]
        df = df.groupby('ds_type').agg({'ds_type': 'count'}).\
            rename(columns={'ds_type': 'count'}).reset_index()
        fig.add_plot(BarPlot(
            data=df,
            x_column_name='ds_type',
            y_column_name='count'))
        path: Path = fig.save()
        self.assertTrue(path.is_file())
        self.assertEqual(path.suffix, '.svg')
