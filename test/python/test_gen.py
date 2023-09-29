import sys
import logging
import unittest
import datetime
import shutil
from pathlib import Path
from zensols.cli import CliHarness
from zensols.datdesc import ApplicationFactory


if 0:
    logging.basicConfig(level=logging.WARNING)

logger = logging.getLogger(__name__)


class TestApplication(unittest.TestCase):
    def setUp(self):
        self.maxDiff = sys.maxsize
        self.targ_dir: Path = Path('target')
        self.out_dir: Path = self.targ_dir / 'lat'
        if self.targ_dir.is_dir():
            shutil.rmtree(self.targ_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.harness: CliHarness = ApplicationFactory.create_harness()

    def _today_date(self) -> str:
        today = datetime.datetime.now()
        return today.strftime("%Y/%m/%d")

    def _text_compare(self, out_file: Path, gold_file: Path):
        self.assertTrue(out_file.is_file(), f'no out file: {out_file}')
        self.assertTrue(gold_file.is_file(), f'no gold file: {gold_file}')
        with open(out_file) as f:
            out: str = f.read().strip()
        with open(gold_file) as f:
            gold: str = f.read().strip()
        today: str = self._today_date()
        gold = gold.replace('{{DATE}}', today)
        if 0:
            print(out)
        self.assertEqual(gold, out, f'\n\ndiff in file {out_file}')

    def test_table(self):
        in_dir: Path = Path('test-resources/config')
        self.harness.execute(f'table {in_dir} {self.out_dir} --level=warn')
        print('\ntesting data table generation')
        conf_file: Path
        for conf_file in in_dir.iterdir():
            print(f'testing {conf_file}')
            out_file: Path = self.out_dir / f'{conf_file.stem}.sty'
            gold_file: Path = in_dir.parent / 'gold' / f'{conf_file.stem}.sty'
            logger.info(f'compare: {out_file}, {gold_file}')
            self._text_compare(out_file, gold_file)

    def test_hyper_yaml(self):
        base_dir: Path = Path('test-resources/hyperparam')
        in_file: Path = base_dir / 'svm-hyperparam.yml'
        gold_file: Path = base_dir / 'svm-gold.yaml'
        out_file: Path = self.out_dir / 'hyper.yaml'
        self.harness.execute(f'hyper {in_file} {out_file} -f yaml --level=warn')
        self._text_compare(out_file, gold_file)

    def test_hyper_sphinx(self):
        base_dir: Path = Path('test-resources/hyperparam')
        in_file: Path = base_dir / 'svm-hyperparam.yml'
        gold_file: Path = base_dir / 'svm-gold.py'
        out_file: Path = self.out_dir / 'svm-hyper.py'
        self.harness.execute(f'hyper {in_file} {out_file} -f sphinx --level=warn')
        self._text_compare(out_file, gold_file)

    def test_hyper_table(self):
        in_dir: Path = Path('test-resources/hyperparam')
        name: str = 'svm-hyperparam'
        out_file: Path = self.out_dir / f'{name}.sty'
        gold_file: Path = in_dir.parent / 'gold' / f'{name}.sty'
        self.harness.execute(f'table {in_dir} {self.out_dir} --level=warn')
        self._text_compare(out_file, gold_file)
