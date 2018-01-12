import traitlets as T
import ipywidgets as W

from nbformat.v4 import new_code_cell


def sized(*btns):
    for btn in btns:
        btn.layout.max_width = btn.layout.min_width = "3em"


class DefaultKernelView(W.HBox):
    """ Show a kernel
    """
    def __init__(self, *args, **kwargs):
        kernel = kwargs.pop("kernel")

        super(DefaultKernelView, self).__init__(*args, **kwargs)

        widgets = W.HBox()
        shutdown = W.Button(icon="trash")
        rerun = W.Button(icon="play")
        save = W.Button(icon="floppy-o")
        file_name = W.Text(placeholder="Notebook Name")


        # style
        sized(shutdown, save, rerun)
        widgets.layout.flex = "2"
        file_name.layout.width = "auto"

        # events
        shutdown.on_click(lambda *x: kernel.shutdown())
        rerun.on_click(lambda *x: kernel.rerun())
        save.on_click(lambda *x: kernel.save())

        # links
        # T.dlink((kernel, "execution_state"), (progress, "description"))
        T.dlink((kernel, "file_name"), (file_name, "value"))
        T.dlink((kernel, "widgets"), (widgets, "children"),
                lambda widgets: [
                    w for w in widgets
                    if "layout" in w.trait_names()])

        self.children = [
            W.VBox([
                W.HBox([
                    save,
                    rerun,
                    shutdown,
                ]),
                file_name,
            ]),
            widgets,
        ]


class DefaultCellView(W.VBox):
    source = T.Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        cell = kwargs.pop("cell")
        notebook = kwargs.pop("notebook")
        kwargs["source"] = "\n".join(cell["source"])

        super(DefaultCellView, self).__init__(*args, **kwargs)

        source = W.Textarea(self.source)
        run = W.Button(icon="forward")

        # style
        sized(run)
        source.layout.width = "auto"

        @run.on_click
        def _run(x):
            list(notebook.run(
                 cells=[new_code_cell([self.source])],
                 shutdown=False,
                 save=False))

        T.link((self, "source"), (source, "value"))

        self.children = [
            W.HBox([run]),
            source,
        ]


class DefaultNotebookView(W.VBox):
    """ Show a Notebook and all of its kernels
    """

    def __init__(self, *args, **kwargs):
        notebook = kwargs.pop("notebook")

        super(DefaultNotebookView, self).__init__(*args, **kwargs)

        name = W.Text()
        kernels = W.VBox()
        cells = W.HBox()
        add = W.Button(icon="plus-square-o")
        save = W.Button(icon="floppy-o")
        load = W.Button(icon="refresh")

        # style
        sized(save, load, add)
        name.layout.flex = "1"
        name.layout.width = "auto"

        # events

        save.on_click(lambda *x: notebook.save())
        load.on_click(lambda *x: notebook.load())

        @add.on_click
        def _add(evt):
            notebook.notebook_node.cells += [new_code_cell()]
            notebook._to_ipynb()

        def _update(i, child):
            def _do(change):
                notebook.notebook_node.cells[i].source = \
                    child.source.strip().split("\n")

                notebook.ipynb["cells"][i]["source"] = child.source.split("\n")
            return _do

        def _make_children(ipynb):
            children = [
                DefaultCellView(cell=cell, notebook=notebook)
                for cell in ipynb["cells"]
            ]

            for i, child in enumerate(children):
                child.observe(_update(i, child))
            return children

        T.link((notebook, "file_name"), (name, "value"))
        T.dlink((notebook, "kernels"), (kernels, "children"),
                lambda children: [c.view() for c in children])
        T.dlink((notebook, "ipynb"), (cells, "children"), _make_children)

        top = W.HBox([
            W.VBox([
                W.HBox([
                    save,
                    load,
                    add,
                ]),
                name,
            ]),
            cells,
        ])

        bottom = W.VBox([
            kernels,
        ])

        top.layout.flex = "1"
        bottom.layout.flex = "4"

        self.children = [
            top,
            bottom,
        ]
