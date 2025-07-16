from typing import Iterable
import unittest
import pandas as pd
from zensols.persist import PersistableError
from zensols.datdesc.dfstash import DataFrameStash
from util import TestUtil


class TestBase(TestUtil):
    def test_create(self):
        dfs = self._create_dfs()
        self.assertEqual('key', dfs.key_column)
        self.assertEqual('key', dfs.dataframe.index.name)
        df = dfs.dataframe
        self.assertTrue(isinstance(df, pd.DataFrame))
        self.assertEqual(0, len(df))
        self.assertEqual(0, len(dfs.dataframe))
        self.assertEqual((), tuple(dfs.keys()))
        self.assertEqual((), tuple(dfs.values()))
        self.assertEqual(('value',), tuple(df.columns))
        self.assertEqual('key', df.index.name)
        self._dfs = dfs
        self._assertFile(dfs)

    def test_nascent_append(self):
        dfs = self._create_dfs()
        self.assertEqual('key', dfs.dataframe.index.name)
        self.assertEqual(0, len(dfs))
        dfs.dump('Stan', (16,))
        self.assertFalse(self.dfs_path.exists())
        self.assertEqual('key', dfs.dataframe.index.name)
        self.assertEqual(1, len(dfs))
        self.assertEqual(('Stan',), tuple(dfs.keys()))
        self.assertEqual(((16,),), tuple(dfs.values()))
        self._dfs = dfs
        self._assertFile(dfs)

    def test_append(self):
        df = self._get_example_df()
        df.index.name = 'key'
        dfs = self._create_dfs(dataframe=df)
        self.assertEqual(4, len(df))
        dfs.dump('Mackey', (33, False))
        self.assertFalse(self.dfs_path.exists())
        self.assertEqual(5, len(dfs.dataframe))
        self.assertEqual(('Stan', 'Kyle', 'Cartman', 'Kenny', 'Mackey'),
                         tuple(dfs.keys()))
        self.assertEqual(
            ((16, True), (20, True), (19, False), (18, True), (33, False)),
            tuple(dfs.values()))
        self._dfs = dfs
        self._assertFile(dfs)


