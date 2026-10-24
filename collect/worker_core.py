#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工人公共调度层 —— 7 个 run_step_0X.py 都调它。

分工：
  · 本文件 = 机械部分（选层 / 逐层调引擎 / 汇总退出码）
  · run_step_0X.py = 那一步的业务差异（默认 policy + 可覆盖的参数）
  · steps.json = 参数（C 阶段落地；现在用下面 DEFAULTS，结构与之一致）

★ 单层直跑兼容：带 --layer 时直接进 pilot.main()，现有 matrix workflow 不受影响。
"""
from __future__ import annotations
import argparse
import csv
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PLAN_F = os.path.join(HERE, "layer_plan.csv")
LAYERS_F = os.path.join(HERE, "pilot_layers.json")
STEPS_F = os.path.join(HERE, "steps.json")

# 与未来 steps.json 同结构；steps.json 存在时按 step 覆盖同名键
DEFAULTS = {
    "00": {"kind": "bootstrap", "title": "地基"},
    "01": {"kind": "preflight", "title": "预检", "shards": 12},
    "02": {"kind": "collect", "title": "试点 8 层",
           "select": {"source": "pilot_layers"}, "workers": 4, "unit_rows": 500000},
    "03": {"kind": "collect", "title": "单州 KS",
           "select": {"state": "KS"}, "workers": 4, "unit_rows": 200000,
           "geom_in": ["point", "multipoint", "socrata", "na"]},
    "04": {"kind": "collect", "title": "全州放量",
           "select": {"where": "row_count>300000"}, "workers": 4, "unit_rows": 1000000,
           "geom_in": ["point", "multipoint", "socrata", "na"]},
    "05": {"kind": "collect", "title": "县市碎片",
           "select": {"mode": "bulk"}, "batch": 40, "workers": 4, "unit_rows": 100000,
           "geom_in": ["point", "multipoint", "socrata", "na"]},
    "06": {"kind": "report", "title": "收工"},
}


def load_policy(step):
    pol = dict(DEFAULTS.get(step) or {})
    if os.path.exists(STEPS_F):
        try:
            ext = (json.load(open(STEPS_F, encoding="utf-8")).get("steps") or {}).get(step) or {}
            for k, v in ext.items():
                if isinstance(v, dict) and isinstance(pol.get(k), dict):
                    pol[k] = dict(pol[k], **v)
                else:
                    pol[k] = v
        except Exception as e:
            print("⚠️ steps.json 解析失败（改用内置默认）：%s" % str(e)[:120])
    return pol


def _rows_from_csv(path=None):
    path = path or PLAN_F          # 不能在默认参数里绑 PLAN_F：那样 patch 模块属性会失效
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _norm_plan_row(r):
    return {"id": r.get("layer_id") or r.get("id"),
            "state": r.get("state") or "",
            "title": r.get("title") or r.get("layer_id") or "",
            "svc": r.get("svc") or "FeatureServer",
            "url": r.get("url") or "",
            "expect": int(r["row_count"]) if (r.get("row_count") or "").isdigit() else None,
            "plan": r.get("plan") or "",
            "geom": r.get("geom") or ""}


def _cmp(row, expr):
    """只支持「字段>数字」「字段<数字」「字段=值」—— 不发明 DSL"""
    import re
    m = re.match(r"^\s*(\w+)\s*(>=|<=|>|<|=)\s*(.+?)\s*$", expr or "")
    if not m:
        return True
    field, op, val = m.group(1), m.group(2), m.group(3).strip()
    cur = row.get(field)
    try:
        cur_n, val_n = float(cur), float(val)
    except (TypeError, ValueError):
        cur_n = val_n = None
    if cur_n is not None:
        return {">": cur_n > val_n, ">=": cur_n >= val_n,
                "<": cur_n < val_n, "<=": cur_n <= val_n, "=": cur_n == val_n}[op]
    return str(cur or "") == val if op == "=" else True


def select_layers(step, limit=0, policy=None):
    """按 policy 选出本步要采的层。返回 cfg 列表（结构同 pilot_layers.json）。"""
    pol = policy or load_policy(step)
    sel = pol.get("select") or {}
    if sel.get("source") == "pilot_layers" or not sel:
        rows = json.load(open(LAYERS_F, encoding="utf-8")) if os.path.exists(LAYERS_F) else []
        out = [dict(r) for r in rows]
    else:
        rows = [_norm_plan_row(r) for r in _rows_from_csv()]
        out = [r for r in rows if r["url"]]
        if sel.get("state"):
            out = [r for r in out if r["state"] == sel["state"]]
        if sel.get("where"):
            out = [r for r in out if _cmp(r, sel["where"])]
        if sel.get("mode") == "bulk":
            skip = ("skip", "empty")
            out = [r for r in out if (r.get("plan") or "") not in skip]
            off = int(sel.get("offset") or 0)
            size = int(sel.get("batch") or pol.get("batch") or 40)
            out = out[off:off + size]
        if sel.get("layers"):
            want = set(sel["layers"])
            out = [r for r in out if r["id"] in want]
        # 几何白名单：Poligon/Polyline 是边界和道路层，采地址时纯属浪费额度
        allow = pol.get("geom_in")
        if allow:
            allow = {str(x).lower() for x in allow}
            out = [r for r in out if (r.get("geom") or "").lower() in allow]
    # 缺 url 的一律剔除（不能带病执行）
    out = [r for r in out if r.get("url")]
    return out[:limit] if limit else out


def _parse(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--layer", help="只跑这一层（兼容现有 matrix workflow）")
    ap.add_argument("--layers", help="逗号分隔的层 id 列表")
    ap.add_argument("--state")
    ap.add_argument("--offset", type=int)
    ap.add_argument("--size", type=int)
    ap.add_argument("--workers", type=int)
    ap.add_argument("--unit-rows", type=int)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--cfg")
    ap.add_argument("--max-layers", type=int, default=0, help="只跑前 N 层（灰度用）")
    ap.add_argument("--dry-run", action="store_true")
    a, _ = ap.parse_known_args(argv)
    return a


def _pilot_cmd(cfg_file, layer, a):
    cmd = [sys.executable, os.path.join(HERE, "pilot.py"),
           "--layer", layer, "--cfg", cfg_file]
    if a.workers:
        cmd += ["--workers", str(a.workers)]
    if a.unit_rows:
        cmd += ["--unit-rows", str(a.unit_rows)]
    if a.limit:
        cmd += ["--limit", str(a.limit)]
    return cmd


def run(step, argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    a = _parse(argv)
    pol = load_policy(step)
    kind = pol.get("kind")

    # ---- 单层直跑：兼容 collect-pilot.yml 的 matrix ----
    if a.layer:
        sys.argv = _pilot_cmd(a.cfg or LAYERS_F, a.layer, a)[1:]
        sys.argv[0] = os.path.join(HERE, "pilot.py")
        import pilot
        return pilot.main()

    if kind == "bootstrap":
        import supervisor
        rc1 = supervisor.entry_check()
        rc2 = subprocess.call([sys.executable, "-m", "unittest", "discover",
                               "-s", os.path.join(HERE, "tests")])
        return 0 if (rc1 == 0 and rc2 == 0) else 1

    if kind == "preflight":
        n = int(pol.get("shards") or 12)
        bad = 0
        for i in range(n):
            rc = subprocess.call([sys.executable, os.path.join(HERE, "preflight.py"),
                                  "--shard", str(i), "--n", str(n)])
            bad += (rc != 0)
        return 0 if bad == 0 else 1

    if kind == "report":
        rc = subprocess.call([sys.executable, os.path.join(HERE, "final_report.py")])
        return rc

    # ---- 默认：collect ----
    sel = dict(pol.get("select") or {})
    if a.state:
        sel["state"] = a.state
    if a.offset is not None:
        sel["offset"] = a.offset
    if a.size is not None:
        sel["batch"] = a.size
    if a.layers:
        sel["layers"] = [x.strip() for x in a.layers.split(",") if x.strip()]
    pol = dict(pol, select=sel)

    layers = select_layers(step, limit=a.max_layers, policy=pol)
    print("[step %s] %s：选中 %d 层，workers=%s unit_rows=%s"
          % (step, pol.get("title"), len(layers), a.workers or pol.get("workers"),
             a.unit_rows or pol.get("unit_rows")))
    if a.dry_run:
        for r in layers[:20]:
            print("   ", r.get("id"), r.get("state"), r.get("expect"), r.get("url", "")[:70])
        return 0
    if not layers:
        print("没有选中任何层")
        return 1

    tmp = os.path.join("/tmp", "worker_cfg_%s.json" % step)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(layers, f, ensure_ascii=False)

    bad, ok = [], 0
    for r in layers:
        cmd = _pilot_cmd(tmp, r["id"], a)
        rc = subprocess.call(cmd)
        if rc == 0:
            ok += 1
        else:
            bad.append(r["id"])
            print("❌ %s rc=%d" % (r["id"], rc))
    print("[step %s] 完成：成功 %d / 失败 %d%s"
          % (step, ok, len(bad), ("（" + ",".join(bad[:10]) + "）") if bad else ""))
    return 0 if not bad else 1
