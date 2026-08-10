from dataclasses import dataclass, field
import unittest
from io import StringIO
from zensols.config import Dictable
from zensols.dataclasses.inspect import DataclassMetadata
from zensols.datdesc import DataFrameDescriber
from util import TestUtil


@dataclass
class MaybeCoolPerson(Dictable):
    """Represents a human.

    """
    name: str = field()
    """The person's name."""

    age: int = field()
    """The age of the person in years."""

    cool: bool = field()
    """Whether or this person is kewl."""


class TestDataclassDatdescMerge(TestUtil, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.data = (MaybeCoolPerson('Stan', 16, True),
                     MaybeCoolPerson('Cartman', 19, False))

    def _assert_all_col(self, dfd: DataFrameDescriber):
        should = """\
maybe-cool-person (Represents a human.)
name       age  cool
-------  -----  ------
Stan        16  True
Cartman     19  False\n"""
        sio = StringIO()
        dfd.write_pretty(writer=sio)
        self.assertEqual(should, sio.getvalue())

        should = """\
name: maybe-cool-person
desc: Represents a human.
dataframe:
          name  age   cool
    0     Stan   16   True
    1  Cartman   19  False
columns:
    age: The age of the person in years.
    cool: Whether or this person is kewl.
    name: The person's name.\n"""
        sio = StringIO()
        dfd.write(writer=sio)
        self.assertEqual(should, sio.getvalue())

    def _assert_column_subset(self, dfd: DataFrameDescriber):
        should = """\
maybe-cool-person (Represents a human.)
name       age
-------  -----
Stan        16
Cartman     19\n"""
        sio = StringIO()
        dfd.write_pretty(writer=sio)
        self.assertEqual(should, sio.getvalue())

        should = """\
name: maybe-cool-person
desc: Represents a human.
dataframe:
          name  age
    0     Stan   16
    1  Cartman   19
columns:
    age: The age of the person in years.
    name: The person's name.\n"""
        sio = StringIO()
        dfd.write(writer=sio)
        self.assertEqual(should, sio.getvalue())

    def test_create_from_meta(self):
        meta = DataclassMetadata(MaybeCoolPerson)
        dfd = DataFrameDescriber.from_dataclasses(self.data, meta)
        self._assert_all_col(dfd)

    def test_create_from_no_meta(self):
        dfd = DataFrameDescriber.from_dataclasses(self.data)
        self._assert_all_col(dfd)

    def test_create_column_subset(self):
        dfd = DataFrameDescriber.from_dataclasses(
            self.data,
            field_names='name age'.split())
        self._assert_column_subset(dfd)

    def test_merge(self):
        dfd1 = DataFrameDescriber.from_dataclasses(
            self.data,
            field_names='name age'.split())
        dfd2 = DataFrameDescriber.from_dataclasses(
            self.data,
            field_names=['cool'])
        dfd = dfd1.merge((dfd2,))
        self._assert_all_col(dfd)
