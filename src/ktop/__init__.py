"""
Use Notebooks and Kernels like widgets
"""
import ipywidgets as W  # noqa
import traitlets as T  # noqa

from ._version import __version__  # noqa

from .widget_kernel import Kernel  # noqa
from .widget_notebook import Notebook  # noqa
from .widget_nbformat import NBFormat, Code, Markdown, Raw  # noqa
