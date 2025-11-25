"""Common used plots for ML.

"""
__author__ = 'Paul Landes'

from typing import Tuple, List, Dict, Sequence, Iterable, Any, Union, Callable
from dataclasses import dataclass, field
import logging
import itertools as it
import math
from matplotlib.pyplot import Axes
import pandas as pd
from zensols.util import APIError
from .figure import Plot

logger = logging.getLogger(__name__)


@dataclass
class PaletteContainerPlot(Plot):
    """A base class that supports creating a color palette for subclasses.

    """
    palette: Union[str, Callable] = field(default=None)
    """Either the a list of color characters or a callable that takes the number
    of colors as input.  For example, the Seaborn color palette (such as
    ``sns.color_palette('tab10', n_colors=n)``).  This is used as the
    ``palette`` parameter in the ``sns.pointplot`` call.

    """
    def __post_init__(self):
        import seaborn as sns
        super().__post_init__()
        self._set_defaults(
            palette=lambda n: sns.color_palette('hls', n_colors=n))

    def _get_palette(self, hue_names: Sequence[str]) -> \
            Dict[str, Tuple[int, int, int]]:
        palette: Union[str, Callable] = self.palette
        n_colors = len(hue_names)
        colors: Tuple[int, int, int]
        if isinstance(palette, Callable):
            colors = palette(n_colors)
        elif isinstance(palette, str):
            p_len: int = len(palette)
            n_iters: int = math.ceil(n_colors / p_len)
            colors = tuple(it.chain.from_iterable(
                it.repeat(list(palette), n_iters)))[:n_colors]
        else:
            raise APIError(f'Unknown palette type: {type(palette)}')
        return dict(zip(hue_names, colors))


@dataclass
class DataFramePlot(Plot):
    """A base class for plots that render data from a Pandas dataframe.

    """
    data: pd.DataFrame = field(default=None, repr=False)
    """The data to plot."""


@dataclass
class PointPlot(PaletteContainerPlot, DataFramePlot):
    """An abstract base class that renders overlapping lines that uses a
    :mod:`seaborn` ``pointplot``.

    """
    point_data: List[Tuple[str, pd.DataFrame]] = field(default=None, repr=False)
    """The data to plot.  Each element is tuple first components with the plot
    name.  The second component is a dataframe with columns:

        * :obj:`x_column_name`: the X values of the graph, usually an
          incrementing number

        * :obj:`y_column_name`: a list loss float values

    Optionally use :meth:`add_line` to populate this list.

    """
    x_axis_name: str = field(default=None)
    """The axis name with the X label."""

    y_axis_name: str = field(default=None)
    """The axis name with the Y label."""

    x_column_name: str = field(default='x')
    """The :obj:`data` column with the X values."""

    y_column_name: Union[str, Sequence[Tuple[str, str]]] = field(default='y')
    """The :obj:`data` column(s) with the Y values."""

    key_title: str = field(default=None)
    """The title that goes in the key."""

    sample_rate: int = field(default=0)
    """Every $n$ data point in the list of losses is added to the plot."""

    plot_params: Dict[str, Any] = field(
        default_factory=lambda: dict(markersize=0, linewidth=1.5))
    """Parameters given to :func:`seaborn.plotpoint`.  The default are
    decorative parameters for the marker size and line width.

    """
    hue_name: str = field(default=None, repr=False)
    """The name of the heu given to :mod:`seaborn.pointplot`."""

    hue_names: Tuple[str, ...] = field(default=None, repr=False)
    """Hue names give to :mod:`seaborn.pointplot`."""

    def __post_init__(self):
        super().__post_init__()
        df: pd.DataFrame = self.data
        if self.title is None:
            self.title = ''
        if df is not None and self.point_data is None and \
           self.x_column_name is not None and \
           self.y_column_name is not None and \
           isinstance(self.y_column_name, (Tuple, List)) and \
           self.x_column_name in df.columns:
            x_vals: List
            if self.x_column_name is None:
                x_vals = tuple(range(len(df)))
            else:
                x_vals = df[self.x_column_name]
            col_map: Sequence[Tuple[str, str]] = self.y_column_name
            self.y_column_name = 'y_column'
            col: str
            name: str
            for col, name in col_map:
                self.add(name, df[col], x_vals)
        self.data = None

    def add(self, name: str, line: Iterable[float], x_vals: Sequence = None):
        """Add the losses of a dataset by adding X values as incrementing
        integers the size of ``line``.

        :param name: the line name

        :param line: the Y values for the line

        :param x_vals: the values used for the X axes, which defaults to
                       `range(1, n+ 1)`

        """
        line = tuple(line)
        n: int = len(line)
        df = pd.DataFrame(
            data=tuple(range(1, n + 1)) if x_vals is None else x_vals,
            columns=[self.x_column_name])
        df[self.y_column_name] = line
        if self.point_data is None:
            self.point_data = []
        self.point_data.append((name, df))

    def _point_data_to_meld(self) -> pd.DataFrame:
        data: Sequence[Tuple[str, pd.DataFrame]] = self.point_data
        hue_name: str = self.title
        x_axis_name: str = self.x_axis_name
        y_axis_name: str = self.y_axis_name
        x_column_name: str = self.x_column_name
        y_column_name: str = self.y_column_name
        df: pd.DataFrame = None
        assert len(data) > 0
        desc: str
        dfl: pd.DataFrame
        for desc, dfl in data:
            dfl = dfl[[y_column_name, x_column_name]]
            dfl = dfl.rename(columns={y_column_name: desc})
            if df is None:
                df = dfl
            else:
                df = df.merge(
                    dfl, left_on=x_column_name, right_on=x_column_name,
                    suffixes=(None, None))
        if self.sample_rate > 0:
            df = df[(df.index % self.sample_rate) == 0]
        df = df.rename(columns={x_column_name: x_axis_name})
        df = df.melt(x_axis_name, var_name=hue_name, value_name=y_axis_name)
        self.hue_names = tuple(df[hue_name].drop_duplicates().to_list())
        return df

    def _render(self, axes: Axes):
        import seaborn as sns
        x_axis_name: str = self.x_axis_name
        y_axis_name: str = self.y_axis_name
        df: pd.DataFrame = self.data
        if df is None:
            df = self._point_data_to_meld()
        params: Dict[str, Any] = dict(
            ax=axes, data=df, x=x_axis_name, y=y_axis_name, hue=self.title,
            palette=self._get_palette(self.hue_names))
        params.update(self.plot_params)
        sns.pointplot(**params)
        self._set_legend_title(axes, self.key_title)


