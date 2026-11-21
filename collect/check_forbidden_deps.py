#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""禁止依赖检查：shapely / rtree 永不许进运行时（muse-000146 Phase 1a 第 4 片 · 第 10 项）。

架构裁决（2026-10-18，二仓 requirements.txt）：
  「shapely / rtree 明确禁止 —— 空间索引一律复用引擎内自带的网格索引 + point_in_rings()」
定案文档：docs/DEPENDENCY-VERDICT-20261122.md（三仓）。

判据（唯一，禁再写一套）：
  ① 仓库内任何 `*.py` 出现 `import shapely` / `from shapely…` / `import rtree` / `from rtree…`
     → 报错（rc=1）。含 `import shapely.geometry`、`from shapely.ops import …` 等变体。
  ② `requirements*.txt` / `pyproject.toml` / `setup.cfg` / `environment*.yml` 里
     把 shapely / rtree 列为**依赖**（非注释行）→ 报错（rc=1）。
     只提「禁止」的注释行**不算违规** —— 二仓 requirements.txt 里那段裁决注释必须原样留着。
  ③ 注释 / 文档 / 字符串里的提及一律放过（本仓本来就有「无 shapely 依赖」这类说明）。

为什么用「行首去注释后再看包名」而不是全文 grep：
  全文 grep 会把裁决注释本身判红（一句话写清「禁止 shapely」就违规 → 荒谬），
  于是大家会删掉注释而不是删掉依赖。

用法：
  python3 collect/check_forbidden_deps.py                     # 检查本仓
  python3 collect/check_forbidden_deps.py --root <repo> ...   # 检查多个仓（只读）
  python3 collect/check_forbidden_deps.py --json

退出码：0 = 无违规；1 = 有违规；2 = 路径不存在。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BANNED = ("shapely", "rtree")

# import shapely / from shapely.geometry import ... / import rtree as rt
PY_IMPORT = re.compile(r"^\s*(?:import|from)\s+(%s)\b" % "|".join(BANNED))
DEP_FILES = ("requirements*.txt", "pyproject.toml", "setup.cfg", "setup.py",
             "environment*.yml", "environment*.yaml", "Pipfile")
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", "build", "dist"}


def _strip_comment(line: str) -> str:
    """去掉行内注释（# 之后），保留代码部分。"""
    i = line.find("#")
    return line if i < 0 else line[:i]


def scan_py(root: Path) -> list[dict]:
    bad: list[dict] = []
    for p in root.rglob("*.py"):
        if SKIP_DIRS & set(p.parts):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for i, line in enumerate(text.splitlines(), 1):
            if PY_IMPORT.match(_strip_comment(line)):
                bad.append({"file": str(p.relative_to(root)), "line": i,
                            "kind": "import", "text": line.strip()[:120]})
    return bad


def scan_deps(root: Path) -> list[dict]:
    bad: list[dict] = []
    for pat in DEP_FILES:
        for p in root.rglob(pat):
            if SKIP_DIRS & set(p.parts):
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                code = _strip_comment(line).strip()
                if not code:
                    continue                      # 整行注释（例如二仓那段裁决）放过
                low = code.lower()
                hit = [b for b in BANNED if re.search(r"(^|[^a-z0-9_.-])%s([^a-z0-9_-]|$)" % b, low)]
                if hit:
                    bad.append({"file": str(p.relative_to(root)), "line": i,
                                "kind": "dependency", "text": line.strip()[:120],
                                "hits": hit})
    return bad


def scan(root: Path) -> list[dict]:
    return scan_py(root) + scan_deps(root)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", action="append", default=[])
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    roots = [Path(r).resolve() for r in a.root] or [Path(__file__).resolve().parents[1]]

    report = {}
    total = 0
    for root in roots:
        if not root.is_dir():
            print("路径不存在：%s" % root, file=sys.stderr)
            return 2
        bad = scan(root)
        report[str(root)] = bad
        total += len(bad)

    if a.json:
        print(json.dumps({"violations": total, "by_root": report}, ensure_ascii=False, indent=1))
    else:
        for root, bad in report.items():
            print("== %s ==" % root)
            if not bad:
                print("  ✅ 无 shapely / rtree（import 与依赖清单均干净）")
                continue
            for b in bad:
                print("  ❌ %s:%d  [%s] %s" % (b["file"], b["line"], b["kind"], b["text"]))
    if total:
        print("\n判定：❌ %d 处违规 —— shapely / rtree 永不用作运行时依赖"
              "（见 docs/DEPENDENCY-VERDICT-20261122.md）" % total)
        return 1
    print("\n判定：✅ 零违规（%d 个仓已查；注释里的「禁止 shapely」不算违规）" % len(roots))
    return 0


if __name__ == "__main__":
    sys.exit(main())
