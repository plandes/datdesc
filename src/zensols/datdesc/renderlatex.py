"""Things rendered for LaTeX files (usually ``.sty``).

"""
from typing import Any, ClassVar
from collections.abc import Sequence
from dataclasses import dataclass, field
import logging
import sys
from itertools import chain
from datetime import datetime
import re
from io import StringIO, TextIOBase
from zensols.config import Dictable
from .domain import DataDescriptionError
from .render import RenderableArtifact

logger = logging.getLogger(__name__)


@dataclass
class RenderableLatexArtifact(RenderableArtifact):
    """Subclasses implement behavior to render LaTeX files.  There are also
    utility method for generating latex commands.

    """
    _FILE_NAME_REGEX: ClassVar[re.Pattern] = re.compile(r'(.+)\.yml')
    """Used to narrow down to a :obj:`package_name`."""

    uses: list[str] = field(default_factory=list)
    """Comma separated list of packages to use."""

    default_params: Sequence[Sequence[str]] = field(default_factory=list)
    """Default parameters to be substituted in the template that are
    interpolated by (i.e. LaTeX) numeric values such as #1, #2, etc.  This is a
    sequence (list or tuple) of ``(<name>, [<default>])`` where ``name`` is
    substituted by name in the template and ``default`` is the default if not
    given in :obj:`params`.

    For any that have no default, which is a singleton paramenter name,
    arguments are created for the function that must be supplied to the
    function.

    """
    params: dict[str, str] = field(default_factory=dict)
    """Parameters used in the template that override of the
    :obj:`default_params`.

    """
    def __post_init__(self):
        super().__post_init__()
        if isinstance(self.uses, str):
            self.uses = re.split(r'\s*,\s*', self.uses)

    @property
    def package_name(self) -> str:
        """Return the package name for the table in ``table_path``."""
        fname: str = self.definition_file.name
        m: re.Match = self._FILE_NAME_REGEX.match(fname)
        if m is None:
            raise DataDescriptionError(
                f'Does not appear to be a YAML file: {fname}', self.name)
        return m.group(1)

    def _get_template_params(self) -> dict[str, Any]:
        params: dict[str, Any] = dict(self.asdict())
        params.update(self._get_command_params())
        return params

    def _get_command_params(self) -> dict[str, str]:
        """Create parameters prefixed as a nested :class:`~builtins.dict` with
        name ``p`` to be substituted as values in the table template.  A
        ``p.argdef`` is also added that gives the commands number of arguments
        and the initial default.

        """
        dparams: Sequence[Sequence[str]] = self.default_params  # metadata
        oparams: dict[str, str] = self.params  # user overridden
        aparams: dict[str, str] = {}  # argument params
        # to populate and return
        params: dict[str, str] = {
            'p': aparams,
            't': self.template_params}
        proto: str = ''
        init_arg: str = ''
        pix: int = 1  # parameter index
        usage = StringIO()
        usage.write(f'\\{self.name}')
        dpix: int  # default parameter index
        param: Sequence[str]
        for dpix, param in enumerate(dparams):
            lp: int = len(param)
            if lp < 1:
                msg: str = f"No entries in param definition '{param}'"
                raise DataDescriptionError(msg, self.name)
            if len(param) > 2:
                raise DataDescriptionError(
                    f"Expecting < 2 params: '{param}'", self.name)
            name: str = param[0]
            default: str = param[1] if len(param) > 1 else None
            val: str = oparams.get(name, default)
            if dpix == 0:
                if val is not None:
                    init_arg = f'[{val}]'
            if dpix == 0 and val is not None:
                usage.write(f'[<{name}>]')
            else:
                usage.write(f'{{<{name}>}}')
            if val is None or (dpix == 0 and len(init_arg) > 0):
                val = f'#{pix}'
                pix += 1
            aparams[name] = val
        proto = f'[{pix - 1}]{init_arg}'
        aparams['argdef'] = proto
        params['usage'] = usage.getvalue()
        return params


@dataclass
class RenderableLatexPackage(Dictable):
    """Generate a Latex table from a CSV file.

    """
    artifacts: Sequence[RenderableLatexArtifact] = field()
    """A list of instances to create Latex definitions."""

    name: str = field()
    """The name Latex .sty package."""

    description: str = field(default='{date} Artifacts')
    """The package description."""

    def _write_header(self, depth: int, writer: TextIOBase):
        date = datetime.now().strftime('%Y/%m/%d')
        params: dict[str, Any] = self.asdict() | {'date': date}
        desc: str = self.description.format(**params)
        writer.write("""\\NeedsTeXFormat{LaTeX2e}
\\ProvidesPackage{%(package_name)s}[%(desc)s]

""" % {'package_name': self.name, 'desc': desc})
        uses: set[str] = set(chain.from_iterable(
            map(lambda t: t.uses, self.artifacts)))
        for use in sorted(uses):
            writer.write(f'\\usepackage{{{use}}}\n')
        if len(uses) > 0:
            writer.write('\n')

    def _write_artifact(self, artifact: RenderableLatexArtifact,
                        depth: int, writer: TextIOBase):
        artifact.write(depth, writer)

    def write(self, depth: int = 0, writer: TextIOBase = sys.stdout):
        """Write the Latex table to the writer given in the initializer.

        """
        art_len: int = len(self.artifacts)
        self._write_header(depth, writer)
        for i, artifact in enumerate(self.artifacts):
            try:
                #artifact.write(depth, writer)
                self._write_artifact(artifact, depth, writer)
            except Exception as e:
                msg: str = f"could not format '{artifact.name}': {e}"
                self._write_line(f'% erorr: {msg}', depth, writer)
                logger.error(msg, e)
            if i < art_len:
                writer.write('\n')
