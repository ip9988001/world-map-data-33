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
import re
import subprocess
import sys
import tempfile

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
            doc = json.load(open(STEPS_F, encoding="utf-8"))
            ext = (doc.get("steps") or {}).get(step) or {}
            if not ext.get("geom_in") and (doc.get("engine") or {}).get("geom_allow"):
                ext = dict(ext, geom_in=list(doc["engine"]["geom_allow"]))
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
        rows = list(csv.DictReader(f))
    # ★ layer_id 会撞车（实测 245 个重复、56 个跨州）：撞车的加 `@<state>-<n>` 后缀。
    #   不唯一化就会「--layer 反查命中别的州那一行」→ 静默采错数据，比报错更坏。
    cnt = {}
    for r in rows:
        lid = r.get("layer_id") or ""
        cnt[lid] = cnt.get(lid, 0) + 1
    idx = {}
    for r in rows:
        lid = r.get("layer_id") or ""
        if cnt.get(lid, 0) > 1:
            idx[lid] = idx.get(lid, 0) + 1
            r["layer_id"] = "%s@%s-%d" % (lid, r.get("state") or "na", idx[lid])
    return rows


def _norm_plan_row(r):
    return {"id": r.get("layer_id") or r.get("id"),
            "state": r.get("state") or "",
            "title": r.get("title") or r.get("layer_id") or "",
            "svc": r.get("svc") or "FeatureServer",
            "url": r.get("url") or "",
            "expect": int(r["row_count"]) if (r.get("row_count") or "").isdigit() else None,
            "plan": r.get("plan") or "",
            "geom": r.get("geom") or ""}


# where 表达式里的字段名 → plan 行里的真实字段（写 row_count 但行里叫 expect，曾让过滤静默失效）
FIELD_ALIAS = {"row_count": "expect", "count": "expect", "rows": "expect", "layer_id": "id", "state_name": "state"}


def _cmp(row, expr):
    """只支持「字段>数字」「字段<数字」「字段=值」—— 不发明 DSL

    ★ 2026-10-24 事故：STEP-04 写的 `where: row_count>300000` 因为字段名对不上（行里叫 expect），
      float(None) 抛错被吞进 except，函数返回 True → 过滤从未生效，19,116 层（全量点层）被当成
      「州级大层」。现在字段找不到一律判 False：宁可少采，不许靠猜乱采。
    """
    import re as _re
    m = _re.match(r"^\s*(\w+)\s*(>=|<=|>|<|=)\s*(.+?)\s*$", expr or "")
    if not m:
        return True
    field, op, val = m.group(1), m.group(2), m.group(3).strip()
    field = FIELD_ALIAS.get(field, field)
    cur = row.get(field)
    if cur is None:
        return False
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
        # ★ skip/empty 是「这层不该采」的结论，与选法无关：放在所有过滤之前统一剔除
        if not sel.get("include_skip"):
            out = [r for r in out if (r.get("plan") or "") not in ("skip", "empty")]
        if sel.get("state"):
            out = [r for r in out if r["state"] == sel["state"]]
        if sel.get("where"):
            out = [r for r in out if _cmp(r, sel["where"])]
        if sel.get("layers"):
            want = set(sel["layers"])
            out = [r for r in out if r["id"] in want]
        # ---- 04 放量专用口径：全州级大层里只要真·地址层 ----
        # 实测：row_count>300000 一条能筛出 19,116 层 / 14.4 亿行，其中火警出警记录、
        # 欧洲 OSM、parcels/zones 占 42% 的行 —— 靠标题关键词和行数上限收窄。
        if sel.get("skip_blocked"):
            try:
                blk = json.load(open(os.path.join(HERE, "blocked.json"), encoding="utf-8"))
                ids = {x.get("id") for x in (blk.get("items") or [])}
                out = [r for r in out if r["id"] not in ids]
            except Exception as e:
                print("⚠️ blocked.json 读不动，跳过 skip_blocked：%s" % str(e)[:80])
        if sel.get("svc_exclude"):
            bad = {str(x).lower() for x in sel["svc_exclude"]}
            out = [r for r in out if (r.get("svc") or "").lower() not in bad]
        if sel.get("state_exclude"):
            bad = {str(x) for x in sel["state_exclude"]}
            out = [r for r in out if r["state"] not in bad]
        if sel.get("title_include"):
            rx = re.compile(sel["title_include"], re.I)
            out = [r for r in out if rx.search(r.get("title") or "")]
        if sel.get("title_exclude"):
            rx = re.compile(sel["title_exclude"], re.I)
            out = [r for r in out if not rx.search(r.get("title") or "")]
        if sel.get("rows_max"):
            out = [r for r in out if (r.get("expect") or 0) <= int(sel["rows_max"])]
        if sel.get("rows_min"):
            out = [r for r in out if (r.get("expect") or 0) >= int(sel["rows_min"])]
        # 几何白名单：Poligon/Polyline 是边界和道路层，采地址时纯属浪费额度
        allow = pol.get("geom_in")
        if allow:
            allow = {str(x).lower() for x in allow}
            out = [r for r in out if (r.get("geom") or "").lower() in allow]
        # ★ 排序与分批窗口必须放在所有过滤之后：
        #   上一版先切 [off:off+size] 再过滤，40 层切出来只剩 1 层（过滤把窗口里的都杀了）。
        if sel.get("order") in ("rows_desc", "rows_asc"):
            out = sorted(out, key=lambda r: (r.get("expect") or 0), reverse=(sel["order"] == "rows_desc"))
        if sel.get("mode") == "bulk":
            off = int(sel.get("offset") or 0)
            size = int(sel.get("batch") or pol.get("batch") or 40)
            out = out[off:off + size]
    # 缺 url 的一律剔除（不能带病执行）
    out = [r for r in out if r.get("url")]
    if not limit:
        return out
    if pol.get("limit_mode") == "spread" and len(out) > limit:
        # 灰度抽样：按 row_count 排序后等距取 limit 个 → 小/中/大三档都在里面
        pool = sorted(out, key=lambda r: r.get("expect") or 0)
        gap = (len(pool) - 1) / float(limit - 1) if limit > 1 else 0
        return [pool[int(round(i * gap))] for i in range(limit)]
    return out[:limit]


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
    ap.add_argument("--validate", action="store_true", help="校验 steps.json")
    ap.add_argument("--show", metavar="STEP", help="展开该步的完整参数")
    ap.add_argument("--list-matrix", action="store_true", help="输出 matrix JSON（给 workflow 用）")
    a, _ = ap.parse_known_args(argv)
    return a


