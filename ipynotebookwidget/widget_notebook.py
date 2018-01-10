import json
import traitlets as T
from copy import deepcopy

from nbformat.v4 import new_notebook, writes, new_code_cell
from nbformat.notebooknode import NotebookNode

import ipywidgets as W

from .widget_kernel import Kernel
from .utils import save_notebook

try:
    import pandas as pd
except ImportError:
    pd = None

from_json = W.widget_serialization["from_json"]


class Notebook(W.Widget):
    file_name = T.Unicode("Untitled", allow_none=True).tag(sync=True)
    kernel_name = T.Unicode("python3").tag(sync=True)
    ipynb = T.Dict(allow_none=True).tag(sync=True)
    json = T.Unicode(allow_none=True).tag(sync=True)
    stdout = T.Tuple(allow_none=True).tag(sync=True)
    stderr = T.Tuple(allow_none=True).tag(sync=True)
    kernels = T.Tuple([]).tag(sync=True, **W.widget_serialization)
    code_cells = T.Tuple([]).tag(sync=True)

    # "private" traitlets
    notebook_node = T.Instance(NotebookNode, allow_none=True)

    kernel_count = T.Integer(0).tag(sync=True)

    def __init__(self, *args, **kwargs):
        if kwargs.get("notebook_node") is None:
            kwargs["notebook_node"] = new_notebook()

        super(Notebook, self).__init__(*args, **kwargs)

    @property
    def df(self):
        self._to_ipynb()
        return pd.io.json.json_normalize(self.ipynb["cells"])

    @T.observe("code_cells")
    def _on_code_cells(self, _=None):
        self.notebook_node.cells = list(map(new_code_cell, self.code_cells))
        self._to_ipynb()

    @T.observe("notebook_node")
    def _to_ipynb(self, _=None):
        _json = writes(self.notebook_node)
        if _json != self.json:
            self.json = _json
            self.ipynb = json.loads(_json)

    def run(self, cells=None, kernels=[], kernel_name=None, shutdown=True):
        kernels = kernels or self.kernels or []

        if cells is not None:
            cells = [
                c if isinstance(c, NotebookNode) else new_code_cell(c)
                for c in cells
            ]

        cells = cells or self.notebook_node.cells or []

        if not kernels:
            kernels = [Kernel(
                name=kernel_name or self.kernel_name,
                file_name=f"{self.file_name}_{self.kernel_count}"
            )]
            self.kernel_count += 1

        for kernel in kernels:
            yield kernel.run(
                cells=deepcopy(cells or self.notebook_node.cells or []),
                shutdown=shutdown)

    def save(self):
        if self.file_name is None:
            raise ValueError("needs file_name")
        save_notebook(self.file_name, self.notebook_node)
