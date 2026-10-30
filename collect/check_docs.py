#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判据卡一致性校验器 —— steps.json ↔ 7 份 STEP-0X.md ↔ 真实文件 ↔ 命令

为什么要有它：参数只在 steps.json 一处；判据卡里有一份「镜像块」方便人读。
镜像靠手改就会漂 —— 这个脚本逐字段比对，漂了直接判红，不给「大概一致」留缝。

用法：
  python3 collect/check_docs.py            # 人看
  python3 collect/check_docs.py --json     # 机器看（exit 0 全绿 / 1 有红）
"""
from __future__ import annotations
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STEPS_JSON = os.path.join(HERE, "steps.json")
MIRROR_RE = re.compile(r"<!-- steps\.json 镜像.*?```json\s*(\{.*?\})\s*```", re.S)
BASH_RE = re.compile(r"```bash\s*(.*?)```", re.S)
WANT_FIELDS = ("kind", "poly_centroid", "poly_rings", "title", "select", "workers", "unit_rows",
                "tag", "gate", "evidence", "accept")
# 命令块里的脚本：开关按**被调的那个脚本**校验，不是一律按 supervisor.py
# （2026-10-30 修：补采四阶段走 full_plan/full_shard/step_full_report，老规则会把真开关判成假的）
CMD_SCRIPT_RE = re.compile(r"(collect/[\w/.\-]+\.py|scripts/[\w/.\-]+\.py)")
_FLAGS_CACHE = {}


def load_steps():
    with open(STEPS_JSON, encoding="utf-8") as f:
        return json.load(f).get("steps") or {}


def supervisor_flags():
    """从 supervisor.py 的 argparse 里取出真实存在的开关：命令模板写错会当场暴露。"""
    src = open(os.path.join(HERE, "supervisor.py"), encoding="utf-8").read()
    return set(re.findall(r'add_argument\("(--[a-zA-Z0-9-]+)"', src))


def flags_of(script_rel):
    """某个脚本自己 argparse 里真有的开关（按文件缓存；文件不存在返回 None）。"""
    if script_rel in _FLAGS_CACHE:
        return _FLAGS_CACHE[script_rel]
    fp = os.path.join(ROOT, script_rel)
    if not os.path.exists(fp):
        _FLAGS_CACHE[script_rel] = None
        return None
    src = open(fp, encoding="utf-8").read()
    _FLAGS_CACHE[script_rel] = set(re.findall(r'add_argument\("(--[a-zA-Z0-9-]+)"', src))
    return _FLAGS_CACHE[script_rel]


def check_one(n, s, flags):
    """返回 (问题列表, 事实字典)。"""
    bad = []
    doc_rel = ((s.get("supervise") or {}).get("doc") or "collect/steps/STEP-%s.md" % n)
    doc = os.path.join(ROOT, doc_rel)
    if not os.path.exists(doc):
        return ["判据卡不存在：%s" % doc_rel], {}

    text = open(doc, encoding="utf-8").read()
    m = MIRROR_RE.search(text)
    if not m:
        return ["%s 里找不到 steps.json 镜像块" % doc_rel], {}

    try:
        mirror = json.loads(m.group(1))
    except Exception as e:
        return ["%s 镜像块不是合法 JSON：%s" % (doc_rel, str(e)[:80])], {}

    if str(mirror.get("step")) != str(n):
        bad.append("镜像块 step=%r，应为 %r" % (mirror.get("step"), n))
    for k in WANT_FIELDS:
        if k not in s:
            continue
        if mirror.get(k) != s.get(k):
            bad.append("字段漂移 `%s`：判据卡=%r ≠ steps.json=%r"
                       % (k, mirror.get(k), s.get(k)))

    # 判据卡里点名的文件：代码/文档/workflow 必须真的在；产物类（还没跑出来）只记「待产出」
    pending = []
    for rel in re.findall(r"`(collect/[\w/.\-]+|\.github/workflows/[\w/.\-]+)`", text):
        if os.path.exists(os.path.join(ROOT, rel)):
            continue
        if rel.startswith("collect/reports/") or rel.endswith(".csv") or rel.endswith(".json"):
            pending.append(rel)          # 本步产出物，跑完才有
        else:
            bad.append("判据卡引用了不存在的文件：%s" % rel)

    # 命令块里的开关必须是 supervisor 真有的
    cmds = [ln.strip() for blk in BASH_RE.findall(text) for ln in blk.splitlines()
            if ln.strip().startswith("python3")]
    if not cmds:
        bad.append("判据卡里没有可照抄的命令块")
    for c in cmds:
        m_s = CMD_SCRIPT_RE.search(c)
        allowed = flags if m_s is None else flags_of(m_s.group(1))
        if allowed is None:
            bad.append("命令引用了不存在的脚本：`%s`（%s）" % (m_s.group(1), c[:70]))
            continue
        for f in re.findall(r"(--[a-zA-Z0-9-]+)", c):
            if f not in allowed:
                bad.append("命令里的开关不存在：`%s`（%s）" % (f, c[:70]))

    return bad, {"step": n, "doc": doc_rel, "mirror": bool(m), "cmds": len(cmds), "pending": pending}


def check_steps_json(steps):
    """steps.json 自身的完整性：每步 evidence 有收集器、supervise 五项齐。"""
    bad = []
    sys.path.insert(0, HERE)
    try:
        import supervisor as core
    except Exception as e:
        return ["supervisor.py 导不进来：%s" % str(e)[:120]]
    for n, s in steps.items():
        unknown = [e for e in (s.get("evidence") or []) if e not in core.COLLECTORS]
        if unknown:
            bad.append("STEP %s 的 evidence 没有收集器：%s" % (n, unknown))
        sup = s.get("supervise") or {}
        lack = [k for k in ("stall_min", "wake_reason", "cmds", "doc", "wf") if not sup.get(k)]
        if lack:
            bad.append("STEP %s 的 supervise 缺项：%s" % (n, lack))
        wf = os.path.join(ROOT, ".github", "workflows", sup.get("wf") or "")
        if not os.path.exists(wf):
            bad.append("STEP %s 的工人 workflow 不存在：%s" % (n, sup.get("wf")))
        sp = os.path.join(HERE, "supervisors", "step_%s.py" % n)
        if not os.path.exists(sp):
            bad.append("STEP %s 的工头不存在：supervisors/step_%s.py" % (n, n))
    return bad


def sync_docs():
    """把判据卡里的镜像块按 steps.json 重写（只动机器块，正文一个字不碰）。"""
    steps = load_steps()
    n = 0
    for k, v in steps.items():
        rel = ((v.get("supervise") or {}).get("doc") or "collect/steps/STEP-%s.md" % k)
        fp = os.path.join(ROOT, rel)
        if not os.path.exists(fp):
            continue
        m = MIRROR_RE.search(open(fp, encoding="utf-8").read())
        if not m:
            continue
        mirror = {"step": k, **{f: v.get(f) for f in WANT_FIELDS if v.get(f) is not None}}
        block = "```json\n" + json.dumps(mirror, ensure_ascii=False, indent=1) + "\n```"
        text = open(fp, encoding="utf-8").read()
        open(fp, "w", encoding="utf-8").write(text[:m.start()] + "<!-- steps.json 镜像（只读；校验器 check_docs.py 逐字段比对） -->\n" + block + text[m.end():])
        n += 1
    print("已同步 %d 份判据卡的镜像块" % n)
    return 0


def main():
    if "--sync" in sys.argv:
        return sync_docs()
    as_json = "--json" in sys.argv
    steps = load_steps()
    flags = supervisor_flags()
    problems = check_steps_json(steps)
    facts = []
    for n, s in steps.items():
        bad, fact = check_one(n, s, flags)
        problems += bad
        if fact:
            facts.append(fact)

    ready = not problems
    if as_json:
        print(json.dumps({"ready": ready, "docs": len(steps), "facts": facts,
                          "problems": problems}, ensure_ascii=False, indent=1))
        return 0 if ready else 1

    for n, f in ((f["step"], f) for f in facts):
        tail = ("，产物待产出：%s" % "、".join(f["pending"])) if f.get("pending") else ""
        print("✅ STEP %s 判据卡 %s — 镜像块一致，命令 %d 条可照抄%s" % (n, f["doc"], f["cmds"], tail))
    for p in problems:
        print("❌ " + p)
    print("\n%s：%d 份判据卡，%d 条问题" % ("READY" if ready else "BLOCKED", len(steps), len(problems)))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
