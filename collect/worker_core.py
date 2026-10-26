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
import time

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
            if "geom_in" not in ext and (doc.get("engine") or {}).get("geom_allow"):
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
    # ★ 列名随清单而异：layer_plan.csv 用 layer_id，batch1.csv 用 layer。
    #   只认 layer_id 会让 batch1 的 1265 行全落到空键 ""，然后把每一行都改成 "@NC-1"，
    #   url 索全数查不中 → 选层静默归零。
    def _lid(r):
        return r.get("layer_id") or r.get("layer") or r.get("id") or ""
    cnt = {}
    for r in rows:
        lid = _lid(r)
        cnt[lid] = cnt.get(lid, 0) + 1
    idx = {}
    for r in rows:
        lid = _lid(r)
        if cnt.get(lid, 0) > 1:
            idx[lid] = idx.get(lid, 0) + 1
            r["layer_id"] = "%s@%s-%d" % (lid, r.get("state") or "na", idx[lid])
    return rows


def _norm_plan_row(r):
    # ★ 字段名随清单而异：layer_plan.csv 用 row_count，situs_layers.csv 用 rows，
    #   batch1.csv 用 declared/layer。只认一种就会让整批选层静默归零。
    raw = r.get("row_count") or r.get("rows") or r.get("declared")
    return {"id": r.get("layer_id") or r.get("layer") or r.get("id"),
            "state": r.get("state") or "",
            "title": r.get("title") or r.get("layer_id") or r.get("layer") or "",
            "svc": r.get("svc") or "FeatureServer",
            "url": r.get("url") or "",
            "expect": int(raw) if str(raw or "").isdigit() else None,
            "plan": r.get("plan") or "",
            "geom": r.get("geom") or "",
            "grade": r.get("grade") or "",
            "eff": r.get("eff") or ""}


_URL_IDX = None


def _url_index():
    """situs_layers.csv 建 layer_id → url 索引（batch1.csv 只存 layer/state/grade/declared/eff）。"""
    global _URL_IDX
    if _URL_IDX is None:
        _URL_IDX = {}
        f = os.path.join(HERE, "situs_layers.csv")
        if os.path.exists(f):
            with open(f, encoding="utf-8") as fh:
                for r in csv.DictReader(fh):
                    lid, url = r.get("layer_id") or "", r.get("url") or ""
                    if lid and url:
                        _URL_IDX[lid] = url
    return _URL_IDX


# ---------------- 续采：已采层判定（本机清单 + Releases 双来源） ----------------
REPO = os.environ.get("GITHUB_REPOSITORY") or "ip9988001/world-map-data-33"
DONE_NAME = "parcel_done.json"
REL_CACHE = ".release_index.json"
REL_TTL = int(os.environ.get("WC_REL_TTL") or 600)


def _gh(path):
    """调 gh api。拿不到就返回 None，绝不抛：续采判断失败时宁可多采，不许炸掉整批。"""
    if os.environ.get("WC_OFFLINE"):
        return None
    try:
        r = subprocess.run(["gh", "api", path], capture_output=True, text=True, timeout=180)
        if r.returncode != 0:
            return None
        return json.loads(r.stdout or "null")
    except Exception:
        return None


def parcel_audit_layers():
    """parcel_done.json 里的全部层（含未完成）—— 用于「本机说没采完」的否决权。"""
    f = os.path.join(HERE, DONE_NAME)
    if not os.path.exists(f):
        return {}
    try:
        return json.load(open(f, encoding="utf-8")).get("layers") or {}
    except Exception as e:
        print("⚠️ parcel_done.json 读不动，按「无已采层」处理：%s" % str(e)[:80])
        return {}


def parcel_done():
    """本机 4.7G 解析产物（P3 生成）→ 已完成层字典。文件不存在时返回空，不是错误。"""
    return {k: v for k, v in parcel_audit_layers().items() if v.get("complete")}


def release_done(step="10", use_cache=True):
    """扫 Releases，返回 {layer: {"tag":..., "complete": bool, "how":...}}

    ★ 判据分两档，必须写清来源，不许假装精确：
      浅判（本函数）= tag 形如 collect-stepNN-<layer> 且 assets 里有 -checkpoint.json
      深判（P6 人工验收）= 再拉 checkpoint，unit_uploaded 全 true 且
                           sum(unit_rows) ≥ declared×0.99（半截层不算完成）
    为什么默认浅判：深判每层要额外一次 asset 下载，批1 有上千个 tag 时就会打爆
    API 额度；而续采阶段真正要剔的层主要来自 parcel_done.json（精确，来自逐层数行），
    Releases 侧目前只有几十个 tag。
    只认「tag 存在」才是错的——那会把截断层永久当已采完，3.7M 行缺口就是这么被埋的。
    """
    key = "step%s" % step
    cache_f = os.path.join(HERE, REL_CACHE)
    if use_cache and os.path.exists(cache_f):
        try:
            c = json.load(open(cache_f, encoding="utf-8"))
            if time.time() - float(c.get("at") or 0) < REL_TTL and key in (c.get("data") or {}):
                return c["data"][key]
        except Exception:
            pass

    seen, page = {}, 1
    while page <= 40:
        batch = _gh("repos/%s/releases?per_page=100&page=%d" % (REPO, page))
        if not batch:
            break
        for r in batch:
            tag = r.get("tag_name") or ""
            m = re.match(r"^collect-step%s-(.+)$" % step, tag)
            if not m:
                continue
            lid = m.group(1)
            assets = [a.get("name") for a in (r.get("assets") or [])]
            seen[lid] = {"tag": tag, "assets": assets,
                         "complete": any(a and a.endswith("-checkpoint.json") for a in assets),
                         "how": "shallow"}
        if len(batch) < 100:
            break
        page += 1

    if seen or page > 1:
        try:
            c = {}
            if os.path.exists(cache_f):
                c = json.load(open(cache_f, encoding="utf-8")) or {}
            c.setdefault("data", {})[key] = seen
            c["at"] = time.time()
            json.dump(c, open(cache_f, "w", encoding="utf-8"), ensure_ascii=False)
        except Exception:
            pass
    return seen


