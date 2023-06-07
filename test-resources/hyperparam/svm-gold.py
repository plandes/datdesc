from dataclasses import dataclass, field
from zensols.datdesc import HyperparamModel


@dataclass
class SvmHyperparams(object):
    """Hyperparaeters for models ``svm``, ``k-means``.

    """
    svm: HyperparamModel = field()
    """Support vector machine.

    Hyperparameters::

        :param kernel: maps the observations into some feature space
        :type kernel: str; one of: radial, linear

        :param C: regularization parameter
        :type C: float

        :param max_iter: number of iterations, must be in the interval
                         [1, 30]
        :type max_iter: int
    """

    k_means: HyperparamModel = field()
    """K-means clustering.

    Hyperparameters::

        :param n_clusters: number of clusters
        :type n_clusters: int

        :param copy_x: when pre-computing distances it is more
                       numerically accurate to center the data first
        :type copy_x: bool

        :param strata: an array of stratified hyperparameters (made up
                       for test cases)
        :type strata: list

        :param kwargs: model keyword arguments (made up for test
                       cases)
        :type kwargs: dict
    """
