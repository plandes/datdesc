from dataclasses import dataclass, field
import dataclasses
import unittest
from pathlib import Path
from zensols.config import Dictable
from zensols.dataclasses.inspect import DataclassMetadata
from zensols.datdesc.dfstash import DataclassStash, PersistableError
from util import TestUtil


@dataclass
class Person(Dictable):
    """Represents a human.

    """
    name: str = field()
    """The person's name."""

    age: int = field()
    """The age of the person in years."""

    cool: bool = field()
    """Whether or this person is kewl."""


class TestDataclassStash(TestUtil, unittest.TestCase):
    def _create_dcs(self):
        df = self._get_example_df()
        dcs = self._create_dfs(
            dataframe=df,
            test_class=DataclassStash,
            metadata=DataclassMetadata(Person))
        return dcs

    def _create_nascent(self, path: Path):
        return DataclassStash(
            path=path,
            metadata=DataclassMetadata(Person),
            auto_commit=False,
            single_column_index=None)

    def test_read(self):
        dcs = self._create_dcs()
        should = Person('Stan', 16, True)
        stan = next(iter(dcs.values()))
        self.assertEqual(should, stan)
        self.assertEqual(4, len(dcs))
        self.assertTrue('Stan' in dcs)
        self.assertTrue('nada' not in dcs)

        should = Person('Cartman', 19, False)
        cartman = dcs[should.name]
        self.assertEqual(should, cartman)

    def test_nascent_write(self):
        path = Path('target/nascent.csv')
        self.assertFalse(path.is_file())
        dcs = self._create_nascent(path)
        self.assertEqual(0, len(dcs))
        should = Person('Cartman', 19, False)
        dcs.dump(should.name, should)
        self.assertEqual(1, len(dcs))
        should = dataclasses.replace(should)
        self.assertEqual(should, dcs['Cartman'])

        self.assertFalse(path.is_file())
        dcs.commit()

        should_csv = """\
key,age,cool
Cartman,19,False
"""
        self.assertTrue(path.is_file())
        self.assertEqual(should_csv, path.read_text())
        dcs = self._create_nascent(path)
        self.assertEqual(should, dcs['Cartman'])

    def test_fail_index_col(self):
        path = Path('target/nascent.csv')
        with self.assertRaisesRegex(PersistableError, r'^single_column_index'):
            DataclassStash(
                dataframe=self._get_example_df(),
                path=path,
                metadata=DataclassMetadata(Person),
                auto_commit=False,
                single_column_index=0)

    def test_dfd(self):
        dcs = self._create_dcs()
        dfd = dcs.get_describer()
        self.assertEqual('person', dfd.name)
        self.assertEqual('Represents a human.', dfd.desc)
        should = """\
                          description
name               The person's name.
age   The age of the person in years.
cool  Whether or this person is kewl."""
        self.assertEqual(should, str(dfd.meta))
