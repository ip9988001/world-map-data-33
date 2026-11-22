#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全量补采 · 计划器：把「本步还剩的层」切成片，写成 plan JSON（供 matrix 分片）。

选层口径 = steps.json 里该步的 select（skip_done=true 自动剔除已采层），
切片顺序 = policy 的 order（step04 按声明行数降序；05/07 升序；10 降序）。

用法：
  python3 collect/full_plan.py --stage 04 --size 20 --out collect/ledger/step04b_plan.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from lib.fetch import classify_failure, kinds_tally   # noqa: E402
from worker_core import base_layer_id   # noqa: E402  W33-048 变体合并


def _retry(fn, what, tries=3):
    """扫描类调用一律重试。

    ★ 2026-10-30 实测事故：Releases 扫到第 3 页失败 → 只认出 185 个 tag，剩下 100+ 个
      已采层被当成「没采过」→ 续跑会拿它们全量重采。计划阶段宁可直接失败，
      也不允许「扫不全 → 多采一遍」这种静默浪费（代价是几百小时带宽）。
    """
    last = None
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            last = e
            print("⚠ %s 第 %d/%d 次失败：%s" % (what, i + 1, tries, str(e)[:160]), file=sys.stderr)
            time.sleep(2 * (i + 1))
    raise last


# ★ 第 7 项（muse-000146）：**唯一**的层放行入口。
#   「本轮采哪些层」只允许这一个来源决定 —— collect-full.yml 的 force_layers 输入 →
#   full_plan.py --force-layers。全仓禁止第二处能独立放行层的入口（同类 only-*-layers 开关一律不许新增）；
#   任何新开关都必须先经过 resolve_allowlist() 并留日志，不许在别处并行生效。
LAYERS_ALLOWLIST_SOURCE = "force_layers"

PROBE_ATTEMPTS = 3                  # 第 4 项：默认复探 3 次
PROBE_BACKOFF = (1, 2, 4)           # 退避秒数（单测里注入 sleep，不真等）
PROBE_TIMEOUT = 25
COUNT_PATHS = ("count", "counts", "total")   # 依次尝试的计数路径（上游改名时能定位到哪条命中）
DISPLAY_LIMIT = 50                  # 第 3 项：**只在展示层**截断，plan json 里必须全量


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def body_keys_sig(raw) -> str:
    """响应体的键签名（用于发现「上游把 count 改名了」）。"""
    if raw is None:
        return "none"
    text = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
    text = text.strip()
    if not text:
        return "empty"
    if text[:1] == "<":
        return "html"
    try:
        d = json.loads(text)
    except Exception:                                  # noqa: BLE001
        return "non_json"
    if isinstance(d, dict):
        if d.get("error"):
            return "error:" + ",".join(sorted((d["error"] or {}))[:6])
        return ",".join(sorted(d)[:12])
    return type(d).__name__


def parse_count_body(raw) -> dict:
    """★ 第 6 项：探针响应体的解析**固化在这里**（可单测），不许散在临时路径。

    返回 {count, count_path, body_keys_sig, parse_ok, reason}：
      · 正常 {"count": 2298}            → parse_ok=True, count_path="count"
      · 字段改名 {"total": 2298}         → 命中 "total"；若是没见过的名字 → parse_ok=False + reason
      · 空体 / HTML / 非 JSON / svcerr   → parse_ok=False + 具体 reason（**不许静默 None**）
    """
    if raw is None:
        return {"count": None, "count_path": None, "body_keys_sig": "none",
                "parse_ok": False, "reason": "no_body"}
    text = raw.decode("utf-8", "replace") if isinstance(raw, (bytes, bytearray)) else str(raw)
    text = text.strip()
    sig = body_keys_sig(raw)
    if not text:
        return {"count": None, "count_path": None, "body_keys_sig": "empty",
                "parse_ok": False, "reason": "empty_body"}
    if text[:1] == "<":
        return {"count": None, "count_path": None, "body_keys_sig": "html",
                "parse_ok": False, "reason": "html_body"}
    try:
        d = json.loads(text)
    except Exception as e:                             # noqa: BLE001
        return {"count": None, "count_path": None, "body_keys_sig": "non_json",
                "parse_ok": False, "reason": "json_error:%s" % str(e)[:60]}
    if isinstance(d, dict) and d.get("error"):
        return {"count": None, "count_path": None, "body_keys_sig": sig,
                "parse_ok": False,
                "reason": "svcerr:%s" % json.dumps(d["error"], ensure_ascii=False)[:160]}
    for path in COUNT_PATHS:
        cur, hit = d, True
        for part in path.split("."):
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                hit = False
                break
        if hit and isinstance(cur, (int, float)) and not isinstance(cur, bool):
            return {"count": int(cur), "count_path": path, "body_keys_sig": sig,
                    "parse_ok": True, "reason": ""}
    return {"count": None, "count_path": None, "body_keys_sig": sig, "parse_ok": False,
            "reason": "no_count_field(期望 %s；实际键 %s)" % ("/".join(COUNT_PATHS), sig)}


