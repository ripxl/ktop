from pprint import pprint
import traceback
import uuid
import multiprocessing


from concurrent.futures import ThreadPoolExecutor

from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor

import traitlets as T
from jupyter_client.manager import start_new_kernel
from jupyter_client.ioloop.manager import IOLoopKernelManager

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
    progress = T.Float(0.0).tag(sync=True)
    file_name = T.Unicode(allow_none=True).tag(sync=True)
    ipynb = T.Dict(allow_none=True).tag(sync=True)

    widgets = T.Tuple([]).tag(sync=True, **W.widget_serialization)

    _view_klass = DefaultKernelView

    executor = ThreadPoolExecutor(multiprocessing.cpu_count())

    def __init__(self, *args, **kwargs):
        super(Kernel, self).__init__(*args, **kwargs)
        self._kernel_client = None
        self._kernel_manager = None

    def save(self):
        if not self.ipynb:
            return
        if not self.file_name:
            self.file_name = str(uuid.uuid4()).split("-")[0]
        save_notebook(self.file_name, self.ipynb)

    def shutdown(self):
        if self._kernel_manager:
            # print(f"---\nSHUTTING DOWN {self.name}\n---")
            self.widgets = []
            self.execution_state = "shutdown"
            self._kernel_manager.request_shutdown()
            self._kernel_manager.cleanup()
            self.execution_state = "down"
        self._kernel_client = None
        self._kernel_manager = None

    def run(self, cell_nodes=None, shutdown=False):
        cell_nodes = cell_nodes or self.ipynb["cells"] or []

        @coroutine
        def _run():
            self.progress = 0.0
            if shutdown:
                self.shutdown()
            if self._kernel_client is None:
                yield self.client()
            try:
                for i, cell in enumerate(cell_nodes):
                    progress = len(cell_nodes) / (i + 1)
                    yield self.run_one(cell, progress=progress)
            except Exception as err:
                print(f"ERROR {self.name} {err}")
                print(traceback.format_exc())
            finally:
                if shutdown:
                    self.shutdown()

        IOLoop.instance().add_callback(_run)
        return self

    @run_on_executor
    def client(self):
        # (
        #     self._kernel_manager,
        #     self._kernel_client
        # ) = start_new_kernel(kernel_name=self.name)
        km = IOLoopKernelManager(kernel_name=self.name)
        km.start_kernel()
        kc = km.client()
        kc.start_channels()
        try:
            kc.wait_for_ready(timeout=5)
        except RuntimeError:
            kc.stop_channels()
            km.shutdown_kernel()
            raise
        self._kernel_manager = km
        self._kernel_client = kc

    def rerun(self, shutdown=False):
        self.shutdown()
        self.run(shutdown=shutdown)
        return self

    def view(self, view_klass=None):
        return (view_klass or self._view_klass)(kernel=self)

    @run_on_executor
    def run_one(self, cell, progress=None):
        def _on_msg(msg):
            msg_type = msg['header']['msg_type']

            handler = getattr(self, "on_msg_{}".format(msg_type), None)

            if handler is not None:
                handler(msg, cell, msg["content"])
            else:
                print(f"UNHANDLED MSG TYPE: {msg_type}\n---")
                pprint(msg)
                print("---\n")
        reply = self._kernel_client.execute_interactive(
            "\n".join(cell["source"]),
            output_hook=_on_msg
        )

        if progress:
            self.progress = progress
        return reply

    def on_msg_stream(self, msg, cell, content):
        if content["name"] == "stdout":
            self.stdout += content["text"],
        elif content["name"] == "stderr":
            self.stderr += content["text"],
        else:
            print(f"UNHANDLED STREAM {content.name}", msg)

    def on_msg_execute_result(self, msg, cell, content):
        cell["outputs"] += [{
            "data": content["data"],
            "output_type": "execute_result",
            "metadata": {}
        }]

    def on_msg_display_data(self, msg, cell, content):
        cell["outputs"] += [{
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
