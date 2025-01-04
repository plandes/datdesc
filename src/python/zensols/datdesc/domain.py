"""Domain classes used by the API.

"""
__author__ = 'Paul Landes'

from dataclasses import dataclass, field
import logging
from zensols.util import APIError

logger = logging.getLogger(__name__)


class DataDescriptionError(APIError):
    """Thrown for any application level error.

    """
    pass


class LatexTableError(DataDescriptionError):
    """Thrown for any application level error related to creating tables.

    """
    pass
