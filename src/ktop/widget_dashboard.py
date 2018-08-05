import traitlets as T
import ipywidgets as W

from nbformat.v4 import new_code_cell
from . import widget_nbformat as NB


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
        cells = W.HBox()
        shutdown = W.Button(icon="trash")
        rerun = W.Button(icon="play")
        file_name = W.Text(placeholder="Notebook Name")

        # style
        sized(shutdown, rerun)
        widgets.layout.flex = "2"
        file_name.layout.width = "auto"

        # events
        shutdown.on_click(lambda *x: kernel.shutdown())
        rerun.on_click(lambda *x: kernel.run(kernel.nbformat.cells,
                                             shutdown=False))

        # links
        # T.dlink((kernel, "execution_state"), (progress, "description"))
        T.dlink((kernel, "file_name"), (file_name, "value"))
        T.dlink((kernel, "widgets"), (widgets, "children"),
                lambda widgets: [
                    w for w in widgets
                    if "layout" in w.trait_names()])
        T.dlink((kernel.nbformat, "cells"), (cells, "children"),
                lambda cells: [
                    DefaultCellOutputView(cell=cell, kernel=kernel)
                    for cell in cells
                ])

        self.children = [
            W.VBox([
                W.HBox([
                    rerun,
                    shutdown,
                ]),
                file_name,
            ]),
            W.VBox([
                widgets,
                cells,
            ]),
        ]


class DefaultCellOutputView(W.VBox):
    def __init__(self, *args, **kwargs):
        kernel = kwargs.pop("kernel")
        cell = kwargs.pop("cell")

        super(DefaultCellOutputView, self).__init__(*args, **kwargs)

        def _view(outputs):
            # print("OUTPUTS", outputs)
            views = [o.view() for o in outputs]
            # print("views", views)
            return views

        T.dlink((cell, "outputs"), (self, "children"), _view)


class DefaultCellView(W.VBox):
    source = T.Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        cell = kwargs.pop("cell")
        notebook = kwargs.pop("notebook")
        kwargs["source"] = cell.source

        super(DefaultCellView, self).__init__(*args, **kwargs)

        source = W.Textarea(cell.source)
        run = W.Button(icon="forward")

        # style
        sized(run)
        source.layout.width = "auto"

        @run.on_click
        def _run(x):
            self.source = cell.source = source.value
            list(notebook.run(
                 cells=[cell],
                 shutdown=False,
                 save=False))

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
        shutdown = W.Button(icon="trash")

        # style
        sized(save, load, add, shutdown)
        name.layout.flex = "1"
        name.layout.width = "auto"

        # events
        def _add():
            print("ADDD")
            notebook.nbformat.cells += (NB.Code(),)

        save.on_click(lambda *x: notebook.save())
        load.on_click(lambda *x: notebook.load())
        add.on_click(lambda *x: _add())

        @shutdown.on_click
        def _shutdown(*args):
            [k.shutdown() for k in notebook.kernels]
            notebook.kernels = []

        def _update(i, child):
            def _do(change):
                notebook.nbformat.cells[i].source = child.source
            return _do

        def _make_children(cell):
            children = [
                DefaultCellView(cell=cell, notebook=notebook)
                for cell in notebook.nbformat.cells
            ]

            for i, child in enumerate(children):
                child.observe(_update(i, child))
            return children

        T.link((notebook, "file_name"), (name, "value"))
        T.dlink((notebook, "kernels"), (kernels, "children"),
                lambda children: [c.view() for c in children])
        T.dlink((notebook.nbformat, "cells"), (cells, "children"),
                _make_children)

        top = W.HBox([
            W.VBox([
                W.HBox([
                    shutdown,
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
