"""A simple object oriented plotting API.

"""
from __future__ import annotations
__author__ = 'Paul Landes'
from typing import (
    Tuple, List, Dict, Set, Iterable, Any, Optional, Union,
    Type, Callable, ClassVar
)
from dataclasses import dataclass, field
from abc import ABCMeta, abstractmethod
import logging
from pathlib import Path
from io import StringIO
import re
import yaml
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.pyplot import Axes
from matplotlib.figure import Figure as MatplotFigure
from zensols.util import Failure
from zensols.persist import (
    persisted, PersistedWork, FileTextUtil, Deallocatable
)
from zensols.config import (
    Serializer, Dictable, ConfigFactory, ImportConfigFactory, ImportIniConfig
)
from . import FigureError

logger = logging.getLogger(__name__)

_FIGURE_FACTORY_CONFIG: str = """
[import]
config_file = resource(zensols.datdesc): resources/figure.yml
"""


@dataclass
class Plot(Dictable, metaclass=ABCMeta):
    """An abstract base class for plots.  The subclass overrides :meth:`plot` to
    generate the plot.  Then the client can use :meth:`save` or :meth:`render`
    it.  The plot is created as a subplot providing attributes for space to be
    taken in rows, columns, height and width.

    """
    title: str = field(default=None)
    """The title to render in the plot."""

    row: int = field(default=0)
    """The row grid position of the plot."""

    column: int = field(default=0)
    """The column grid position of the plot."""

    post_hooks: List[Callable] = field(default_factory=list)
    """Methods to invoke after rendering."""

    def __post_init__(self):
        pass

    @abstractmethod
    def _render(self, axes: Axes):
        pass

    def render(self, axes: Axes):
        if self.title is not None:
            axes.set_title(self.title)
        self._render(axes)
        for hook in self.post_hooks:
            hook(self, axes)

    def _set_defaults(self, **attrs: Dict[str, Any]):
        """Unset member attributes are set to ``attribs``."""
        attr: str
        for attr, val in attrs.items():
            if getattr(self, attr) is None:
                setattr(self, attr, val)

    def _set_legend_title(self, axes: Axes, title: str = None):
        if axes.legend_ is None:
            if logger.isEnabledFor(logging.INFO):
                logger.info(f'No legend set for figure: {self}')
        else:
            if title is None:
                axes.legend_.set_title(None)
            else:
                axes.legend(title=title)

    def _set_axis_labels(self, axes: Axes, x_label: str = None,
                         y_label: str = None):
        if x_label is not None:
            axes.set_xlabel(x_label)
        if y_label is not None:
            axes.set_ylabel(y_label)

    def __str__(self) -> str:
        cls: str = self.__class__.__name__
        return f'{self.title}({cls}): row={self.row}, col={self.column}'