def cli(argv=None, step=None):
    """7 个 run_step_0X.py 的统一 CLI 入口（含 --validate / --show）。"""
    a = _parse(argv)
    if a.validate:
        ok, errs = validate()
        for e in errs:
            print("❌ " + e)
        print(("%s：%d 条" % ("READY" if ok else "BLOCKED", len(errs))))
        return 0 if ok else 1
    if a.show:
        return show(a.show, limit=a.max_layers)
    if a.list_matrix:
        pol = _eff(step, a)
        layers = select_layers(step, limit=a.max_layers, policy=pol)
        if len(layers) > 256:
            # ★ GitHub matrix 硬上限 256 job / run；超了不是慢，是直接跑不起来
            print(json.dumps({"err": "matrix_too_big", "layers": len(layers), "max": 256,
                              "hint": "用 --max-layers 分批，或收窄 steps.json 的 select"},
                             ensure_ascii=False))
            return 3
        print(json.dumps({"include": [{"layer": r["id"]} for r in layers]}, ensure_ascii=False))
        return 0
    return run(step, argv)


def _resolve_layer(step, layer):
    """把 matrix 传来的 layer 反查成一份「单层 cfg 文件」。
    顺序：本步选层结果 → 全量 plan.csv → 试点配置 pilot_layers.json。
    为什么不能直接用 pilot_layers.json：试点只有 8 层，STEP-03 的 120 层全在里面查不到，
    上一版就是这里让所有 collect job 秒挂 unknown layer。
    """
    want = layer
    for src in ("step", "plan", "pilot"):
        try:
            if src == "step":
                pol = load_policy(step)
                pool = select_layers(step, limit=0, policy=dict(pol, select=dict(pol.get("select") or {}) | {"_force_plan": True}))
            elif src == "plan":
                pool = [_norm_plan_row(r) for r in _rows_from_csv()]
            else:
                pool = json.load(open(LAYERS_F, encoding="utf-8")) if os.path.exists(LAYERS_F) else []
        except Exception:
            pool = []
        hit = [r for r in pool if (r.get("id") or r.get("layer_id")) == want]
        if hit:
            one = hit[0]
            one = {"id": one.get("id") or one.get("layer_id"), "title": one.get("title") or want,
                   "svc": one.get("svc") or "FeatureServer", "url": one.get("url"),
                   "expect": one.get("expect")}
            tmp = os.path.join(tempfile.gettempdir(), "one-layer-%s.json" % re.sub(r"[^\w@.\-]", "_", want))
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump([one], f, ensure_ascii=False, indent=1)
            return tmp, one["id"]
    return None, None


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


