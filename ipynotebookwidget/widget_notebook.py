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

    def run(self, cells=None, kernels=[], kernel_name=None, shutdown=True,
            append=False, save=True, reuse=True, start=True):

        if reuse:
            kernels = kernels or self.kernels

        kernels = kernels or []
        print("KERNELS", [k.file_name for k in kernels])

        if cells is None:
            cell_nodes = self.ipynb["cells"]
        else:
            cell_nodes = [
                c if isinstance(c, dict) else
                new_code_cell(c) if isinstance(c, str) else
                new_code_cell("\n".join(c))
                for c in cells
            ]
            if save:
                if append:
                    self.notebook_node.cells += cell_nodes
                else:
                    self.notebook_node.cells = cell_nodes
                self._to_ipynb()
            cell_nodes = self.ipynb["cells"]

        if not kernels and start:
            kernel = Kernel(
                name=kernel_name or self.kernel_name,
                file_name=f"{self.file_name}_{self.kernel_count}",
                ipynb=deepcopy(self.ipynb)
            )
            kernels = [kernel]
            self.kernels += (kernel,)
            self.kernel_count += 1

        print("-->KERNELS", [k.file_name for k in kernels])

        for kernel in kernels:
            yield kernel.run(cell_nodes=cell_nodes, shutdown=shutdown)

    def save(self):
        if self.file_name is None:
            raise ValueError("needs file_name")
        save_notebook(self.file_name, self.notebook_node)
