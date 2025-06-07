import sys
import logging
import unittest
from io import StringIO
from pathlib import Path
import copy
from zensols.datdesc.hyperparam import (
    HyperparamError, HyperparamValueError,
    Hyperparam, HyperparamModel, HyperparamSet, HyperparamSetLoader
)

logger = logging.getLogger(__name__)


class TestHyperparam(unittest.TestCase):
    def setUp(self):
        self.maxDiff = sys.maxsize
        self.happy_path = Path('test-resources/hyperparam/svm-hyperparam.yml')

    def test_equal(self):
        h1 = Hyperparam('C', 'float', 'somedoc')
        h2 = Hyperparam('C', 'float', 'somedoc')

        self.assertTrue(h1 is not h2)
        self.assertEqual(h1, h2)

        h3 = Hyperparam('C', 'int', 'somedoc')
        self.assertNotEqual(h1, h3)
        self.assertNotEqual(h2, h3)

        h4 = Hyperparam('C', 'int', 'somedoc', value=2)
        self.assertNotEqual(h1, h4)

        h5 = Hyperparam('C', 'int', 'somedoc', value=2)
        self.assertEqual(h4, h5)

        h6 = Hyperparam('C2', 'int', 'somedoc', value=2)
        self.assertNotEqual(h5, h6)

    def test_load(self):
        loader = HyperparamSetLoader(self.happy_path)
        hset: HyperparamSet = loader.load()
        self.assertEqual(HyperparamSet, type(hset))
        self.assertEqual(2, len(hset))
        self.assertEqual('float', hset['svm']['C'].type)
        self.assertEqual(None, hset['svm']['C'].value)
        self.assertEqual(str, hset['svm']['kernel'].cls)
        self.assertEqual(float, hset['svm']['C'].cls)
        self.assertEqual(float, hset['svm']['C'].cls)

        self.assertEqual('k_means', hset['k_means'].name)
        self.assertEqual('k-means', hset['k_means'].desc)
        self.assertEqual('bool', hset['k_means']['copy_x'].type)
        self.assertEqual(bool, hset['k_means']['copy_x'].cls)
        self.assertEqual(True, hset['k_means']['copy_x'].value)
        self.assertEqual('list', hset['k_means']['strata'].type)
        self.assertEqual(list, hset['k_means']['strata'].cls)
        self.assertEqual(list, type(hset['k_means'].strata))
        self.assertEqual([1, 2], hset['k_means'].strata)
        self.assertEqual({'learning_rate': 0.01, 'epochs': 3},
                         hset['k_means'].kwargs)

    def test_attr_get(self):
        loader = HyperparamSetLoader(self.happy_path)
        hset: HyperparamSet = loader.load()
        self.assertTrue('svm' in hset)
        self.assertEqual(HyperparamModel, type(hset.svm))
        self.assertEqual('float', hset.svm['C'].type)

        h1: Hyperparam = hset.svm['C']
        self.assertEqual(Hyperparam, type(h1))

        h1.value = 2.
        self.assertEqual(2., h1.value)
        self.assertEqual(2., hset.svm['C'].value)
        self.assertEqual(2., hset.svm.C)

        self.assertEqual(1, hset.k_means.strata[0])
        self.assertEqual(2, hset.k_means.strata[1])
        with self.assertRaises(IndexError):
            self.assertEqual(2, hset.k_means.strata[2])

        hset.k_means.strata[0] = 5
        self.assertEqual(5, hset.k_means.strata[0])

        hset.k_means.strata = [6, 7, 8]
        self.assertEqual(6, hset.k_means.strata[0])
        self.assertEqual(7, hset.k_means.strata[1])
        self.assertEqual(8, hset.k_means.strata[2])

        self.assertEqual(0.01, hset.k_means.kwargs['learning_rate'])
        hset.k_means.kwargs['more'] = 10
        self.assertEqual(10, hset.k_means.kwargs['more'])

        hset.k_means.kwargs = {'animal': 'cat'}
        self.assertEqual({'animal': 'cat'}, hset.k_means.kwargs)

    def test_attr_set(self):
        loader = HyperparamSetLoader(self.happy_path)
        hset: HyperparamSet = loader.load()
        hmodel: HyperparamModel = hset.svm
        hmodel.C = 3.

        self.assertEqual(Hyperparam, type(hmodel['C']))
        self.assertEqual(float, type(hmodel.C))
        self.assertEqual(3, hmodel.C)
        self.assertEqual(3, hmodel['C'].value)

        with self.assertRaisesRegex(
                HyperparamValueError, r"^Wrong type 'int', expecting 'float' for hyperparameter 'C'$"):
            hmodel.C = 3

        hmodel.C = None
        self.assertEqual(None, hmodel.kernel)

        hmodel.kernel = 'linear'
        self.assertEqual('linear', hmodel.kernel)

        with self.assertRaisesRegex(
                HyperparamValueError, r"^Wrong type 'int', expecting 'str' for hyperparameter 'kernel'$"):
            hmodel.kernel = 3

        with self.assertRaisesRegex(
                HyperparamValueError,
                r"Unknown choice 'nada', expecting one of: 'radial', 'linear'$"):
            hmodel.kernel = 'nada'

        self.assertEqual(20, hmodel.max_iter)

        hmodel.max_iter = 1
        with self.assertRaisesRegex(
                HyperparamValueError,
                r"^Out of range value '0' not in \[1, 30\]$"):
            hmodel.max_iter = 0

        hmodel.max_iter = 29
        with self.assertRaisesRegex(
                HyperparamValueError,
                r"^Out of range value '31' not in \[1, 30\]$"):
            hmodel.max_iter = 31

    def test_obj_set(self):
        hset1: HyperparamSet = HyperparamSetLoader(self.happy_path).load()
        hset2: HyperparamSet = HyperparamSetLoader(self.happy_path).load()
        hm1: HyperparamModel = hset1.svm
        hm2: HyperparamModel = hset2.svm

        self.assertEqual(hm1, hm2)
        should = {'C': None,
                  'kernel': None,
                  'max_iter': 20}
        self.assertEqual(should, hm1.flatten())
        should2 = copy.deepcopy(should)
        should2['C'] = 123.

        self.assertNotEqual(should2, hm1.flatten())
        hm1.update(should2)
        self.assertEqual(should2, hm1.flatten())
        self.assertNotEqual(should, hm1.flatten())
        self.assertNotEqual(hm1, hm2)

        hm2.update(hm1)
        self.assertEqual(should2, hm1.flatten())

        hset1: HyperparamSet = HyperparamSetLoader(self.happy_path).load()
        hset2: HyperparamSet = HyperparamSetLoader(self.happy_path).load()

        self.assertEqual(hset1, hset2)
        should = {'k_means.copy_x': True,
                  'k_means.kwargs': {'epochs': 3, 'learning_rate': 0.01},
                  'k_means.n_clusters': None,
                  'k_means.strata': [1, 2],
                  'svm.C': None,
                  'svm.kernel': None,
                  'svm.max_iter': 20}
        self.assertEqual(should, hset1.flatten())
        should2 = copy.deepcopy(should)
        should2['svm.C'] = 123.
        self.assertNotEqual(should2, hset1.flatten())
        hset1.update(should2)
        self.assertEqual(should2, hset1.flatten())
        self.assertNotEqual(should, hset1.flatten())
        self.assertNotEqual(hset1, hset2)

        hset2.update(hset1)
        self.assertEqual(should2, hset1.flatten())

    def test_bad_name(self):
        loader = HyperparamSetLoader(
            Path('test-resources/hyperparam/bad-name.yml'))
        with self.assertRaisesRegex(
                HyperparamError, r'^Illegal name.*kernel\(\)$'):
            loader.load()

    def test_bad_value(self):
        loader = HyperparamSetLoader(
            Path('test-resources/hyperparam/bad-value.yml'))
        with self.assertRaisesRegex(
                HyperparamValueError, r"^Wrong type 'int', expecting 'str' for hyperparameter 'kernel'$"):
            loader.load()

    def test_attr_get_list(self):
        loader = HyperparamSetLoader(self.happy_path)
        hset: HyperparamSet = loader.load()
        self.assertEqual(HyperparamModel, type(hset('svm')))
        h: Hyperparam = hset('svm.max_iter')
        self.assertEqual(20, h)

        self.assertEqual(HyperparamModel, type(hset('svm.node()')))
        self.assertEqual(Hyperparam, type(hset('svm.max_iter.node()')))

        self.assertEqual(1, hset('k_means.strata.0'))
        self.assertEqual(2, hset('k_means.strata.1'))

        with self.assertRaisesRegex(
                HyperparamError, r"^List indices.+not 'nada'$"):
            hset('k_means.strata.nada')

        with self.assertRaisesRegex(
                HyperparamError, r"^Trying to index 'int'.+path: \['1'\]$"):
            hset('svm.max_iter.1')

        with self.assertRaisesRegex(
                HyperparamError, r"^List indices must be integers, not 'k'$"):
            self.assertEqual(2, hset("k_means.strata.k"))

        self.assertEqual(0.01, hset('k_means.kwargs.learning_rate'))

        with self.assertRaises(KeyError):
            hset('k_means.kwargs.nada')

    def test_update(self):
        loader = HyperparamSetLoader(self.happy_path)
        hset: HyperparamSet = loader.load()
        should = """\
models:
    svm:
        C: (float)
        kernel: (str <radial|linear>)
        max_iter: 20 (int) in [1, 30]
    k-means:
        copy_x: True (bool)
        kwargs
            epochs: 3
            learning_rate: 0.01
        n_clusters: (int)
        strata: [1, 2] (list)\n"""
        sio = StringIO()
        hset.write(writer=sio)
        self.assertEqual(should, sio.getvalue())

        hset.svm.update({'C': 123.})
        self.assertEqual(123., hset.svm.C)

        hset.update({'svm.C': 456.})
        self.assertEqual(456., hset.svm.C)

        hset.update({
            'svm.C': 789.,
            'svm.kernel': 'linear',
            'svm.max_iter': 25,
            'k_means.copy_x': False,
            'k_means.kwargs.epochs': 4,
            'k_means.n_clusters': 5,
            'k_means.strata.0': 8,
            'k_means.strata.1': 9,
        })
        should = """\
models:
    svm:
        C: 789.0 (float)
        kernel: linear (str <radial|linear>)
        max_iter: 25 (int) in [1, 30]
    k-means:
        copy_x: False (bool)
        kwargs
            epochs: 4
            learning_rate: 0.01
        n_clusters: 5 (int)
        strata: [8, 9] (list)\n"""
        sio = StringIO()
        hset.write(writer=sio)
        #print('\n' + sio.getvalue())
        self.assertEqual(should, sio.getvalue())
