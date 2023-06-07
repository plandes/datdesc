from dataclasses import dataclass, field
import sys
import logging
import unittest
from zensols.config import Settings, YamlConfig, ImportConfigFactory
from zensols.datdesc.hyperparam import HyperparamModel, HyperparamSet

logger = logging.getLogger(__name__)


@dataclass
class TestContainer(object):
    svm: HyperparamSet = field()
    km: HyperparamSet = field()


class TestHyperparamConfig(unittest.TestCase):
    def setUp(self):
        self.maxDiff = sys.maxsize
        self.fac = ImportConfigFactory(
            YamlConfig('test-resources/load/call.yml'))

    def test_set(self):
        """Test calling the HyperparamSetLoader (no path)."""
        settings: Settings = self.fac('test_set')
        hpset: HyperparamSet = settings.hpset
        self.assertEqual(HyperparamSet, type(hpset))
        self.assertEqual(20, hpset.svm.max_iter)

    def test_path(self):
        """Same but use a dot sep path retrieve the HyperparamModel."""
        cont: TestContainer = self.fac('test_container')
        self.assertEqual(TestContainer, type(cont))
        self.assertEqual(HyperparamModel, type(cont.svm))
        self.assertEqual(HyperparamModel, type(cont.km))
        self.assertEqual([1, 2], cont.km.strata)
        self.assertEqual(None, cont.km.n_clusters)
        self.assertEqual(20, cont.svm.max_iter)

    def test_updates(self):
        cont: TestContainer = self.fac('test_container_update')
        self.assertEqual(TestContainer, type(cont))
        self.assertEqual(16, cont.svm.max_iter)
        self.assertEqual(None, cont.svm.kernel)
        self.assertEqual(2, cont.km.n_clusters)
        self.assertEqual([5, 6], cont.km.strata)
