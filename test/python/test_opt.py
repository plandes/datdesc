from typing import Tuple
from dataclasses import dataclass, field
import sys
import logging
import unittest
import pandas as pd
from pathlib import Path
import shutil
from zensols.config import YamlConfig, ImportConfigFactory, ConfigFactory
from zensols.datdesc.hyperparam import HyperparamModel
from zensols.datdesc.opt import HyperparameterOptimizer, HyperparamResult

logger = logging.getLogger(__name__)


@dataclass
class TestHyperparameterOptimizer(HyperparameterOptimizer):
    model: HyperparamModel = field(default=None)
    config_factory: ConfigFactory = field(default=None)

    def _create_config_factory(self) -> ConfigFactory:
        return self.config_factory

    def _get_hyperparams(self) -> HyperparamModel:
        return self.model

    def _objective(self) -> Tuple[float, pd.DataFrame]:
        y_off: float = 5
        x_off: float = -2
        x: float = self.model.C
        if self.model.kernel == 'linear':
            x_off = -6
            y_off = 3
        loss: float = float(((x + x_off) ** 2) + y_off)
        return loss, self.model.values_dataframe


class TestHyperparamConfig(unittest.TestCase):
    def setUp(self):
        self.maxDiff = sys.maxsize
        self.fac = ImportConfigFactory(
            YamlConfig('test-resources/load/opt.yml'))
        targ = Path('target')
        if targ.is_dir():
            shutil.rmtree(targ)

    def test_create_space(self):
        optimizer: HyperparameterOptimizer = self.fac('optimizer')
        self.assertEqual(TestHyperparameterOptimizer, type(optimizer))
        self.assertEqual(HyperparamModel, type(optimizer.hyperparams))
        space = optimizer._create_space()
        self.assertEqual(set('kernel C'.split()), set(space.keys()))

    def test_opt(self):
        optimizer: HyperparameterOptimizer = self.fac('optimizer')
        self.assertTrue(isinstance(optimizer, HyperparameterOptimizer))
        optimizer.optimize()
        res: HyperparamResult = optimizer.get_best_result()
        df: pd.DataFrame = res.scores
        self.assertEqual((3, 4), df.shape)
        hp_val: float = df[df['name'] == 'C']['value'].item()
        epsilon: float = abs(6 - hp_val)
        if 0:
            print()
            print(hp_val, epsilon)
        self.assertTrue(epsilon < 5., f'e={epsilon}, val={hp_val}')
        self.assertTrue(abs(hp_val - res.hyp.C) < 1e-5)
        # the kernel is a hyperparameter, which isn't determinant from the opt
        self.assertTrue(res.hyp.kernel in {'linear', 'radial'})
