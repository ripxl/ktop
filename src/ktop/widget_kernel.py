from pprint import pformat
import traceback
import uuid
import asyncio
import multiprocessing

from concurrent.futures import ThreadPoolExecutor

from tornado.ioloop import IOLoop
from tornado.gen import coroutine
from tornado.concurrent import run_on_executor
from tornado.queues import Queue

from zmq.eventloop.zmqstream import ZMQStream

import traitlets as T
from jupyter_client.ioloop.manager import IOLoopKernelManager

import ipywidgets as W

from .utils import save_notebook

from .widget_dashboard import DefaultKernelView
from . import widget_nbformat as NB

from_json = W.widget_serialization["from_json"]


class Kernel(W.Widget):
    """ An evented kernel
    """
    execution_state = T.Unicode(allow_none=True).tag(sync=True)
    name = T.Unicode("python3").tag(sync=True)
    progress = T.Float(0.0).tag(sync=True)
    file_name = T.Unicode(allow_none=True).tag(sync=True)
    nbformat = T.Instance(NB.NBFormat).tag(sync=True, **W.widget_serialization)

    widgets = T.Tuple([]).tag(sync=True, **W.widget_serialization)

    executor = ThreadPoolExecutor(multiprocessing.cpu_count())

    _view_klass = DefaultKernelView

    def __init__(self, *args, **kwargs):
        kwargs["nbformat"] = kwargs.get("nbformat") or NB.NBFormat()
        super(Kernel, self).__init__(*args, **kwargs)
        self._kernel_client = None
        self._kernel_manager = None
        self._queue = Queue()
        self._listening = False

    def shutdown(self):
        if self._kernel_manager:
            self.widgets = []
            self.execution_state = "shutdown"
            self._kernel_manager.request_shutdown()
            self._kernel_manager.cleanup()
            self.execution_state = "down"
        self._kernel_client = None
        self._kernel_manager = None

    def run(self, cells, shutdown=None):
        self.nbformat.cells = cells

        @coroutine
        def _run():
            self.progress = 0.0
            if shutdown:
                self.shutdown()
                while self._queue.qsize():
                    yield self._queue.get()

            for cell in cells:
                yield self._queue.put(cell)

            if self._kernel_client is None:
                yield self.client()

            if not self._listening:
                IOLoop.instance().add_callback(self.listen)

            try:
                while self._queue.qsize():
                    self._current_cell = yield self._queue.get()
                    yield self.run_one(self._current_cell)
            except Exception as err:
                print(f"ERROR {self.name} {err}")
                print(traceback.format_exc())
            finally:
                if shutdown:
                    self.shutdown()
                    return

        IOLoop.instance().add_callback(_run)
        return self

    @coroutine
    def listen(self):
        channels = [
            self._kernel_client.iopub_channel,
            self._kernel_client.shell_channel,
        ]
        for channel in channels:
            self._listen_one(channel)
        self._listening = True

    def _listen_one(self, channel):
        stream = ZMQStream(channel.socket)
        handler = self._make_handler()

        @stream.on_recv
        def _listen(raw):
            try:
                ident, smsg = channel.session.feed_identities(raw)
                msg = channel.session.deserialize(smsg)
                IOLoop.instance().add_callback(handler, msg)
            except Exception as err:
                pass
                # print("MSGERROR", err)
                # print(traceback.format_exc())

    @run_on_executor
    def client(self):
        km = self._kernel_manager
        asyncio.set_event_loop(asyncio.new_event_loop())
        if km is None:
            km = IOLoopKernelManager(
                kernel_name=self.name, loop=IOLoop.instance())
            self._kernel_manager = km

        km.start_kernel()
        kc = self._kernel_manager.client()
        self._kernel_client = kc

        kc.start_channels()

        try:
            kc.wait_for_ready(timeout=5)
        except RuntimeError:
            kc.stop_channels()
            km.shutdown_kernel()
            raise

    def rerun(self, shutdown=False):
        self.shutdown()
        self.run(shutdown=shutdown)
        return self

    def view(self, view_klass=None):
        return (view_klass or self._view_klass)(kernel=self)

    def _make_handler(self, cell=None):
        def _on_msg(msg):
            msg_type = msg['header']['msg_type']
            print("MSG", msg_type)
            handler = getattr(self, "on_msg_{}".format(msg_type), None)

            if handler is not None:
                handler(msg, cell or self._current_cell, msg["content"])
            else:
                self.log.warn(f"UNHANDLED MSG TYPE: {msg_type}\n---\n%s\n%s",
                              pformat(msg),
                              f"You should implement on_msg_{msg_type}")

        return _on_msg

    @run_on_executor
    def run_one(self, cell):
        msg_id = self._kernel_client.execute(cell.source)
        return msg_id

    def on_msg_stream(self, msg, cell, content):
        cell.outputs += (NB.Stream(output_type="stream", **content), )

    def on_msg_execute_result(self, msg, cell, content):
        cell.outputs += (NB.ExecuteResult(
            output_type="execute_result", **content), )

    def on_msg_display_data(self, msg, cell, content):
        print("CONTENT", content)
        cell.outputs += (NB.DisplayData(output_type="display_data",
                                        **content), )

    def on_msg_error(self, msg, cell, content):
        cell.outputs += (NB.Error(output_type="error", **content), )

    def on_msg_status(self, msg, cell, content):
        self.execution_state = content["execution_state"]

    def on_msg_execute_input(self, msg, cell, content):
        pass

    def on_msg_execute_reply(self, msg, cell, content):
        pass

    def on_msg_comm_reply(self, msg, cell, content):
        pass

    def on_msg_comm_open(self, msg, cell, content):
        comm_id = content["comm_id"]
        state, buffer_paths, buffers = W.widgets.widget._remove_buffers(
            content["data"]["state"])

        as_json = from_json(state, state)
        print("AS_JSON")
        print(as_json)

        def _sub_widget(obj):
            if isinstance(obj, dict):
                return {k: _sub_widget(c) for k, c in obj.items()}
            elif isinstance(obj, str):
                print("OBJ", obj)
                if obj.startswith("IPY_MODEL_"):
                    print("OBJ_ID", obj[10:])
                    obj_id = obj.split("_")[2]
                    subwidget = W.Widget.widgets.get(obj_id)
                    self.widgets += (subwidget,)
                    return subwidget
                return obj
            elif isinstance(obj, list):
                return [_sub_widget(c) for c in obj]
            else:
                return obj

        # so for bqplot, there are these deep things
        subbed = _sub_widget(state)
        print("SUBBED", subbed)

        comm = W.widgets.widget.Comm(
            comm_id=comm_id,
            target_name='jupyter.widget',
            data={'state': state,
                  'buffer_paths': buffer_paths},
            buffers=buffers,
            metadata={'version': W._version.__protocol_version__})
        W.Widget.handle_comm_opened(comm, msg)
        widget = W.Widget.widgets[comm_id]

        @widget.observe
        def _(change):
            if self._kernel_client is None:
                return

            update_msg = self._kernel_client.session.msg(
                "comm_msg", {
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
        self.widgets += (widget, )

    def on_msg_comm_msg(self, msg, cell, content):
        method = content.get("data", {}).get("method")
        if method == "update":
            for widget in self.widgets:
                if widget.comm.comm_id == content["comm_id"]:
                    for k, v in content["data"]["state"].items():
                        setattr(widget, k, v)

        else:
            self.log.warning(f"UNKNOWN METHOD {method}\n---\n%s", pformat(msg))

    def on_msg_shutdown_reply(self, msg, cell, content):
        self.execution_state = "shutdown"
