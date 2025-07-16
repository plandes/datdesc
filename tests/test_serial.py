import unittest
from io import StringIO
from util import TestUtil
import pandas as pd
from zensols.datdesc import DataFrameDescriber, DataDescriber


class TestSerialization(TestUtil, unittest.TestCase):
    def _equal_df(self, a: pd.DataFrame, b: pd.DataFrame):
        return self.assertTrue(a.equals(b))

    def _equal_dfd(self, a: DataFrameDescriber, b: DataFrameDescriber):
        for attr in 'name desc head meta_path table_kwargs index_meta mangle_file_names'.split():
            self.assertEqual(getattr(a, attr), getattr(b, attr))
        self._equal_df(a.df, b.df)
        self._equal_df(a.meta, b.meta)

    def test_desc(self):
        dfd: DataDescriber = self._get_example()
        dda = DataDescriber.from_describer(dfd)
        sio = StringIO()
        dda.to_json(sio)
        sio.seek(0)
        ddb: DataDescriber = DataDescriber.from_json(sio)
        self.assertEqual(1, len(ddb.describers))
        self._equal_dfd(dfd, ddb.describers[0])
        self.assertEqual(dda.name, ddb.name)
        self.assertEqual(dda.mangle_sheet_name, ddb.mangle_sheet_name)
