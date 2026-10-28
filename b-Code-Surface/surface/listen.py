"""监听 Solid Edge 的命令、环境和选择事件，逐行写成 JSONL。

只订阅、不调用命令：用户真实建模时开着它，摸出实际用到的指令切面，以及“选中什么 →
接着执行哪条命令”的序列。命令标题从 extract 导出的 data/commands.json 查，查不到就只记 Id。
事件回调运行在本进程的 STA 上，主循环负责泵消息。
"""

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pythoncom
import win32com.client
from win32com.client import gencache

DATA = Path(__file__).resolve().parents[1] / "data"
FRAMEWORK_TYPELIB = ("{8A7EFA3A-F000-11D1-BDFC-080036B4D502}", 0, 1, 0)
MAX_SELECTION_ITEMS = 8


class _Source:
    """ApplicationEvents/DocumentEvents 取出来是裸 IUnknown，WithEvents 认不出类型；
    makepy 事件类只要求传入对象带 _oleobj_，这里包一层直接挂连接点。"""

    def __init__(self, unknown):
        self._oleobj_ = getattr(unknown, "_oleobj_", unknown)


def connect(source, events_class, handler_class, **attrs):
    sink_class = type(handler_class.__name__ + "Sink", (handler_class, events_class), attrs)
    return sink_class(_Source(source))


def load_captions(path):
    if not path.exists():
        return {}
    surface = json.loads(path.read_text(encoding="utf-8"))
    return {(r["env"], r["id"]): r["caption"] for r in surface["commands"]}


class Recorder:
    def __init__(self, framework, app, out, captions, echo):
        self.framework = framework
        self.app = app
        self.out = out
        self.captions = captions
        self.echo = echo
        self.document_sink = None

    def environment(self):
        try:
            return self.app.ActiveEnvironment
        except pythoncom.com_error:
            return None

    def write(self, event, **fields):
        row = {"t": round(time.time(), 3), "event": event, "env": self.environment(), **fields}
        self.out.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.out.flush()
        if self.echo:
            caption = self.captions.get((row["env"], fields.get("id")), "")
            detail = {k: v for k, v in fields.items() if k != "id"}
            print(f"{event:14s} {row['env'] or '-':14s} {fields.get('id', ''):>6} {caption} {detail or ''}", flush=True)

    def attach_document(self):
        """把选择事件挂到当前活动文档；切换文档时重挂。"""
        if self.document_sink is not None:
            self.document_sink.close()
            self.document_sink = None
        try:
            document = self.app.ActiveDocument
        except pythoncom.com_error:
            return
        if document is None:
            return
        self.document_sink = connect(
            document.DocumentEvents, self.framework.DISEDocumentEvents, DocumentHandler,
            recorder=self, document=document,
        )

    def selection(self, select_set):
        count = select_set.Count
        types = []
        items = []
        for i in range(1, min(count, MAX_SELECTION_ITEMS) + 1):
            item = select_set.Item(i)
            types.append(_read(lambda: int(item.Type)))
            items.append(describe(item))
        return {"count": count, "types": types, "items": items}


def _read(getter):
    try:
        return getter()
    except (pythoncom.com_error, AttributeError, TypeError):
        return None


def describe(item):
    """面/边带几何类型（GNTTypePropertyConstants 码）和尺寸，状态序列化要用。"""
    info = {"type": _read(lambda: int(item.Type))}
    geometry = _read(lambda: item.Geometry)
    if geometry is not None:
        info["geom"] = _read(lambda: int(geometry.Type))
        radius = _read(lambda: float(geometry.Radius))
        if radius is not None:
            info["radius_mm"] = round(radius * 1000, 3)
    area = _read(lambda: float(item.Area))
    if area is not None:
        info["area_mm2"] = round(area * 1e6, 2)
    return info


class ApplicationHandler:
    recorder = None

    def OnBeforeCommandRun(self, theCommandID):
        self.recorder.write("before_command", id=int(theCommandID))

    def OnAfterCommandRun(self, theCommandID):
        self.recorder.write("after_command", id=int(theCommandID))

    def OnAfterEnvironmentActivate(self, theEnvironment):
        self.recorder.write("environment")

    def OnAfterActiveDocumentChange(self, theDocument):
        self.recorder.attach_document()
        self.recorder.write("document")


class DocumentHandler:
    recorder = None
    document = None

    def OnSelectSetChanged(self, SelectSet):
        select_set = win32com.client.Dispatch(SelectSet) if SelectSet is not None else self.document.SelectSet
        self.recorder.write("selection", **self.recorder.selection(select_set))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, help="缺省为 data/events-<日期时间>.jsonl")
    parser.add_argument("--quiet", action="store_true", help="不在终端回显事件")
    args = parser.parse_args(argv)

    out_path = args.out or DATA / f"events-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    framework = gencache.EnsureModule(*FRAMEWORK_TYPELIB)
    app = win32com.client.GetActiveObject("SolidEdge.Application")
    with out_path.open("a", encoding="utf-8") as out:
        recorder = Recorder(framework, app, out, load_captions(DATA / "commands.json"), not args.quiet)
        app_sink = connect(app.ApplicationEvents, framework.DISEApplicationEvents, ApplicationHandler, recorder=recorder)
        recorder.attach_document()
        recorder.write("start", selection=bool(recorder.document_sink))
        print(f"listening -> {out_path}  (Ctrl+C 结束)", flush=True)
        try:
            while True:
                pythoncom.PumpWaitingMessages()
                time.sleep(0.01)
        except KeyboardInterrupt:
            recorder.write("stop")
    return 0


if __name__ == "__main__":
    sys.exit(main())
