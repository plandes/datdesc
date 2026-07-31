"""Classes to create first class object and process files.

"""
from typing import Any
from collections.abc import Iterable, Callable
from dataclasses import dataclass, field
from abc import abstractmethod, ABCMeta
import sys
from io import TextIOBase
import logging
import re
from pathlib import Path
from jinja2 import Template, Environment, BaseLoader
from zensols.config import Dictable, ConfigFactory
from zensols.persist import PersistableContainer
from . import DataDescriptionError

logger = logging.getLogger(__name__)


@dataclass
class RenderableArtifact(PersistableContainer, Dictable, metaclass=ABCMeta):
    """Data that can be rendered from a :class:`.Renderable`.

    """
    name: str = field()
    """The name of the artifiact, also used in reference labels."""

    path: Path | str = field()
    """The file that has the data used to populate this artifiact."""

    caption: str = field()
    """The human readable string used to the caption in the figure."""

    template: str = field()
    """The figure template, which lives in the application configuration
    ``obj.yml``.

    """
    template_params: dict[str, str] = field(default_factory=dict)
    """Parameters used in the template."""

    definition_file: Path = field(default=None)
    """The YAML file from which this instance was created."""

    head: str = field(default=None)
    """The header to use for the table, which is used as the text in the list of
    tables and made bold in the table.

    """
    writes: list[str] = field(default_factory=lambda: ['template'])
    """A list of what to output for this artifact.  Each must be a method in the
    subclass and the default only renders the template.  This is configurable so
    a client can decide what from the artifact is output.

    """
    def __post_init__(self):
        super().__init__()

    def _get_path(self) -> Path:
        return self._path_value

    def _set_path(self, path: Path):
        self._path_value = path

    @property
    def _path(self) -> Path:
        """The path of the rendered item to save.  This is constructed from
        :obj:`image_dir`, :obj:`name` and :obj`image_format`.  Conversely,
        when set, it updates these fields.

        """
        return self._get_path()

    @_path.setter
    def _path(self, path: Path):
        """The path of the image figure to save.  This is constructed from
        :obj:`image_dir`, :obj:`name` and :obj`image_format`.  Conversely,
        when set, it updates these fields.

        """
        self._set_path(path)

    def _render_template(self, params: dict[str, Any]) -> str:
        if logger.isEnabledFor(logging.TRACE):
            logger.trace(f'template: <<{self.template}>>')
        template: Template = Environment(loader=BaseLoader).from_string(
            self.template)
        return template.render(params)

    def _get_template_params(self) -> dict[str, Any]:
        return dict(self.asdict())

    def _write_template(self, depth: int, writer: TextIOBase):
        template_params: dict[str, Any] = self._get_template_params()
        rendered: str = self._render_template(template_params)
        self._write_block(rendered, depth, writer)

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        writeable: str
        for writeable in self.writes:
            meth_name: str = f'_write_{writeable}'
            if not hasattr(self, meth_name):
                raise DataDescriptionError(
                    f"No such writeable object in {self}: '{writeable}'")
            else:
                meth: Callable = getattr(self, meth_name)
                meth(depth, writer)


RenderableArtifact.path = RenderableArtifact._path


@dataclass
class Renderable(Dictable, metaclass=ABCMeta):
    """Creates rendered output from a machine readble input file.

    """
    path: Path = field()
    """The input definition of the object to render."""

    def get_artifacts(self) -> Iterable[RenderableArtifact]:
        """Return artifacts created found on :obj:`path`."""
        return iter(())

    def __iter__(self) -> Iterable[Any]:
        """See :meth:`get_artifacts`."""
        return self.get_artifacts()

    @abstractmethod
    def render(self, output: Path) -> Path:
        """Write the rendered output.

        :param output: either a file or directory (depending on the subclass)

        """
        pass


@dataclass
class RenderableFactory(Dictable):
    """Creates instances of :class:`.Renderable` from file paths.

    """
    config_factory: ConfigFactory = field()
    """Creates table and figure factories."""

    types: dict[str, re.Pattern | str] = field()
    """Application config to regular expression mapping."""

    name_format: str = field()
    """Section format used to create instances with :obj`config_factory`."""

    def __post_init__(self):
        def map_tup(t: tuple[str, re.Pattern | str]) -> tuple[str, re.Pattern]:
            pat: re.Pattern | str = t[1]
            if isinstance(pat, str):
                pat = re.compile(pat)
            return (t[0], pat)

        self.types = dict(map(map_tup, self.types.items()))

    def _from_name(self, name: str, path: Path = None) -> Renderable:
        sec_name: str = self.name_format.format(name=name)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'renderable section name: {sec_name}')
        return self.config_factory.new_instance(sec_name, path)

    def _from_file(self, path: Path, expect: bool = False) -> Renderable:
        fname: str = path.name
        rend_name: str = None
        name: str
        pat: re.Pattern
        for name, pat in self.types.items():
            m: re.Match = pat.match(fname)
            if m is not None:
                rend_name = name
                break
        if rend_name is None:
            if expect:
                raise DataDescriptionError(f'Unknown file type mapping: {path}')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"no match: '{name}' using '{pat}'")
        else:
            return self._from_name(rend_name, path)

    def _from_dir(self, path: Path) -> Iterable[Renderable]:
        return filter(
            lambda r: r is not None,
            map(self._from_file, path.iterdir()))

    def __call__(self, path: Path | str) -> Iterable[Renderable]:
        if isinstance(path, str):
            return self._from_name(path)
        elif path.is_dir():
            return self._from_dir(path)
        else:
            return iter([self._from_file(path, expect=True)])