@dataclass
class Figure(Deallocatable, Dictable):
    """An object oriented class to manage :class:`matplit.figure.Figure` and
    subplots (:class:`matplit.pyplot.Axes`).

    """
    _DICTABLE_ATTRIBUTES: ClassVar[Set[str]] = {'path'}

    name: str = field(default='Untitled')
    """Used for file naming and the title."""

    config_factory: ConfigFactory = field(default=None, repr=False)
    """The configuration factory used to create plots."""

    title_font_size: int = field(default=0)
    """The font size :obj:`name`.  A size of 0 means do not render the title.
    Typically a font size of 16 is appropriate.

    """
    height: int = field(default=5)
    """The height in inches of the entire figure."""

    width: int = field(default=5)
    """The width in inches of the entire figure."""

    padding: float = field(default=5.)
    """Tight layout padding."""

    metadata: Dict[str, str] = field(default_factory=dict)
    """Metadata added to the image when saved."""

    plots: Tuple[Plot, ...] = field(default=())
    """The plots managed by this object instance.  Use :meth:`add_plot` to add
    new plots.

    """
    image_dir: Path = field(default=Path('.'))
    """The default image save directory."""

    image_format: str = field(default='svg')
    """The image format to use when saving plots."""

    image_file_norm: bool = field(default=True)
    """Whether to normalize the image output file name."""

    seaborn: Dict[str, Any] = field(default_factory=dict)
    """Seaborn (:mod:`seaborn`) rendering configuration.  It has the following
    optional keys:

      * ``style``: parameters used with :function:`sns.set_style`
      * ``context``: parameters used with :function:`sns.set_context`

    """
    def __post_init__(self):
        super().__init__()
        self._subplots = PersistedWork('_subplots', self)
        self._rendered = False
        self._file_name = None

    def add_plot(self, plot: Plot):
        """Add to the collection of managed plots.  This is needed for the plot
        to work if not created from this manager instance.

        :param plot: the plot to be managed

        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'adding plot: {plot}')
        self.plots = (*self.plots, plot)
        self._reset()

    def create(self, name: Union[str, Type[Plot]], **kwargs) -> Plot:
        """Create a plot using the arguments of :class:`.Plot`.

        :param name: the configuration section name of the plot

        :param kwargs: the initializer keyword arguments when creating the plot

        """
        plot: Plot
        if isinstance(name, Type):
            plot = name(**kwargs)
        else:
            plot = self.config_factory.new_instance(name, **kwargs)
        self.add_plot(plot)
        return plot

    @persisted('_subplots')
    def _get_subplots(self) -> Axes:
        """The subplot matplotlib axes.  A new subplot is create on the first
        time this is accessed.

        """
        params: Dict[str, Any] = dict(
            ncols=max(map(lambda p: p.column, self.plots)) + 1,
            nrows=max(map(lambda p: p.row, self.plots)) + 1,
            figsize=(self.width, self.height))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'creating subplots: {params}')
        fig, axs = plt.subplots(**params)
        fig.tight_layout(pad=self.padding)
        if self.title_font_size > 0:
            fig.suptitle(self.name, fontsize=self.title_font_size)
        return fig, axs

    def _get_axes(self) -> Union[Axes, np.ndarray]:
        return self._get_subplots()[1]

    def _get_figure(self) -> MatplotFigure:
        """The matplotlib figure."""
        return self._get_subplots()[0]

    @property
    def path(self) -> Path:
        """The path of the image figure to save.  This is constructed from
        :obj:`image_dir`, :obj:`name` and :obj`image_format`.  Conversely,
        when set, it updates these fields.

        """
        file_name: str = None
        if hasattr(self, '_file_name') and self._file_name is not None:
            file_name = self._file_name
        else:
            if self.image_file_norm:
                file_name = FileTextUtil.normalize_text(self.name)
            else:
                file_name = self.name
            file_name = f'{file_name}.{self.image_format}'
        return self.image_dir / file_name

    @path.setter
    def path(self, path: Path):
        """The path of the image figure to save.  This is constructed from
        :obj:`image_dir`, :obj:`name` and :obj`image_format`.  Conversely,
        when set, it updates these fields.

        """
        if path is None:
            if hasattr(self, '_file_name'):
                del self._file_name
        else:
            self._file_name = path.name
            self.image_dir = path.parent
            self.image_format = path.suffix[1:]

    @persisted('_matplotlib_offline', cache_global=True)
    def _set_matplotlib_offline(self):
        """Invoke the API to create images offline so headless Python
        interpreters don't raise exceptions for long running tasks such as
        training/testing a large model.  The method uses a ``@persisted`` with a
        global caching so it's only called once per interpreter life cycle.

        """
        import matplotlib
        matplotlib.use('agg')

    def _get_image_metadata(self) -> Dict[str, Any]:
        """Factory method to add metadata to the file.  By default,
        :obj:`metadata` is added and ``Title`` with the contents of
        :obj:`name`.

        """
        metadata: Dict[str, str] = {'Title': self.name}
        metadata.update(self.metadata)
        return metadata

    def _configure_seaborn(self):
        import seaborn as sns
        style: Dict[str, Any] = self.seaborn.get('style')
        context: Dict[str, Any] = self.seaborn.get('context')
        if style is not None:
            sns.set_style(**style)
        if context is not None:
            sns.set_context(**context)

    def _render(self):
        """Render the image using :meth:`.Plot.render`."""
        if not self._rendered:
            self._set_matplotlib_offline()
            if len(self.seaborn) > 0:
                self._configure_seaborn()
            axes: Union[Axes, np.ndarray] = self._get_axes()
            plot: Plot
            for plot in self.plots:
                ax: Axes = axes
                if isinstance(ax, np.ndarray):
                    if len(ax.shape) == 1:
                        ix = plot.row if plot.row != 0 else plot.column
                        ax = axes[ix]
                    else:
                        ax = axes[plot.row, plot.column]
                assert ax is not None
                plot.render(ax)
            self._rendered = True

    def save(self) -> Path:
        """Save the figure of subplot(s) to at location :obj:`path`.

        :param: if provided, overrides the save location :obj:`path`

        :return: the value of :obj:`path`

        """
        path: Path = self.path
        self._render()
        path.parent.mkdir(parents=True, exist_ok=True)
        self._get_figure().savefig(
            fname=path,
            format=self.image_format,
            bbox_inches='tight',
            metadata=self._get_image_metadata())
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'wrote: {path}')
        return path

    def show(self):
        """Render and display the plot."""
        plt.show()

    def _reset(self):
        """Reset the :mod:`matplotlib` module and any data structures."""
        if self._subplots.is_set():
            fig: MatplotFigure = self._get_figure()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'deallocating fig: {fig}')
            fig.clear()
        self._subplots.clear()
        self._rendered = False

    def clear(self):
        """Remove all plots and reset the :mod:`matplotlib` module."""
        self._reset()
        self.plots = ()

    def deallocate(self):
        self.clear()


@dataclass
class _FigureSerializer(Serializer):
    DATAFRAME_REGEXP = re.compile(r'^dataframe:\s*(.+)$')

    def parse_object(self, v: str) -> Any:
        v = super().parse_object(v)
        if isinstance(v, str):
            m: re.Pattern = self.DATAFRAME_REGEXP.match(v)
            if m is not None:
                path = Path(m.group(1)).expanduser()
                v = pd.read_csv(path)
        return v


@dataclass
class FigureFactory(Dictable):
    """Create instances of :`.Figure` using :meth:`create` or from configuration
    files with :meth:`from_file`.  See the `usage`_ documentation for
    information about the configuration files used by :meth:`from_file`.

    .. _usage: https://github.com/plandes/datdesc?#figures

    """
    _DEFAULT_INSTANCE: ClassVar[FigureFactory] = None
    """The singleton instance when not created from a configuration factory."""

    _TYPE_NAME: ClassVar[str] = 'type'
    """The field in the figure that indicates the type of figure.  This is used
    to select the template used to generate the figure.

    """
    _SECTION_PREFIX: ClassVar[str] = 'datdesc_plot_'
    """The section name prefix for plot templates."""

    _FIGURE_SEC_NAME: ClassVar[str] = 'datdesc_figure'
    """The section name prefix for plot templates."""

    _PLOTS_NAME: ClassVar[str] = 'plots'
    """The name of the key of the plots in figure definitions."""

    _PATH_NAME: ClassVar[str] = 'path'
    """The name of the key of the path to a CSV file of the plot data."""

    _CODE_NAME: ClassVar[str] = 'code'
    """The name of the key of the plots in figure definitions."""

    config_factory: ConfigFactory = field(repr=False)
    """The configuration factory used to create :class:`.Table` instances."""

    plot_section_regex: re.Pattern = field()
    """A regular expression that matches plot entries."""

    @classmethod
    def default_instance(cls: FigureFactory) -> FigureFactory:
        """Get the singleton instance."""
        if cls._DEFAULT_INSTANCE is None:
            config = ImportIniConfig(StringIO(_FIGURE_FACTORY_CONFIG))
            fac = ImportConfigFactory(config)
            try:
                cls._DEFAULT_INSTANCE = fac('datdesc_figure_factory')
            except Exception as e:
                fail = Failure(
                    exception=e,
                    message='Can not create stand-alone template factory')
                fail.rethrow()
        return cls._DEFAULT_INSTANCE

    @classmethod
    def reset_default_instance(cls: FigureFactory):
        """Force :meth:`default_instance' to re-instantiate a new instance on a
        subsequent call.

        """
        cls._DEFAULT_INSTANCE = None

    @persisted('_serializer')
    def _get_serializer(self) -> Serializer:
        return _FigureSerializer()

    def _get_section_by_name(self, plot_type: str = None) -> str:
        return self._SECTION_PREFIX + plot_type

    def get_plot_names(self) -> Iterable[str]:
        """Return names of plots used in :meth:``create``."""
        def map_sec(sec: str) -> Optional[str]:
            m: re.Match = self.plot_section_regex.match(sec)
            if m is not None:
                return m.group(1)
        return filter(lambda s: s is not None,
                      map(map_sec, self.config_factory.config.sections))

    def create(self, type: str, **params: Dict[str, Any]) -> Plot:
        """Create a plot from the application configuration.

        :param type: the name used to find the plot by section

        :param params: the keyword arguments used to create the plot

        :return: a new instance of the plot defined by the template

        :see: :meth:`get_plot_names`

        """
        sec: str = self._get_section_by_name(type)
        return self.config_factory.new_instance(sec, **params)

    def _apply_df_eval(self, df: pd.DataFrame, code: str):
        if code is not None:
            _locs = locals()
            exec(code)
            df = _locs['df']
        return df

    def _parse_plot(self, pdef: Dict[str, Any], raise_fn: Callable) -> Plot:
        figure_type: str = pdef.pop(self._TYPE_NAME, None)
        data: pd.DataFrame = pdef.pop('data', None)
        code: str = pdef.pop(self._CODE_NAME, None)
        if figure_type is None:
            raise_fn(f"No '{self._TYPE_NAME}' given <{pdef}>")
        if data is not None and code is not None:
            assert isinstance(data, pd.DataFrame)
            pdef['data'] = self._apply_df_eval(data, code)
        return self.create(figure_type, **pdef)

    def _unserialize(self, data: Dict[str, Any]) -> Dict[str, Any]:
        def trav(node):
            if isinstance(node, Dict):
                for k, v in node.items():
                    trav(v)
                repl = ser.populate_state(node, {})
                node.update(repl)
            elif isinstance(node, (list, tuple, set)):
                for v in node:
                    trav(v)

        ser: Serializer = self._get_serializer()
        trav(data)

    def from_file(self, figure_path: Path) -> Iterable[Figure]:
        """Return figures parsed from a YAML file (see class documentation).

        :param figure_path: the file containing the figure configurations

        """
        def raise_fn(msg: str):
            msg = f"{msg} in figure '{fig_name}' in file '{figure_path}'"
            raise FigureError(msg)

        if logger.isEnabledFor(logging.INFO):
            logger.info(f'reading figure definitions file {figure_path}')
        with open(figure_path) as f:
            content = f.read()
            defs: Dict[str, Any] = yaml.load(content, yaml.FullLoader)
        self._unserialize(defs)
        fig_name: str
        fdef: Dict[str, Any]
        for fig_name, fdef in defs.items():
            pdefs: List[Dict[str, Any]] = fdef.pop(self._PLOTS_NAME, None)
            fig: Figure = self.config_factory.new_instance(
                self._FIGURE_SEC_NAME, **fdef)
            if pdefs is None:
                raise_fn(f"Plot definition '{self._PLOTS_NAME}' not found")
            if not isinstance(pdefs, List):
                raise_fn(f"Invalid plot definition: '{pdefs}'")
            fig.name = fig_name
            pdef: Dict[str, Any]
            for pdef in pdefs:
                if not isinstance(pdef, Dict):
                    raise_fn(f"Invalid plot definition: '{pdefs}'")
                plot: Plot = self._parse_plot(pdef, raise_fn)
                fig.add_plot(plot)
            yield fig
