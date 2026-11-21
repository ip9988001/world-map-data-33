#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""公开仓「制品 / 缓存」泄密口检查（muse-000146 Phase 1a 第 3 片 · 第 9 项）。

背景（事实前提，不重复论证）：
  一仓 World-US-Map-Data、二仓 world-map-data-test、三仓 world-map-data-33、总仓 World-Map-Data
  **四个都是 public**。public 仓的 Artifact / Cache 出口 = 任何人可下载。
  → 含**行级**原始 / staging 数据的制品一律禁止出现在公开仓出口（定级 **S 级**）。

判据（唯一，不许各写一套）：
  S 级 path 标记（任一命中即 S 级，rc=1）：
    `.ndjson` / `.jsonl` / `.parquet`        行级数据文件本体（含 .ndjson.gz）
    `collect/out`                            采集产物桶（pilot 逐单元 .ndjson.gz 落这里）
    `staging` 目录                           中转行级数据
    `raw/` 目录                              原始行级数据
  只认 **path / key 里的字面 glob**，不猜内容、不看 job 名。

  `actions/cache`：key 或 path 覆盖到上述标记 → 同样 S 级（缓存比制品留得更久，更危险）。

  retention-days：非 S 级制品要求 ≤ `--max-retention`（默认 3，muse-000146 第 9 项「留存压到最小」）。
    默认只**告警**（不 rc=1），因为存量 workflow（collect-full.yml 的账本/文档类制品）还在 30/90 天
    过渡中，压留存要单开一单（该文件属 judgment-gate 判据文件，需外部 APPROVED review）。
    `--strict-retention` 时告警升级为 rc=1，供过渡完成后收紧门禁用。

用法：
  python3 collect/check_public_exports.py                     # 扫本仓 .github/workflows/**
  python3 collect/check_public_exports.py --root /path/repo    # 只读扫别的仓（不改）
  python3 collect/check_public_exports.py --strict-retention    # 留存超限也 rc=1
  python3 collect/check_public_exports.py --json                # 机器可读

退出码：0 = 无 S 级出口；1 = 有 S 级出口（或 strict 下留存超限）；2 = 目录不存在。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# S 级标记：命中即视为「行级原始 / staging 数据」出口
S_MARKERS = (
    ".ndjson",
    ".jsonl",
    ".parquet",
    "collect/out",
    "staging",
    "raw/",
)

# S 级豁免（写明白，不许悄悄加）：单个**具名文件**、且是单元清单/账本而不是行数据。
# 例：`collect/out/<layer>/_manifest.json`（单元清单，~KB 级），虽在 collect/out 桶里但不是行数据。
# 只豁免「无通配符 + 命中下列后缀」的 path；带 `*` 的通配（=
# 可能是整桶）一律不豁免。
S_EXEMPT_SUFFIX = ("_manifest.json",)

EXPORT_USES = re.compile(r"^\s*uses:\s*(actions/(upload-artifact|cache)[^\s@]*)@")
ANY_ARTIFACT_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*actions/(?:upload-artifact|cache)[^\s@]*@")
STEP_ITEM = re.compile(r"^\s*-\s")


def _flow_map(text: str) -> dict:
    """解析 `{ a: 1, b: x, c: y }` 行内 map（懂得跳过 ${{ }} 里的逗号）。"""
    s = text.strip()
    if "{" not in s or "}" not in s:
        return {}
    body = s[s.index("{") + 1: s.rindex("}")]
    parts, buf, depth = [], [], 0
    i = 0
    while i < len(body):
        two = body[i:i + 2]
        if two == "${":
            depth += 1
            buf.append(two)
            i += 2
            continue
        if two == "}}" and depth:
            depth -= 1
            buf.append(two)
            i += 2
            continue
        ch = body[i]
        if ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf))
    out = {}
    for p in parts:
        if ":" not in p:
            continue
        k, v = p.split(":", 1)
        out[k.strip()] = _strip_q(v)
    return out


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _strip_q(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1]
    return s


def _step_bounds(lines: list[str], i: int) -> tuple[int, int]:
    """返回包含第 i 行（uses 行）的 step 文本的行区间 [start, end)。

    step 可能以 `- uses:` 开头，也可能 `- name:` 在前、uses 在后（同缩进的兄弟键）——
    后者必须往回合 step 起点，否则 `with:` 块会被当成新 step 而漏掉 path（2026-11-22 实测 bug）。
    """
    ind = _indent(lines[i])
    start = i
    j = i
    while j >= 0:
        ln = lines[j]
        if ln.strip() and _indent(ln) < ind:
            start = j if STEP_ITEM.match(ln) else j + 1
            if STEP_ITEM.match(ln):
                break
            # 上级不是 step 项 → 继续往上找
            ind = _indent(ln)
        elif STEP_ITEM.match(ln) and _indent(ln) <= ind:
            start = j
            break
        j -= 1
    base = _indent(lines[start])
    end = len(lines)
    k = start + 1
    while k < len(lines):
        ln = lines[k]
        if ln.strip():
            if _indent(ln) < base:
                end = k
                break
            if STEP_ITEM.match(ln) and _indent(ln) <= base:
                end = k
                break
        k += 1
    return start, end


