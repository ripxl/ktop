import traitlets as T
import ipywidgets as W


class DefaultKernelView(W.VBox):
    def __init__(self, *args, **kwargs):
        kernel = kwargs.pop("kernel")

        super(DefaultKernelView, self).__init__(*args, **kwargs)

        progress = W.FloatProgress(min=0.0, max=1.0)
        widgets = W.VBox()
        shutdown = W.Button(icon="trash")
        rerun = W.Button(icon="play")
        save = W.Button(icon="floppy-o")
        file_name = W.Text(description="📓", placeholder="Notebook Name")

        # style
        for btn in [shutdown, save, rerun]:
            btn.layout.max_width = "3em"
        widgets.layout.flex = "1"

        # events
        shutdown.on_click(lambda *x: kernel.shutdown())
        rerun.on_click(lambda *x: kernel.rerun())
        save.on_click(lambda *x: kernel.save())

        # links
        T.dlink((kernel, "execution_state"), (progress, "description"))
        T.dlink((kernel, "progress"), (progress, "value"))
        T.dlink((kernel, "file_name"), (file_name, "value"))
        T.dlink((kernel, "widgets"), (widgets, "children"),
                lambda widgets: [
                    w for w in widgets
                    if "layout" in w.trait_names()])

        self.children = [
            W.HBox([
                file_name,
                save,
                progress,
                rerun,
                shutdown,
            ]),
            widgets,
        ]


class DefaultNotebookView(W.HBox):
    def __init__(self, *args, **kwargs):
        notebook = kwargs.pop("notebook")

        super(DefaultNotebookView, self).__init__(*args, **kwargs)

        name = W.Text()
        kernels = W.VBox()
        cells = W.VBox()
        save = W.Button(icon="floppy-o")
        load = W.Button(icon="refresh")

        for btn in [save, load]:
            btn.layout.max_width = "3em"

        # events

        save.on_click(lambda *x: notebook.save())
        load.on_click(lambda *x: notebook.load())

        def _make_children(ipynb):
            return [
                W.HTML("<code>\n{}\n</code>".format(
                    "\n".join(cell.get("source", []))))
                for cell in ipynb["cells"]
            ]

        T.link((notebook, "file_name"), (name, "value"))
        T.dlink((notebook, "kernels"), (kernels, "children"),
                lambda children: [c.view() for c in children])
        T.dlink((notebook, "ipynb"), (cells, "children"), _make_children)

        left = W.VBox([
            W.HBox([
                name,
                save,
                load,
            ]),
            cells,
        ])

        right = W.VBox([
            kernels,
        ])

        left.layout.flex = "1"
        right.layout.flex = "1.6"

        self.children = [
            left,
            right,
        ]