# ---------------- 配置校验 / 展开（steps.json 是唯一参数来源） ----------------
KINDS = ("bootstrap", "preflight", "collect", "report")


def validate(path=None):
    """校验 steps.json。返回 (ok, errs)。CI 与工人启动前都会用它。"""
    path = path or STEPS_F
    errs = []
    if not os.path.exists(path):
        return False, ["steps.json 不存在：%s" % path]
    try:
        cfg = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        return False, ["steps.json 解析失败：%s" % str(e)[:150]]
    if cfg.get("schema") != "v2.1":
        errs.append("schema 必须是 v2.1（实际 %r）" % cfg.get("schema"))
    eng = cfg.get("engine") or {}
    if not eng.get("channels"):
        errs.append("engine.channels 缺失（应为 keyset/ids/offset）")
    steps = cfg.get("steps") or {}
    for st in ("00", "01", "02", "03", "04", "05", "06"):
        if st not in steps:
            errs.append("缺 STEP %s 的 policy" % st)
            continue
        pol = steps[st] or {}
        if pol.get("kind") not in KINDS:
            errs.append("STEP %s kind 非法：%r（只允许 %s）" % (st, pol.get("kind"), "/".join(KINDS)))
        if not pol.get("title"):
            errs.append("STEP %s 缺 title" % st)
        if pol.get("kind") == "collect":
            if not pol.get("select"):
                errs.append("STEP %s 是 collect 但没有 select" % st)
            if "{layer}" not in (pol.get("tag") or ""):
                errs.append("STEP %s 的 tag 必须含 {layer}：%r" % (st, pol.get("tag")))
            if int(pol.get("unit_rows") or 0) <= 0:
                errs.append("STEP %s unit_rows 必须 > 0" % st)
            if int(pol.get("workers") or 0) <= 0:
                errs.append("STEP %s workers 必须 > 0" % st)
        allow = set(str(x).lower() for x in (eng.get("geom_allow") or []))
        for g in (pol.get("geom_in") or []):
            if str(g).lower() not in allow:
                errs.append("STEP %s geom_in 含未登记几何：%r" % (st, g))
    return (not errs), errs


def show(step, limit=0):
    """展开某一步的完整参数（人读+机读）。工头叫醒话术、判据卡都引用这里的输出。"""
    pol = load_policy(step)
    layers = []
    try:
        layers = select_layers(step, limit=limit, policy=pol)
    except Exception as e:
        pol["_select_error"] = str(e)[:150]
    expanded = dict(pol)
    expanded["_selected_layers"] = len(layers)
    expanded["_sample"] = [r.get("id") for r in layers[:5]]
    print(json.dumps(expanded, ensure_ascii=False, indent=1))
    return 0


def _eff(step, a):
    """把 CLI 覆盖合并进 policy（select.state/offset/batch/layers）。"""
    pol = load_policy(step)
    sel = dict(pol.get("select") or {})
    if getattr(a, "state", None):
        sel["state"] = a.state
    if getattr(a, "offset", None) is not None:
        sel["offset"] = a.offset
    if getattr(a, "size", None) is not None:
        sel["batch"] = a.size
    if getattr(a, "layers", None):
        sel["layers"] = [x.strip() for x in a.layers.split(",") if x.strip()]
    return dict(pol, select=sel)


def run(step, argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    a = _parse(argv)
    pol = load_policy(step)
    kind = pol.get("kind")

    # ---- 单层直跑：兼容 collect-pilot.yml 的 matrix ----
    if a.layer:
        cfg_f, lid = _resolve_layer(step, a.layer)
        if not cfg_f:
            print(json.dumps({"layer": a.layer, "err": "unknown_layer"}, ensure_ascii=False))
            return 2
        sys.argv = _pilot_cmd(cfg_f, lid, a)[1:]
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
    pol = _eff(step, a)
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