def parse_step(block: list[str]) -> dict:
    """从一段 step 文本里抠 uses / name / path / retention-days / key（含行内 flow map）。"""
    out = {"uses": "", "name": "", "paths": [], "retention": None, "key": ""}
    if not block:
        return out
    for ln in block:
        m = ANY_ARTIFACT_USES.match(ln)
        if m:
            out["uses"] = re.search(r"actions/[^\s@]+@", ln).group(0).rstrip("@")
            break
    base = _indent(block[0])
    i = 0
    while i < len(block):
        raw = block[i]
        s = raw.strip()
        ind = _indent(raw)
        flow = _flow_map(s) if "{" in s else {}
        if flow:                                          # with: { name: x, path: y, retention-days: 14 }
            for k, v in flow.items():
                if k == "name":
                    out["name"] = v
                elif k == "path":
                    out["paths"].append(v)
                elif k == "retention-days":
                    try:
                        out["retention"] = int(v)
                    except ValueError:
                        pass
                elif k == "key":
                    out["key"] = v
            i += 1
            continue
        if s.startswith("name:") and ind > base:
            out["name"] = _strip_q(s.split(":", 1)[1])
        elif s.startswith("retention-days:") and ind > base:
            try:
                out["retention"] = int(_strip_q(s.split(":", 1)[1]))
            except ValueError:
                pass
        elif s.startswith("key:") and ind > base:
            out["key"] = _strip_q(s.split(":", 1)[1])
        elif s.startswith("path:") and ind > base:
            val = s.split(":", 1)[1].strip()
            if val in ("|", ">", "|-", ">-", ""):
                j = i + 1
                while j < len(block) and (not block[j].strip() or _indent(block[j]) > ind):
                    if block[j].strip():
                        out["paths"].append(_strip_q(block[j]))
                    j += 1
                i = j - 1
            elif val.startswith("["):                      # 行内 list
                out["paths"].extend(_strip_q(x) for x in val.strip("[]").split(",") if x.strip())
            else:
                out["paths"].append(_strip_q(val))
        i += 1
    return out


def scan_file(path: Path) -> list[dict]:
    """返回该 workflow 里每个 artifact / cache 出口一条记录。"""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    recs: list[dict] = []
    seen: set[int] = set()
    for idx, line in enumerate(lines):
        if not ANY_ARTIFACT_USES.match(line):
            continue
        start, end = _step_bounds(lines, idx)
        if start in seen:
            continue
        seen.add(start)
        st = parse_step(lines[start:end])
        kind = "upload-artifact" if "upload-artifact" in st["uses"] else "cache"
        live = [p for p in st["paths"]
                if not ("*" not in p and p.endswith(S_EXEMPT_SUFFIX))]
        probe = " ".join(live) + " " + st["key"]
        low = probe.lower()
        hits = sorted({mk for mk in S_MARKERS if mk in low})
        recs.append({
            "file": str(path),
            "line": start + 1,
            "kind": kind,
            "name": st["name"] or st["key"] or "(无名)",
            "paths": st["paths"] or ([st["key"]] if st["key"] else []),
            "retention": st["retention"],
            "s_level": bool(hits),
            "s_hits": hits,
        })
    return recs


def scan(root: Path) -> list[dict]:
    wf = root / ".github" / "workflows"
    if not wf.is_dir():
        raise SystemExit("找不到 %s（--root 指到仓库根目录）" % wf)
    recs: list[dict] = []
    for p in sorted(list(wf.rglob("*.yml")) + list(wf.rglob("*.yaml"))):
        recs.extend(scan_file(p))
    return recs


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--max-retention", type=int, default=3)
    ap.add_argument("--strict-retention", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    root = Path(a.root).resolve()
    recs = scan(root)
    bad = [r for r in recs if r["s_level"]]
    fat = [r for r in recs if not r["s_level"] and (r["retention"] is None or r["retention"] > a.max_retention)]

    rel = lambda r: str(Path(r["file"]).relative_to(root))  # noqa: E731
    if a.json:
        print(json.dumps({"root": str(root), "exports": len(recs), "s_level": len(bad),
                          "retention_warn": len(fat),
                          "records": [{**r, "file": rel(r)} for r in recs]}, ensure_ascii=False, indent=1))
    else:
        print("== 公开仓制品/缓存出口清点（%s）==" % root)
        print("%-42s %-6s %-16s %-7s %s" % ("workflow:line", "出口", "name", "留存", "path / 级别"))
        for r in recs:
            lvl = "❌S级(%s)" % ",".join(r["s_hits"]) if r["s_level"] else "普通"
            ret = "%dd" % r["retention"] if r["retention"] is not None else "默认(90d)"
            print("%-42s %-6s %-16s %-7s %s" % (
                "%s:%d" % (rel(r), r["line"]), "artifact" if r["kind"] == "upload-artifact" else "cache",
                r["name"], ret, " | ".join(r["paths"]) + "  ← " + lvl))
        print("\n共 %d 个出口：S 级 %d / 留存超 %dd 或未设 %d"
              % (len(recs), len(bad), a.max_retention, len(fat)))
        for r in bad:
            print("  ❌ S 级：%s:%d  %s  path=%s" % (rel(r), r["line"], r["name"], " | ".join(r["paths"])))
        for r in fat:
            print("  ⚠️ 留存：%s:%d  %s  retention=%s（要求 ≤%dd，见 muse-000146 第 9 项）"
                  % (rel(r), r["line"], r["name"], r["retention"], a.max_retention))

    if bad:
        print("\n判定：❌ 有 %d 处 S 级（行级/staging 数据）出口，公开仓禁止" % len(bad))
        return 1
    if fat and a.strict_retention:
        print("\n判定：❌ %d 处留存超 %dd（--strict-retention）" % (len(fat), a.max_retention))
        return 1
    print("\n判定：✅ 无 S 级出口（%d 处出口；留存告警 %d 条仅为提示）" % (len(recs), len(fat)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