@dataclass
class BarPlot(PaletteContainerPlot, DataFramePlot):
    """Create a bar plot using :meth:`seaborn.barplot`.

    """
    x_axis_label: str = field(default=None)
    """The axis name with the X label."""

    y_axis_label: str = field(default=None)
    """The axis name with the Y label."""

    x_column_name: str = field(default=None)
    """The :obj:`data` column with the X values."""

    y_column_name: str = field(default=None)
    """The :obj:`data` column with the Y values."""

    hue_column_name: str = field(default=None)
    """The column in :obj:`data` used for the data hue (each data category will
    have a unique in :obj:`palette`.

    """
    x_label_rotation: float = field(default=0)
    """The degree of label rotation."""

    key_title: str = field(default=None)
    """The title that goes in the key."""

    log_scale: float = field(default=None)
    """The log scale of the Y-axis (see :obj:`matplotlib.axes.Axis.set_yscale`.

    """
    render_value_font_size: int = field(default=None)
    """Whether to add Y-axis values to the bars."""

    hue_palette: bool = field(default=False)
    """Whether to use the hue to calculate the palette colors."""

    plot_params: Dict[str, Any] = field(default_factory=dict)
    """Parameters given to :func:`seaborn.barplot`."""

    def _render(self, axes: Axes):
        from matplotlib.ticker import ScalarFormatter
        import seaborn as sns
        df: pd.DataFrame = self.data
        params: Dict[str, Any] = dict(
            # dataframe of occurances and hue name
            data=df,
            # subplot
            ax=axes,
            # data mapping
            x=self.x_column_name,
            y=self.y_column_name,
            hue=self.hue_column_name,
            # do not render the error (line above/intersecting with bars)
            errorbar=None,
            **self.plot_params)
        if self.hue_palette and 'palette' not in params:
            # palette's colors are the hues of variables
            params['palette'] = self._get_palette(
                self.data[self.hue_column_name].drop_duplicates())
        sns.barplot(**params)
        if self.render_value_font_size:
            for cont in axes.containers:
                axes.bar_label(cont, fontsize=self.render_value_font_size)
        if self.log_scale is not None:
            # add log scale
            axes.set_yscale('log', base=self.log_scale)
            # create human readable ticks
            # https://stackoverflow.com/questions/21920233/matplotlib-log-scale-tick-label-number-formatting
            axes.yaxis.set_major_formatter(ScalarFormatter())
        # set x/y axis text
        self._set_axis_labels(axes, self.x_axis_label, self.y_axis_label)
        # set the legend title or hide the hue_col text if not set
        self._set_legend_title(axes, self.key_title)
        # rotate labels
        if self.x_label_rotation != 0:
            axes.tick_params(axis='x', labelrotation=self.x_label_rotation)


