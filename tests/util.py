from pathlib import Path
import shutil
import pandas as pd
from zensols.datdesc.dfstash import DataFrameStash
from zensols.datdesc import DataFrameDescriber


class TestUtil(object):
    DEBUG: bool = False

    def setUp(self):
        targ = Path('target')
        self.dfs_path = targ / 'dfs.csv'
        if targ.is_dir():
            shutil.rmtree(targ)
        if self.DEBUG:
            print()
            print('_' * 80)

    def _get_example_df(self) -> pd.DataFrame:
        return pd.DataFrame(
            data={'age': [16, 20, 19, 18],
                  'cool': [True, True, False, True]},
            index=['Stan', 'Kyle', 'Cartman', 'Kenny'])

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

    def _create_dfs(self, **kwargs):
        if 'single_column_index' not in kwargs:
            kwargs['single_column_index'] = None
        if 'auto_commit' not in kwargs:
            kwargs['auto_commit'] = False
        return DataFrameStash(path=self.dfs_path, **kwargs)

    def _assertFile(self, dfs: DataFrameStash):
        self.assertFalse(self.dfs_path.exists())

    def _test_df_equal(self):
        # df from test just ran
        dfi = self._dfs
        self.assertEqual('key', dfi.key_column)
        self.assertEqual('key', dfi.dataframe.index.name)

        # restored from file system
        dfs = self._create_dfs()
        self.assertEqual('key', dfs.key_column)
        self.assertEqual('key', dfs.dataframe.index.name)

        self.assertEqual(dfi.dataframe.astype(str).to_string(),
                         dfs.dataframe.astype(str).to_string())