def done_layers(step="10"):
    """已采层全集 = 本机清单（精确）+ Releases（tag）

    ★ 优先级：本机逐层数行 > Releases 的 tag 浅判。
      2026-10-26 那次误跑的产物正好暴露了这一点：4 层在 Releases 里
      有 tag 有 checkpoint，但本机实测缺口还在（partial）。
      若让 tag 浅判覆盖本机结论，这 4 层的缺口就永久钉死、永远不会被补。
      所以：本机明确说 complete=false 的层，一律不因为 tag 存在而跳过。
    """
    audit = parcel_audit_layers()
    done = {k: v for k, v in audit.items() if v.get("complete")}
    for lid, rec in release_done(step).items():
        if not rec.get("complete"):
            continue
        if lid in audit and not audit[lid].get("complete"):
            continue
        done.setdefault(lid, rec)
    return done


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
        # ★ STEP-10 这类步的选层清单不是 layer_plan.csv：宗地层是 Polygon/Polyline，
        #   STEP-01 预检按几何白名单早把它们 skip 了，永远不会进 plan。靠 select.file 指路。
        f = sel.get("file")
        csv_path = None
        if f:
            csv_path = f if os.path.isabs(f) else os.path.join(ROOT, f)
            if not os.path.exists(csv_path):
                csv_path = os.path.join(HERE, os.path.basename(f))
        rows = [_norm_plan_row(r) for r in _rows_from_csv(csv_path)]
        # 清单里没有 url 的（batch1.csv 就是），从 situs_layers.csv 补回来
        if any(not r["url"] for r in rows):
            idx_url = _url_index()
            for r in rows:
                if not r["url"]:
                    # 唯一化后缀 @STATE-n 不是真层名，查 url 要剥掉
                    r["url"] = (idx_url.get(r["id"])
                                or idx_url.get((r["id"] or "").split("@")[0]) or "")
        out = [r for r in rows if r["url"]]
        if sel.get("grade"):
            want_g = {str(x).lower() for x in sel["grade"]}
            out = [r for r in out if (r.get("grade") or "").lower() in want_g]
        if sel.get("eff_min") is not None:
            # ★ 有效率口径不统一：situs 表用 0~1 小数，batch1 表用 0~100 百分数。
            #   直接比较会让 eff_min=0.2 把 100.0 判成不达标 → 整批归零。
            def _eff01(v):
                try:
                    x = float(v)
                except (TypeError, ValueError):
                    return None
                return x / 100.0 if x > 1 else x
            _m = float(sel["eff_min"])
            out = [r for r in out if (_eff01(r.get("eff")) is not None and _eff01(r.get("eff")) >= _m)]
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
        # ★ 已采层剔除必须在 bulk 窗口切片**之前**：
        #   先切 [off:off+size] 再剔除，切出来的 20 层里仍混着已采层，等于白跑。
        # ★ 显式点名要采的层（--layers）不算续采，不能剔：冒烟测的就是已采层。
        #   自动选层才走 skip_done。
        if sel.get("skip_done") and not sel.get("layers"):
            done = done_layers(step)
            if done:
                _b = len(out)
                out = [r for r in out if r["id"] not in done]
                print("⏭ 跳过已采 %d 层，待采 %d 层" % (_b - len(out), len(out)))
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
                # ★ 反查必须关掉 bulk 游标窗口：05/10 是 offset+size 分批推进，
                #   开着窗口时 matrix 里第 N 层会反查不到 → 全部 unknown_layer 秒挂。
                sel = {k: v for k, v in (pol.get("select") or {}).items()
                       if k not in ("mode", "offset", "batch")}
                sel["skip_done"] = False    # 反查已采层也必须能查到，否则 unknown_layer 秒挂
                pool = select_layers(step, limit=0, policy=dict(pol, select=sel))
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
KINDS = ("bootstrap", "preflight", "collect", "report", "analyze", "delta", "parcel_situs")


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
    for st in sorted(steps):
        if st not in steps:
            errs.append("缺 STEP %s 的 policy" % st)
            continue
        pol = steps[st] or {}
        if pol.get("kind") not in KINDS:
            errs.append("STEP %s kind 非法：%r（只允许 %s）" % (st, pol.get("kind"), "/".join(KINDS)))
        if not pol.get("title"):
            errs.append("STEP %s 缺 title" % st)
        if pol.get("kind") in ("collect", "parcel_situs"):
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

    if kind == "analyze":
        # STEP 08：只读自家 Release，不动数据。dedup.py 自己做全部事。
        rc = subprocess.call([sys.executable, os.path.join(HERE, "dedup.py")] + argv)
        return rc

    if kind == "delta":
        # STEP 09：探测编辑时间字段 + 统计变更量（不落地数据，先验证机制）
        rc = subprocess.call([sys.executable, os.path.join(HERE, "delta.py")] + argv)
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