@dataclass
class HistPlot(PaletteContainerPlot):
    """Create a histogram plot using :meth:`seaborn.histplot`.

    """
    data: List[Tuple[str, pd.DataFrame]] = field(
        default_factory=list, repr=False)
    """The data to plot.  Each element is tuple first components with the plot
    name.

    """
    x_axis_label: str = field(default=None)
    """The axis name with the X label."""

    y_axis_label: str = field(default=None)
    """The axis name with the Y label."""

    key_title: str = field(default=None)
    """The title that goes in the key."""

    log_scale: float = field(default=None)
    """See the :meth:`seaborn.histplot` ``log_scale`` parameter.  This is also
    used to update the ticks if provided.

    """
    plot_params: Dict[str, Any] = field(default_factory=dict)
    """Parameters given to :func:`seaborn.histplot`."""

    def add(self, name: str, data: Iterable[float]):
        """Add occurances to use in the histogram.

        :param name: the variable name

        :param data: the data to render

        """
        self.data.append((name, pd.DataFrame(data, columns=[name])))

    def _render(self, axes: Axes):
        import math
        import matplotlib.ticker as ticker
        import seaborn as sns
        dfs: pd.DataFrame = []
        hue_col: str = 'name'
        value_col: str = 'occur'

        # create column-singleton dataframes with the occurance data with a name
        # column for the hue
        name: str
        df: pd.DataFrame
        for name, df in self.data:
            dfg: pd.DataFrame = df[name].to_frame().\
                rename(columns={name: value_col})
            dfg[hue_col] = name
            dfs.append(dfg)
        params: Dict[str, Any] = dict(
            # dataframe of occurancesand hue name
            data=pd.concat(dfs),
            # subplot
            ax=axes,
            # occurances column in the agg dataframe
            x=value_col,
            # hue identifier
            hue=hue_col,
            **self.plot_params)
        # log_scale is treated separately to recreate ticks
        if self.log_scale is not None:
            params['log_scale'] = self.log_scale
        sns.histplot(**params)
        # create human readable ticks
        # https://stackoverflow.com/questions/53747298/how-to-format-axis-tick-labels-from-number-to-thousands-or-millions-125-436-to
        if self.log_scale is not None:
            axes.xaxis.set_major_formatter(ticker.FuncFormatter(
                lambda x, pos: f'{math.log(x, self.log_scale) * 10:.0f}'))
        # set x/y axis text
        self._set_axis_labels(axes, self.x_axis_label, self.y_axis_label)
        # set the legend title or hide the hue_col text if not set
        self._set_legend_title(axes, self.key_title)


@dataclass
class HeatMapPlot(PaletteContainerPlot, DataFramePlot):
    """Create heat map plot and optionally normalize.  This uses
    :mod:`seaborn`'s ``heatmap``.

    """
    format: str = field(default='.2f')
    """The format of the plots's cell numerical values."""

    x_label_rotation: float = field(default=0)
    """The degree of label rotation."""

    params: Dict[str, Any] = field(default_factory=dict)
    """Additional parameters to give to :func:`seaborn.heatmap`."""

    def _render(self, axes: Axes):
        import seaborn as sns
        chart = sns.heatmap(ax=axes, data=self.data,
                            annot=True, fmt=self.format, **self.params)
        if self.x_label_rotation != 0:
            axes.set_xticklabels(
                chart.get_xticklabels(),
                rotation=self.x_label_rotation)