def _fetch_count_body(url, timeout=PROBE_TIMEOUT):
    """取一次 returnCountOnly 的原始响应：(status, code, body_bytes, exc_text)。"""
    ep = url.rstrip("/") + "/query?" + urllib.parse.urlencode(
        {"where": "1=1", "returnCountOnly": "true", "f": "json"})
    try:
        with urllib.request.urlopen(ep, timeout=timeout) as r:
            return 200, r.status, r.read(), ""
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:                              # noqa: BLE001
            body = b""
        return e.code, e.code, body, ""
    except Exception as e:                             # noqa: BLE001
        return None, None, b"", str(e)[:200]


def probe_layer(url, attempts=PROBE_ATTEMPTS, backoff=PROBE_BACKOFF,
                timeout=PROBE_TIMEOUT, fetch=_fetch_count_body, sleep=time.sleep):
    """★ 第 4 项：一层一次全流程 —— 复探 N 次（退避）全失败才判 dead，每次结果都落盘。

    为什么要复探：以前一次失败就判死，上游一个 5xx 抖动就把层永久钉在 dead 上。
    现在 dead 必须满足「N 次都失败」，且带 `dead_since`（UTC）与 `probe_attempts`（逐次证据）。
    复探成功 → dead=False（回到待采），不需要人工捞。
    """
    rec = {"url": (url or ""), "ok": False, "count": None, "dead": False, "dead_since": None,
           "count_path": None, "body_keys_sig": None, "parse_ok": False, "reason": "",
           "probe_attempts": []}
    if not (url or "").strip():
        rec.update(dead=True, dead_since=_now_iso(), reason="empty_url")
        return rec
    attempts = max(1, int(attempts))
    last_kind = None
    for i in range(attempts):
        t0 = time.time()
        status, code, body, exc = fetch(url, timeout)
        elapsed_ms = int((time.time() - t0) * 1000)
        parsed = parse_count_body(body)
        ok = status == 200 and parsed["parse_ok"]
        kind = ("ok" if ok else
                ("timeout" if (code is None and exc) else
                 classify_failure(code=code, body=body, status=status, exc=exc)))
        rec["probe_attempts"].append({"at": _now_iso(), "attempt": i + 1, "status": status,
                                      "code": code, "elapsed_ms": elapsed_ms, "kind": kind})
        last_kind = kind
        rec.update({k: parsed[k] for k in ("count_path", "body_keys_sig", "parse_ok", "reason")})
        if ok:
            rec.update(ok=True, count=parsed["count"])
            return rec
        if i < attempts - 1:
            sleep(backoff[min(i, len(backoff) - 1)])
    rec.update(dead=True, dead_since=_now_iso(),
               reason=rec["reason"] or ("probe_failed:%s" % last_kind))
    return rec


def _count_one(url, tries=2, timeout=25):
    """**兼容壳**（plan_probe_retry2.py 直接 import 它）：返回 int 或 None。

    语义与老版一致（失败返回 None），但内部走 probe_layer：解析固化 + 失败分类，
    不再「body 里没有 count 就当 None 且无理由」。
    """
    rec = probe_layer(url, attempts=tries, timeout=timeout)
    return rec["count"] if rec["ok"] else None


