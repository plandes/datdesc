import logging
import unittest


if 0:
    logging.basicConfig(level=logging.WARNING)

logger = logging.getLogger(__name__)


class TestApplication(unittest.TestCase):
    def test_ver(self):
        print()
        import sys
        print('PYTHON', sys.version_info)

