from pprint import pprint
import traceback
import uuid
from pathlib import Path

from tornado.ioloop import IOLoop

import traitlets as T
from nbformat.v4 import new_notebook, writes
from jupyter_client.manager import start_new_kernel

import ipywidgets as W

from .utils import save_notebook

class DefaultKernelView(W.HBox):
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
        shutdown.layout.max_width = \
            rerun.layout.max_width = \
            save.layout.max_width = "3em"
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
            file_name,
            save,
            progress,
            rerun,
            widgets,
            shutdown,
        ]


class Kernel(W.Widget):
    execution_state = T.Unicode(allow_none=True).tag(sync=True)
    name = T.Unicode("python3").tag(sync=True)
    stdout = T.Tuple([]).tag(sync=True)
    stderr = T.Tuple([]).tag(sync=True)
    progress = T.Float(0).tag(sync=True)
    file_name = T.Unicode(allow_none=True).tag(sync=True)

    widgets = T.Tuple([]).tag(sync=True, **W.widget_serialization)

    last_cells = T.Tuple([]).tag(sync=True)

    _view_klass = DefaultKernelView

    def __init__(self, *args, **kwargs):
        super(Kernel, self).__init__(*args, **kwargs)
        self._kernel_client = None
        self._kernel_manager = None

    def save(self):
        if not self.last_cells:
            return
        if not self.file_name:
            self.file_name = str(uuid.uuid4()).split("-")[0]
        save_notebook(self.file_name, cells=self.last_cells)

    def shutdown(self):
        if self._kernel_manager:
            # print(f"---\nSHUTTING DOWN {self.name}\n---")
            self.widgets = []
            self.execution_state = "shutdown"
            self._kernel_manager.request_shutdown()
            self.execution_state = "down"
        self._kernel_client = None
        self._kernel_manager = None

    def run(self, cells=None, shutdown=False):
        cells = cells or self.last_cells or []
        self.last_cells = cells or []

        def _run():
            self.progress = 0
            if self._kernel_client is None:
                # print(f"---\nSTARTING {self.name}\n---")
                (
                    self._kernel_manager,
                    self._kernel_client
                ) = start_new_kernel(kernel_name=self.name)
            try:
                for i, cell in enumerate(cells):
                    self.progress = len(cells) / (i + 1)
                    self.run_one(cell)
            except Exception as err:
                print(f"ERROR {self.name} {err}")
                print(traceback.format_exc())
            finally:
                if shutdown:
                    self.shutdown()
        IOLoop.instance().add_callback(_run)
        return self

    def rerun(self):
        self.shutdown()
        self.run(cells=self.last_cells, shutdown=False)
        return self

    def view(self, view_klass=None):
        return (view_klass or self._view_klass)(kernel=self)

    def run_one(self, cell):
        def _print(msg):
            msg_type = msg['header']['msg_type']

            handler = getattr(self, "on_msg_{}".format(msg_type), None)

            if handler is not None:
                handler(msg, cell, msg["content"])
            else:
                print(f"UNHANDLED MSG TYPE: {msg_type}\n---")
                pprint(msg)
                print("---\n")
        return self._kernel_client.execute_interactive(
            cell.source,
            output_hook=_print
        )

    def on_msg_stream(self, msg, cell, content):
        if content["name"] == "stdout":
            self.stdout += content["text"],
        elif content["name"] == "stderr":
            self.stderr += content["text"],
        else:
            print(f"UNHANDLED STREAM {content.name}", msg)

    def on_msg_execute_result(self, msg, cell, content):
        cell.outputs += [{
            "data": content["data"],
            "output_type": "execute_result",
            "metadata": {}
        }]

    def on_msg_display_data(self, msg, cell, content):
        cell.outputs += [{
            "data": content["data"],
            "output_type": "display_data",
            "metadata": {}
        }]

    def on_msg_status(self, msg, cell, content):
        self.execution_state = content["execution_state"]

    def on_msg_execute_input(self, msg, cell, content):
        pass

    def on_msg_comm_open(self, msg, cell, content):
        comm_id = content["comm_id"]
        state, buffer_paths, buffers = W.widgets.widget._remove_buffers(
            content["data"]["state"])

        comm = W.widgets.widget.Comm(
            comm_id=comm_id,
            target_name='jupyter.widget',
            data={'state': state, 'buffer_paths': buffer_paths},
            buffers=buffers,
            metadata={'version': W._version.__protocol_version__}
        )
        W.Widget.handle_comm_opened(comm, msg)
        widget = W.Widget.widgets[comm_id]

        @widget.observe
        def _(change):
            if self._kernel_client is None:
                return

            update_msg = self._kernel_client.session.msg("comm_msg", {
                "comm_id": widget.comm.comm_id,
                "data": {
                    "method": "update",
                    "state": {
                        change["name"]: change["new"]
                    },
                    "buffer_paths": []
                }
            })

            def _send():
                self._kernel_client.shell_channel.send(update_msg)

            IOLoop.instance().add_callback(_send)

        self.widgets += (widget,)

    def on_msg_comm_msg(self, msg, cell, content):
        method = content.get("data", {}).get("method")
        if method == "update":
            # print("UPDATE", content["data"]["state"])
            for widget in self.widgets:
                if widget.comm.comm_id == content["comm_id"]:
                    for k, v in content["data"]["state"].items():
                        setattr(widget, k, v)

        else:
            print(f"UNKNOWN METHOD {method}\n---")
            pprint(msg)
            print("---")

    def on_msg_error(self, msg, cell, content):
        print(f"ERROR\n---")
        pprint(msg)