def probe_live_counts(layers, workers=8, attempts=PROBE_ATTEMPTS, fetcher=None, sleep=time.sleep):
    """计划阶段探上游实时行数 → (expect_live, failed_ids, results)。

    第 3/4/5/6 项的落点：
      · results[layer_id] = probe_layer 的完整记录（含 probe_attempts / count_path / kind）
      · failed = 复探 N 次全失败的层（列表与 `probe_failed_n` **同源**，plan json 里全量）
      · 失败按 kind 分桶（bad_request_paging / not_found_404 / server_5xx …互不串）
    """
    rows = [r for r in layers if (r.get("url") or "").strip()]
    out, failed, results = {}, [], {}
    kw = {"attempts": attempts, "sleep": sleep}
    if fetcher is not None:
        kw["fetch"] = fetcher
    with ThreadPoolExecutor(max_workers=max(1, workers)) as ex:
        futs = {ex.submit(probe_layer, r.get("url") or "", **kw): r["id"] for r in rows}
        for fut in futs:
            lid = futs[fut]
            rec = fut.result()
            results[lid] = rec
            (out.__setitem__(lid, rec["count"]) if rec["ok"] else failed.append(lid))
    for r in layers:                                   # url 为空的层也要有记录（不许静默丢）
        if r["id"] not in results:
            results[r["id"]] = {"url": "", "ok": False, "count": None, "dead": True,
                                "dead_since": _now_iso(), "count_path": None,
                                "body_keys_sig": "none", "parse_ok": False,
                                "reason": "empty_url", "probe_attempts": []}
            failed.append(r["id"])
    return out, failed, results



def resolve_allowlist(force_layers: str, force_unstable_layers: str = "") -> dict:
    """★ 第 7 项：把「显式点名要采的层」收敛成**一份** allowlist。

    现在有两条 CLI 开关（--force-layers / --force-unstable-layer），它们语义不同
    （前者「即使判完成也要重跑」、后者「即使到重试上限也要再试」），但**都不允许自己
    另行决定队列成员**：一律在这里合并成同一份 allowlist，由 main 统一施加。
    其余任何入口（workflow input / 环境变量 / 另一个 python 脚本）都不许独立放行层。

    返回 {forced, forced_unstable, source}；source 恒为 LAYERS_ALLOWLIST_SOURCE。
    """
    def _split(x):
        return [y.strip() for y in (x or "").split(",") if y.strip()]
    out = {"forced": _split(force_layers),
           "forced_unstable": _split(force_unstable_layers),
           "source": LAYERS_ALLOWLIST_SOURCE}
    if out["forced"] or out["forced_unstable"]:
        print("ℹ 层白名单唯一来源 = %s（本仓禁止第二处放行入口）" % LAYERS_ALLOWLIST_SOURCE)
    return out


def _last_kind(rec: dict) -> str:
    at = (rec or {}).get("probe_attempts") or []
    return (at[-1].get("kind") if at else None) or "other"


def _failed_by_kind(results: dict, failed_ids) -> dict:
    """第 5 项：失败按类别分桶（口径唯一来源 = lib.fetch.ALL_KINDS）。"""
    items = [{"kind": _last_kind((results or {}).get(i))} for i in (failed_ids or [])]
    return kinds_tally(items)


def _dead_entries(results: dict) -> list:
    """第 4 项：dead 项必须带 dead_since（UTC）与 probe_attempts（逐次证据）。"""
    out = []
    for lid, rec in sorted((results or {}).items()):
        if rec.get("dead"):
            out.append({"layer": lid, "dead_since": rec.get("dead_since"),
                        "attempts_n": len(rec.get("probe_attempts") or []),
                        "last_kind": _last_kind(rec),
                        "reason": rec.get("reason") or "",
                        "probe_attempts": rec.get("probe_attempts") or []})
    return out


