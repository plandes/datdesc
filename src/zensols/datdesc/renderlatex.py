"""Things rendered for LaTeX files (usually ``.sty``).

"""
from dataclasses import dataclass, field
from io import StringIO
from collections.abc import Sequence
from . import DataDescriptionError
from .render import RenderableArtifact


@dataclass
class RenderableLatexArtifact(RenderableArtifact):
    """Subclasses implement behavior to render LaTeX files.  There are also
    utility method for generating latex commands.

    """
    default_params: Sequence[Sequence[str]] = field(default_factory=list)
    """Default parameters to be substituted in the template that are
    interpolated by (i.e. LaTeX) numeric values such as #1, #2, etc.  This is a
    sequence (list or tuple) of ``(<name>, [<default>])`` where ``name`` is
    substituted by name in the template and ``default`` is the default if not
    given in :obj:`params`.

    """
    params: dict[str, str] = field(default_factory=dict)
    """Parameters used in the template that override of the
    :obj:`default_params`.

    """
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
