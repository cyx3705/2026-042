"""从运行中的 Solid Edge 导出扁平指令表。

只读：遍历 Application.Environments，每个环境的 CommandCategories 下是 CommandInfo
（Id、Caption、Tooltip、Description、BuiltIn）。同一命令会出现在多个分类里（如快速访问
工具栏），按 (环境, Id) 去重，分类记成列表。不调用 Customization，不改界面。
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import win32com.client

DEFAULT_OUT = Path(__file__).resolve().parents[1] / "data" / "commands.json"


def _text(value):
    return (value or "").strip()


def extract_environment(env):
    commands = {}
    categories = env.CommandCategories
    for i in range(1, categories.Count + 1):
        category = categories.Item(i)
        category_name = _text(category.Caption)
        for j in range(1, category.Count + 1):
            info = category.Item(j)
            command_id = int(info.Id)
            row = commands.get(command_id)
            if row is None:
                row = commands[command_id] = {
                    "id": command_id,
                    "caption": _text(info.Caption),
                    "tooltip": _text(info.Tooltip),
                    "description": _text(info.Description),
                    "builtIn": bool(info.BuiltIn),
                    "categories": [],
                }
            if category_name not in row["categories"]:
                row["categories"].append(category_name)
    return sorted(commands.values(), key=lambda r: r["id"])


def extract(app, only=None):
    environments = []
    commands = []
    envs = app.Environments
    for i in range(1, envs.Count + 1):
        env = envs.Item(i)
        name = env.Name
        if only and name not in only:
            continue
        entry = {"name": name, "caption": _text(env.Caption), "catid": env.CATID}
        try:
            rows = extract_environment(env)
        except Exception as error:  # 个别环境未加载时 COM 会拒绝，记下原因继续
            entry["error"] = str(error)
            rows = []
        entry["commandCount"] = len(rows)
        environments.append(entry)
        commands.extend({"env": name, **row} for row in rows)
    return {
        "source": {"application": "Solid Edge", "version": app.Version},
        "extractedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "environments": environments,
        "commands": commands,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--env", action="append", help="只导出指定环境，可重复；缺省导出全部")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)

    app = win32com.client.GetActiveObject("SolidEdge.Application")
    surface = extract(app, set(args.env) if args.env else None)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(surface, ensure_ascii=False, indent=1), encoding="utf-8")

    for env in surface["environments"]:
        note = f"  ! {env['error']}" if "error" in env else ""
        print(f"{env['name']:26s} {env['commandCount']:5d}{note}")
    print(f"total {len(surface['commands'])} -> {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