@dataclass
class RadarPlot(DataFramePlot):
    """A radar plot (a.k.a. spider plolt).

    """
    key_title: str = field(default=None)
    """The title that goes in the key."""

    frame: str = field(default='circle')
    """Shape of frame surrounding axes (``circle`` or ``polygon``).

    """
    render_value_font_size: int = field(default=None)
    """Whether to add Y-axis values to the bars."""

    label_gap: int = field(default=None)
    """The spacing of the labels from the center of the plot."""

    alpha: float = field(default=0.25)
    """The fill alpha for each row of the dataframe.

    """
    def __post_init__(self):
        super().__post_init__()
        self._register_projection(len(self.data.columns), self.frame)

    def _register_projection(self, num_vars: int, frame: str):
        """Create a radar chart with `num_vars` axes.

        This function creates a RadarAxes projection and registers it.

        Parameters
        ----------
        num_vars : int
            Number of variables for radar chart.
        frame : {'circle' | 'polygon'}
            Shape of frame surrounding axes.

        :link: https://stackoverflow.com/questions/52910187/how-to-make-a-polygon-radar-spider-chart-in-python

        """
        import numpy as np
        from matplotlib.projections import register_projection
        from matplotlib.patches import Circle, RegularPolygon
        from matplotlib.path import Path
        from matplotlib.projections.polar import PolarAxes
        from matplotlib.spines import Spine
        from matplotlib.transforms import Affine2D

        # calculate evenly-spaced axis angles
        theta = np.linspace(0, 2 * np.pi, num_vars, endpoint=False)
        self._theta = theta

        class RadarAxes(PolarAxes):
            name = 'radar'

            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                # rotate plot such that the first axis is at the top
                self.set_theta_zero_location('N')

            def fill(self, *args, closed=True, **kwargs):
                """Override fill so that line is closed by default"""
                return super().fill(closed=closed, *args, **kwargs)

            def plot(self, *args, **kwargs):
                """Override plot so that line is closed by default"""
                lines = super().plot(*args, **kwargs)
                for line in lines:
                    self._close_line(line)

            def _close_line(self, line):
                x, y = line.get_data()
                # FIXME: markers at x[0], y[0] get doubled-up
                if x[0] != x[-1]:
                    x = np.concatenate((x, [x[0]]))
                    y = np.concatenate((y, [y[0]]))
                    line.set_data(x, y)

            def set_varlabels(self, labels):
                self.set_thetagrids(np.degrees(theta), labels)

            def _gen_axes_patch(self):
                # The Axes patch must be centered at (0.5, 0.5) and of radius
                # 0.5 in axes coordinates.
                if frame == 'circle':
                    return Circle((0.5, 0.5), 0.5)
                elif frame == 'polygon':
                    return RegularPolygon((0.5, 0.5), num_vars,
                                          radius=.5, edgecolor="k")
                else:
                    raise ValueError("unknown value for 'frame': %s" % frame)

            def draw(self, renderer):
                """ Draw. If frame is polygon, make gridlines polygon-shaped """
                if frame == 'polygon':
                    gridlines = self.yaxis.get_gridlines()
                    for gl in gridlines:
                        gl.get_path()._interpolation_steps = num_vars
                super().draw(renderer)

            def _gen_axes_spines(self):
                if frame == 'circle':
                    return super()._gen_axes_spines()
                elif frame == 'polygon':
                    # spine_type must be 'left'/'right'/'top'/'bottom'/'circle'.
                    spine = Spine(axes=self,
                                  spine_type='circle',
                                  path=Path.unit_regular_polygon(num_vars))
                    # unit_regular_polygon gives a polygon of radius 1 centered
                    # at (0, 0) but we want a polygon of radius 0.5 centered at
                    # (0.5, 0.5) in axes coordinates.
                    spine.set_transform(Affine2D().scale(.5).translate(.5, .5) +
                                        self.transAxes)
                    return {'polar': spine}
                else:
                    raise ValueError("unknown value for 'frame': %s" % frame)

        register_projection(RadarAxes)

    def _set_legend_title(self, axes: Axes, title: str = None):
        super()._set_legend_title(axes, title)
        if title is not None or len(self.legend_params) > 0:
            # needed to display prompt
            axes.legend(title=title, **self.legend_params)

    def _render(self, axes: Axes):
        import math
        import pandas as pd
        axes.set_theta_offset(math.pi / 2)
        axes.set_theta_direction(-1)
        cats: List[str] = self.data.columns.to_list()
        theta = self._theta
        rid: Any
        row: pd.Series
        for rid, row in self.data.iterrows():
            data: List[int] = row.to_list()
            axes.plot(theta, data, label=str(rid))
            axes.fill(theta, data, alpha=self.alpha)
        axes.set_varlabels(cats)
        self._set_legend_title(axes, self.key_title)
        params: Dict[str, Any] = {}
        if self.label_gap is not None:
            params['pad'] = self.label_gap
        if self.render_value_font_size:
            params['labelsize'] = self.render_value_font_size
        if len(params) > 0:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'setting params: {params}')
            axes.tick_params(**params)
