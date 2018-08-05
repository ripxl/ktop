import traitlets as T
import ipywidgets as W

from nbformat.notebooknode import NotebookNode
from nbformat.v4 import new_notebook


def node_or_ident(v):
    if hasattr(v, "_to_node"):
        return v._to_node()
    return v


class Node(W.Widget):
    _nbformat_factory = None

    def _to_node(self) -> NotebookNode:
        """
        """
        traits = {}

        for trait_name in self.trait_names():
            if trait_name.startswith("_"):
                continue
            elif trait_name in ["comm", "keys", "log", "node"]:
                continue

            value = getattr(self, trait_name)

            if isinstance(value, (list, tuple)):
                value = list(map(node_or_ident, value))
            elif isinstance(value, (dict)):
                value = {
                    k: node_or_ident(v)
                    for k, v in value.items()
                }

            traits[trait_name] = value

        return NotebookNode(**traits)


class Output(Node):
    output_type = T.Unicode().tag(sync=True)

    @classmethod
    def from_node(cls, node):
        return dict(
            execute_result=ExecuteResult,
            error=Error,
            stream=Stream,
            display_data=DisplayData,
        )[node.output_type](**node)

    def view(self):
        text = W.Label(self.output_type)

        def up(change):
            text.value = "T:" + self.output_type

        self.observe(up, names=None)

        return W.HBox([
            text,
        ])


class Dataful(Output):
    data = T.Dict().tag(sync=True)
    metadata = T.Dict().tag(sync=True)


class ExecuteResult(Dataful):
    execution_count = T.Integer(allow_none=True).tag(sync=True)


class DisplayData(Dataful):
    pass


class Error(Output):
    ename = T.Unicode(allow_none=True).tag(sync=True)
    evalue = T.Unicode(allow_none=True).tag(sync=True)
    traceback = T.Tuple([]).tag(sync=True)


class Stream(Output):
    name = T.Unicode(allow_none=True).tag(sync=True)
    text = T.Unicode("").tag(sync=True)

    def view(self):
        text = W.Label(self.text)
        name = W.Label(self.name)

        def up(change):
            text.value = self.text
            name.value = self.name

        self.observe(up, names=["text", "name"])

        return W.HBox([
            name,
            text,
        ])


class Cell(Node):
    cell_type = T.Unicode().tag(sync=True)
    metadata = T.Dict().tag(sync=True)
    source = T.Unicode("").tag(sync=True)

    @classmethod
    def from_node(cls, node):
        cell_types = dict(
            markdown=Markdown,
            code=Code,
            raw=Raw
        )

        return cell_types[node.cell_type](**node)


class Code(Cell):
    outputs = T.Tuple([]).tag(sync=True, **W.widget_serialization)
    execution_count = T.Integer(0, allow_none=True).tag(sync=True)

    def __init__(self, *args, **kwargs):
        outputs = kwargs.get("outputs", [])

        if outputs:
            kwargs["outputs"] = [
                Output.from_node(o)
                for o in outputs
            ]

        super(Code, self).__init__(*args, **kwargs)


class Raw(Cell):
    pass


class Markdown(Cell):
    pass


class NBFormat(Node):
    metadata = T.Dict().tag(sync=True)
    cells = T.Tuple().tag(sync=True, **W.widget_serialization)
    nbformat = T.Integer(4).tag(sync=True)
    nbformat_minor = T.Integer(2).tag(sync=True)

    _node = T.Instance(NotebookNode, allow_none=True)
    node = T.Instance(NotebookNode, allow_none=True)

    def __init__(self, node=None, *args, **kwargs):
        node = node or new_notebook()
        kwargs["_node"] = node
        super(NBFormat, self).__init__(*args, **kwargs)

        self.observe(self._on_node, names=("_node", "node"))

    def _on_node(self, change=None):
        n = self.node or self._node
        self.metadata = n.metadata
        self.cells = list(map(Cell.from_node, n.cells))
        self.nbformat = n.nbformat
        self.nbformat_minor = n.nbformat_minor