def resolve_forced(forced, univ_rows, queue):
    """★ W33-048 缺陷 A：把 `--force-layers` 名单解析成「必须排在队首的层」。

    旧实现 `add = [univ[i] for i in forced if i in univ and i not in have]` 有两个洞：
      ① force 写的是 `@未定位-2`，而队列里同一层的实际 id 是 `@未定位-1`（或反过来）
         → `i in univ` 命中不到，整条名单被当成 unknown 静默丢掉；
      ② 就算命中了，`i not in have` 会因为「另一个变体已在队列里」而跳过 → 提不到队首。
    现在一律按 **base 层 id** 解析；命中队列的层直接**提到队首**（不是跳过）。

    返回 (front, rest, unknown, merged)：
      front   = 要放在队首的层（名单顺序、按真实 id 去重）
      rest    = 原队列里除掉 front 后的剩余（按 base id 去重，同一个层不重复计数）
      unknown = 选层范围里找不到的名单项（不静默）
      merged  = [(名单里写的 id, 实际使用的 id)]，变体被归并时留痕
    """
    by_id = {str(r["id"]): r for r in (univ_rows or [])}
    by_base = {}
    for r in univ_rows or []:
        by_base.setdefault(base_layer_id(r["id"]), r)
    front, seen, unknown, merged = [], set(), [], []
    for raw in forced or []:
        fid = str(raw or "").strip()
        if not fid:
            continue
        row = by_id.get(fid) or by_base.get(base_layer_id(fid))
        if not row:
            unknown.append(fid)
            continue
        rid = str(row["id"])
        if rid != fid:
            merged.append((fid, rid))
        if rid in seen:
            continue
        seen.add(rid)
        front.append(row)
    front_bases = {base_layer_id(x) for x in seen}
    rest = [r for r in (queue or [])
            if str(r["id"]) not in seen and base_layer_id(r["id"]) not in front_bases]
    return front, rest, unknown, merged


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-shards", type=int, default=250,
                    help="matrix job 上限 256，留余量")
    ap.add_argument("--force-layers", default="",
                    help="逗号分隔的层 id：**即使已判完成也强制重跑**（补 cancelled 片 / 口径差）")
    # ★ 重试上限（2026-10-31 用户立规）：已判 upstream_unstable 的层**默认不进待采队列**，
    #   否则同一个层会连续吃掉 3 轮 CI。要再试必须显式点名。
    ap.add_argument("--unstable-log", default=os.path.join(ROOT, "analysis", "04b-attempt-log.json"),
                    help="逐层尝试账本（attempt_log.py 产物）；不存在 = 不剔除")
    ap.add_argument("--force-unstable-layer", default="",
                    help="逗号分隔的层 id：即使已到重试上限也照旧排进待采队列（「仍要试」的显式开关）")
    ap.add_argument("--max-attempts", type=int, default=3, help="连续失败上限（默认 3）")
    ap.add_argument("--probe-attempts", type=int, default=PROBE_ATTEMPTS,
                    help="探针复探次数（第 4 项，默认 %d；全失败才判 dead）" % PROBE_ATTEMPTS)
    ap.add_argument("--reprobe-dead-prev-plan", default="",
                    help="上一轮 plan json：其中判 dead 的层**重新复探**，成功即回到待采队列")
    a = ap.parse_args(argv)
    allow = resolve_allowlist(a.force_layers, a.force_unstable_layer)

    from worker_core import load_policy, select_layers, base_layer_id   # noqa: E402
    pol = load_policy(a.stage)
    sel = dict(pol.get("select") or {})
    # 计划阶段必须做 skip_done（这是「不重采」的唯一开关）；layers 显式清单不算续采
    sel["skip_done"] = True
    try:
        layers = _retry(lambda: select_layers(a.stage, limit=0, policy=dict(pol, select=sel)),
                        "select_layers(%s)" % a.stage)
    except Exception as e:  # noqa: BLE001
        print("::error::扫 Releases 失败，拒绝「扫不全 → 当没采过」地盲切计划：%s" % str(e)[:200])
        return 4
    # ★ 已采判定要用**基础步**的 tag 命名空间（04b 复用 collect-step04-<layer> 的 tag），
    #   否则 04b 永远判「一层都没采过」→ 全量重采 320 层。
    base = str(pol.get("done_from") or a.stage)
    if base != a.stage:
        try:
            from worker_core import done_layers      # noqa: E402
            done = _retry(lambda: set(done_layers(base)), "done_layers(%s)" % base)
            b0 = len(layers)
            layers = [r for r in layers if r["id"] not in done]
            print("⏭ %s 已有 %d 层完成 → 待采 %d 层" % (base, b0 - len(layers), len(layers)))
        except Exception as e:  # noqa: BLE001
            # 扫不全就不许切计划：盲切的结果是把已采层重采一遍（几百小时带宽）
            print("::error::done_layers(%s) 连试 3 次都失败：%s" % (base, str(e)[:200]))
            return 4
    # ★ 强制重跑名单：done_layers 判「完成」只看 tag+checkpoint，可 cancelled 片里的层
    #   会留下「单元 done_units 标完成、产物没上传」或「计划期口径差」的半截状态 ——
    #   这类层若跟着 skip_done 走，缺口就永久钉死。所以允许显式点名强制重跑，
    #   并且排在**最前**（大层先起跑，早拿到新 checkpoint，不至于又撞 350 分钟上限）。
    # ★ 重试上限：已判 upstream_unstable（连续 N 次超时/503/非 JSON 且无进展）的层默认剔除。
    #   只在「自动排进队列」这一步生效：--force-layers 点名的层下面还会被加回来（人比规则大）。
    excluded_unstable = []
    if a.max_attempts and a.unstable_log and os.path.exists(a.unstable_log):
        try:
            import attempt_log as _al                # noqa: E402
            _log = json.load(open(a.unstable_log, encoding="utf-8"))
            _sum = _al.summarize(_log.get("attempts") or [], a.max_attempts)
            _force = allow["forced_unstable"]
            ids_now = [r["id"] for r in layers]
            keep, excluded_unstable, forced_back = _al.partition_queue(ids_now, _sum, _force, a.max_attempts)
            keep_set = set(keep)
            layers = [r for r in layers if r["id"] in keep_set]
            for x in excluded_unstable:
                print("::warning::⛔ %s 已到重试上限（%d 次：%s，累计 %.1f 分钟）→ 默认不排；"
                      "仍要试请 --force-unstable-layer %s"
                      % (x["layer"], x["attempts_n"], "/".join(x.get("kinds") or []),
                         x.get("elapsed_min") or 0, x["layer"]))
            if excluded_unstable:
                print("⛔ 剔除 %d 层 upstream_unstable（连续失败已达上限，不再吃 CI）"
                      % len(excluded_unstable))
            if forced_back:
                print("★ 显式保留 %d 层「仍要试」的 unstable 层：%s"
                      % (len(forced_back), ", ".join(forced_back[:5])))
        except Exception as e:                       # noqa: BLE001
            print("::warning::尝试账本读取失败（%s）：本轮不剔除 unstable 层" % str(e)[:160],
                  file=sys.stderr)
    forced = allow["forced"]
    forced_merged = []
    if forced:
        have = {r["id"] for r in layers}
        try:
            univ_l = _retry(lambda: select_layers(
                a.stage, limit=0, policy=dict(pol, select=dict(sel, skip_done=False))),
                "select_layers(%s, 全量)" % a.stage)
        except Exception as e:  # noqa: BLE001
            print("::error::强制重跑名单无法核对（扫 Releases 失败）：%s" % str(e)[:200])
            return 4
        # ★ W33-048：按 base 层 id 解析；命中队列的提到队首（旧版会因另一个变体已在队列里而跳过）
        front, rest, unknown, merged = resolve_forced(forced, univ_l, layers)
        forced_merged = merged
        already = sum(1 for r in front if r["id"] in have)
        layers = front + rest
        if merged:
            print("⚠️ force 名单里有 %d 条是 `@变体` 写法，已归并到真实层 id：%s"
                  % (len(merged), "; ".join("%s→%s" % (x, y) for x, y in merged[:5])),
                  file=sys.stderr)
        if unknown:
            print("⚠️ 强制重跑名单里有 %d 层不在本步选层范围内（已忽略，不静默）：%s"
                  % (len(unknown), ", ".join(unknown[:5])), file=sys.stderr)
        print("★ 强制重跑 %d 层（其中 %d 层原本已在队列、已提到队首；%d 层原本被判完成）"
              % (len(front), already, len(front) - already))
    ids = [r["id"] for r in layers]
    shards = [{"shard": i // a.size, "layers": ids[i:i + a.size]}
              for i in range(0, len(ids), a.size)]
    rows_by_id = {r["id"]: (r.get("expect") or 0) for r in layers}
    # ★ D3：计划阶段探上游实时行数（returnCountOnly），写成 expect_live 供收尾对账用双分母。
    # ★ 第 4 项：上一轮判 dead 的层先回到队列复探（复探成功即「回到待采」，不许留在 dead）
    reprobed = []
    if a.reprobe_dead_prev_plan and os.path.exists(a.reprobe_dead_prev_plan):
        try:
            prev = json.load(open(a.reprobe_dead_prev_plan, encoding="utf-8"))
            dead_ids = [x.get("layer") for x in (prev.get("probe_dead") or []) if x.get("layer")]
            have = {r["id"] for r in layers}
            univ_all = _retry(lambda: select_layers(
                a.stage, limit=0, policy=dict(pol, select=dict(sel, skip_done=False))),
                "select_layers(%s, 复探)" % a.stage)
            univ_map = {r["id"]: r for r in univ_all}
            reprobed = [univ_map[i] for i in dead_ids if i in univ_map and i not in have]
            layers = reprobed + layers
            ids = [r["id"] for r in layers]
            shards = [{"shard": i // a.size, "layers": ids[i:i + a.size]}
                      for i in range(0, len(ids), a.size)]
            rows_by_id = {r["id"]: (r.get("expect") or 0) for r in layers}
            print("🔁 复探上一轮 dead 的 %d 层（进队列最前）：%s"
                  % (len(reprobed), ", ".join(x["id"] for x in reprobed[:5])))
        except Exception as e:                        # noqa: BLE001
            print("::warning::复探上一轮 dead 失败（%s）：本轮不捞 dead 层" % str(e)[:160], file=sys.stderr)

    expect_live, probe_failed, probe_results = ({}, [], {})
    if os.environ.get("PLAN_PROBE_COUNT", "1") not in ("0", "false", "no"):
        expect_live, probe_failed, probe_results = probe_live_counts(
            layers, attempts=a.probe_attempts)
        print("★ 计划阶段 returnCountOnly 探到 %d/%d 层实时行数（%d 层失败，回退快照值）"
              % (len(expect_live), len(ids), len(probe_failed)))
    plan = {"schema": "collect-plan/v1", "stage": a.stage, "size": a.size,
            "layers_n": len(ids), "shards_n": len(shards),
            "declared_rows": sum(rows_by_id.values()),
            "expect_source": "returnCountOnly@plan" if expect_live else "row_count_snapshot",
            "expect_by_layer": rows_by_id,
            "expect_live": expect_live,
            "expect_live_total": sum(expect_live.values()),
            # ★ 第 3 项：列表与计数同源（都取完整 len）——只许在展示层截断并写明「显示前 50 / 共 N」
            "probe_failed": probe_failed, "probe_failed_n": len(probe_failed),
            # ★ 第 5 项：失败按类别分桶，400（可修）与 404/500（上游坏）互不串
            "probe_failed_by_kind": _failed_by_kind(probe_results, probe_failed),
            # ★ 第 4 项：dead 必须有时间证据；复探成功的不进 dead
            "probe_dead": _dead_entries(probe_results),
            "probe_dead_n": len(_dead_entries(probe_results)),
            # ★ 第 6 项：每条探针结果落解析证据（count 是怎么解析出来的、上游键名、失败原因）
            "probe_results": probe_results,
            "unit_rows": pol.get("unit_rows"), "workers": pol.get("workers"),
            "done_from": str(pol.get("done_from") or a.stage),
            "tag": pol.get("tag"), "order": sel.get("order"),
            "forced_layers": [r["id"] for r in layers[:len(forced)]],
            "forced_layers_raw": forced,
            "forced_layers_merged": [{"raw": x, "resolved": y} for x, y in forced_merged],
            "shards": shards,
            "excluded_unstable": excluded_unstable,
            "excluded_unstable_n": len(excluded_unstable),
            "retry_cap": {"max_attempts": a.max_attempts, "attempt_log": os.path.relpath(
                a.unstable_log, ROOT) if a.unstable_log else ""}}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(plan, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    shown = {k: v for k, v in plan.items() if k not in ("shards", "probe_results")}
    # ★ 第 3 项：**只在展示层**截断，且必须显式写「显示前 N / 共 M」
    if plan["probe_failed_n"] > DISPLAY_LIMIT:
        shown["probe_failed"] = plan["probe_failed"][:DISPLAY_LIMIT]
        shown["probe_failed_display"] = "显示前 %d / 共 %d" % (DISPLAY_LIMIT, plan["probe_failed_n"])
    if plan["probe_dead_n"] > DISPLAY_LIMIT:
        shown["probe_dead"] = plan["probe_dead"][:DISPLAY_LIMIT]
        shown["probe_dead_display"] = "显示前 %d / 共 %d" % (DISPLAY_LIMIT, plan["probe_dead_n"])
    print(json.dumps(shown, ensure_ascii=False))
    if len(shards) > a.max_shards:
        print("::error::片数 %d 超过上限 %d" % (len(shards), a.max_shards), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
