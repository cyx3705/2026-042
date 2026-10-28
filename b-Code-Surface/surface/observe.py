"""把 listen 写的事件日志整理成实际用到的指令切面。

before/after 成对还原出每次命令执行；命令标题先查 data/commands.json，查不到再查下面
实测补录的隐式命令；同时记下每条命令执行前最近一次的选择集，得到“选中什么 → 执行什么”。
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
SELECT_TOOL = 45000

# 导出表里没有、靠监听才看到的命令（环境无关）。Id → 标题，来源写在注释里。
IMPLICIT = {
    10311: "方向盘移动（点方向盘主轴后输入距离，2026-10-28 DMPart 实测）",
    40212: "删除（Delete 键；constant.tlb 里是 PartEditDelete）",
}

CONSTANT_TYPELIB = r"C:\Program Files\Siemens\Solid Edge 2020\Program\constant.tlb"
TYPE_ENUMS = ("GNTTypePropertyConstants", "ObjectType", "FeatureTypeConstants")


def load_type_names():
    """选择集 Type 与几何 Type 码 → 名称，直接读 constant.tlb，去掉 ig 前缀。"""
    import pythoncom

    library = pythoncom.LoadTypeLib(CONSTANT_TYPELIB)
    names = {}
    for i in range(library.GetTypeInfoCount()):
        if library.GetDocumentation(i)[0] not in TYPE_ENUMS:
            continue
        info = library.GetTypeInfo(i)
        for j in range(info.GetTypeAttr().cVars):
            var = info.GetVarDesc(j)
            names.setdefault(var.value, info.GetDocumentation(var.memid)[0].removeprefix("ig"))
    return names


TYPE_NAMES = {}


def load_captions(path):
    if not path.exists():
        return {}
    surface = json.loads(path.read_text(encoding="utf-8"))
    return {(r["env"], r["id"]): r["caption"] for r in surface["commands"]}


def caption(captions, env, command_id):
    if (env, command_id) in captions:
        return captions[(env, command_id)]
    return IMPLICIT.get(command_id, "?")


def selection_label(event):
    if not event or not event.get("count"):
        return "无选择"
    items = event.get("items") or [{"type": t} for t in event["types"]]
    names = []
    for item in items:
        name = TYPE_NAMES.get(item.get("type"), str(item.get("type")))
        if item.get("geom") is not None:
            name += ":" + TYPE_NAMES.get(item["geom"], str(item["geom"]))
        names.append(name)
    return f"{event['count']}×" + "/".join(sorted(set(names)))


def runs(events):
    """按 before_command 切出命令执行；选择工具本身不算一次操作。"""
    last_selection = None
    for event in events:
        if event["event"] == "selection":
            last_selection = event
        elif event["event"] == "before_command" and event["id"] != SELECT_TOOL:
            yield event["env"], event["id"], selection_label(last_selection)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("logs", nargs="*", type=Path, help="缺省为 data/events-*.jsonl")
    args = parser.parse_args(argv)

    TYPE_NAMES.update(load_type_names())
    paths = args.logs or sorted(DATA.glob("events-*.jsonl"))
    captions = load_captions(DATA / "commands.json")
    events = [json.loads(line) for p in paths for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]

    commands = Counter()
    contexts = Counter()
    for env, command_id, selected in runs(events):
        commands[(env, command_id)] += 1
        contexts[(selected, env, command_id)] += 1

    print(f"{len(events)} events from {len(paths)} log(s)\n")
    print("命令                                           次数  来源")
    for (env, command_id), n in commands.most_common():
        source = "导出表" if (env, command_id) in captions else ("实测补录" if command_id in IMPLICIT else "未知")
        print(f"{env:8s} {command_id:>6} {caption(captions, env, command_id):28s} {n:4d}  {source}")
    print("\n选中什么 → 执行什么")
    for (selected, env, command_id), n in contexts.most_common():
        print(f"{selected:14s} → {caption(captions, env, command_id)} ×{n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