class TestDFStashOp(TestBase, unittest.TestCase):
    def _create_dfs(self, **kwargs):
        return super()._create_dfs(auto_commit=False, **kwargs)

    def test_create_with_df(self):
        df = self._get_example_df()
        dfs = self._create_dfs(dataframe=df)
        self.assertEqual(id(df), id(dfs.dataframe))
        self._assertFile(dfs)

    def test_no_modify(self):
        dfs = self._create_dfs()
        with self.assertRaises(PersistableError):
            dfs.dataframe = pd.DataFrame()
        self._assertFile(dfs)

    def test_read(self):
        df = self._get_example_df()
        dfs = self._create_dfs(dataframe=df)
        self.assertEqual(4, len(dfs))
        self.assertEqual(4, len(dfs.dataframe))
        self.assertEqual(('age', 'cool'), tuple(dfs.columns))
        self.assertTrue(isinstance(dfs.keys(), Iterable))
        self.assertEqual(('Stan', 'Kyle', 'Cartman', 'Kenny'),
                         tuple(dfs.keys()))
        self.assertEqual(((16, True), (20, True), (19, False), (18, True)),
                         tuple(dfs.values()))
        self.assertTrue('Stan' in dfs)
        self.assertTrue('nada' not in dfs)
        self._assertFile(dfs)

    def test_bad_append(self):
        df = self._get_example_df()
        dfs = self._create_dfs(dataframe=df)
        self.assertEqual(4, len(df))
        s = r'^Expecting input length \(3\) alignment with columns length \(2\)$'
        with self.assertRaisesRegex(PersistableError, s):
            dfs.dump('Mackey', (33, False, 'nada'))
        self.assertEqual(4, len(df))
        self.assertEqual(4, len(dfs.dataframe))
        self._assertFile(dfs)

    def test_nascent_col_append(self):
        dfs = self._create_dfs(columns=['name', 'is_cool'])
        self.assertEqual(0, len(dfs))
        dfs.dump('Stan', (16, True))
        self.assertFalse(self.dfs_path.exists())
        self.assertEqual(1, len(dfs))
        self.assertEqual(('Stan',), tuple(dfs.keys()))
        self.assertEqual(((16, True),), tuple(dfs.values()))
        self._assertFile(dfs)

    def test_load(self):
        df = self._get_example_df()
        dfs = self._create_dfs(dataframe=df)
        self.assertEqual((16, True), dfs.load('Stan'))
        self.assertEqual((16, True), dfs['Stan'])
        self.assertEqual((16, True), dfs.get('Stan'))
        self.assertEqual(None, dfs.get('nada'))
        self.assertEqual(None, dfs.load('nada'))
        with self.assertRaises(KeyError):
            self.assertEqual(None, dfs['nada'])
        self._assertFile(dfs)

    def test_nascent_remove(self):
        df = self._get_example_df()
        dfs = self._create_dfs(dataframe=df)
        self.assertEqual(4, len(df))
        self.assertTrue('Stan' in dfs)
        dfs.delete('Stan')
        self.assertEqual(3, len(dfs))
        self.assertEqual(3, len(dfs.dataframe))
        self.assertFalse('Stan' in dfs)
        self._assertFile(dfs)

    def test_update(self):
        df = self._get_example_df()
        dfs = self._create_dfs(dataframe=df)
        dfs.dump('Stan', (55, False))
        self.assertFalse(self.dfs_path.exists())
        self.assertEqual(4, len(dfs))
        self.assertEqual(4, len(dfs.dataframe))
        self.assertEqual(('Stan', 'Kyle', 'Cartman', 'Kenny'),
                         tuple(dfs.keys()))
        self.assertEqual(((55, False), (20, True), (19, False), (18, True)),
                         tuple(dfs.values()))
        self._assertFile(dfs)

    def test_clear(self):
        dfs = self._create_dfs(dataframe=self._get_example_df())
        self.assertFalse(self.dfs_path.exists())
        dfs.dump('Makey', (55, False))
        self.assertFalse(self.dfs_path.exists())
        dfs.commit()
        self.assertTrue(self.dfs_path.exists())
        dfs.clear()
        self.assertFalse(self.dfs_path.exists())
        self.assertEqual(0, len(dfs))
        self.assertEqual(0, len(dfs.dataframe))
        self.assertEqual((), tuple(dfs.keys()))
        self.assertEqual((), tuple(dfs.values()))


class TestDFStashCommit(TestBase, unittest.TestCase):
    def _assertFile(self, dfs: DataFrameStash):
        dfs.close()
        self.assertTrue(self.dfs_path.exists())
        self._test_df_equal()

    def test_key_name_change(self):
        col = 'diffkey'
        dfs = self._create_dfs(key_column=col)
        self.assertEqual(col, dfs.key_column)
        self.assertEqual(col, dfs.dataframe.index.name)
        dfs.close()

        dfn = self._create_dfs(key_column=col)
        self.assertEqual(col, dfn.key_column)
        self.assertEqual(col, dfn.dataframe.index.name)

        s = r'^Instance key column \(key\) to be equal to persisted column \(diffkey\)$'
        with self.assertRaisesRegex(PersistableError, s):
            self._create_dfs()


class TestDFStashConfig(TestUtil, unittest.TestCase):
    def test_single_col(self):
        dfs = self._create_dfs(single_column_index=0)
        self.assertEqual('key', dfs.dataframe.index.name)
        self.assertEqual(0, len(dfs))
        dfs.dump('Stan', 16)
        self.assertFalse(self.dfs_path.exists())
        self.assertEqual('key', dfs.dataframe.index.name)
        self.assertEqual(1, len(dfs))
        self.assertEqual(('Stan',), tuple(dfs.keys()))
        self.assertEqual((16,), tuple(dfs.values()))
        self.assertEqual(16, dfs.get('Stan'))
        self._dfs = dfs
        self._assertFile(dfs)
        dfs.close()
        self.assertTrue(self.dfs_path.exists())
        self._test_df_equal()

    def test_auto_commit(self):
        dfs = self._create_dfs(auto_commit=True)
        self.assertEqual('key', dfs.dataframe.index.name)
        self.assertEqual(0, len(dfs))
        dfs.dump('Stan', (16,))
        self.assertTrue(self.dfs_path.exists())
