#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""行数单调护栏 —— 重跑不许把「已完成度的证据」变小。

## 事故（2026-10-30 22:23Z，run 41126178216）
NAD view 层（`s_Points_from_National_Address_Database_view_FeatureServer_0`）在 force 补采里
被新建的「1 unit / 0 行」检查点**整份覆盖**：`_fetch_ckpt_asset` 一发现 `plan_hash` 不同就
返回 None，pilot 于是当成第一次跑，跑完 `--clobber` 把 Release 上那份 68 单元、39,875,268 行
的检查点换成了 441 字节的「0 行」。68 个 `u000NN.tar.gz` 一个都没少，但账本这层从
partial(39,875,268) 掉成 failed(0)，`ledger_rebuild` 的 rows 因此少 33.4M。

数据没丢，丢的是**判据**。所以这里立三条规矩：

1. **覆盖前先备份**：旧检查点先另存成 `<layer>-checkpoint.bak-<RUN_ID>.json`（保留 3 代）。
2. **按单元合并，不整份覆盖**：旧单元的包名若在 Release 里仍在且可下载（state=uploaded、
   size>0），其 `unit_uploaded=true` 与行数**必须保留**，并标 `legacy_split=true`；
   新旧切分不兼容时两边都记（`units_new[]` / `units_legacy[]`），行数按**包名**去重后求和，
   不靠猜、不靠下标对齐。
3. **行数只许涨**：任何重跑都不得让某层 rows 变小，除非有实证证明旧记录是错的
   （`regression_reason` + 证据路径）。没有证据就拒绝写入并报错退出。

本模块是纯函数 + 薄 IO：pilot（检查点）与 ledger_merge（账本）共用同一套判定，
两处口径不一致时以本模块为准。
"""
from __future__ import annotations

import json
import os
import re
import shutil

KEEP_BACKUPS = 3
PKG_IDX_RE = re.compile(r"-u(\d{5})")


class RowsRegression(Exception):
    """行数变小且拿不出实证 —— 调用方必须拒绝写入并报错退出。"""

    def __init__(self, msg: str, detail: dict):
        super().__init__(msg)
        self.detail = detail


def now_ish(run_id) -> str:
    return str(run_id or "local")


# ---------------- 基础口径 ----------------
def unit_rows_map(ck: dict) -> dict:
    """每单元行数（与 pilot/账本同口径：unit_rows_seen 优先，回退 unit_rows）。"""
    ck = ck or {}
    src = ck.get("unit_rows_seen") or ck.get("unit_rows") or {}
    out = {}
    for k, v in src.items():
        try:
            out[str(k)] = int(v or 0)
        except (TypeError, ValueError):
            out[str(k)] = 0
    return out


def rows_of(ck: dict) -> int:
    """检查点口径的总行数（pilot 收尾时算的就是这个数）。"""
    return sum(unit_rows_map(ck).values())


def pkg_name(layer: str, idx, ck: dict | None = None) -> str:
    """单元包名（Release 上的资产名）。

    优先级：① 检查点里记下的真实上传名 `unit_package[str(idx)]`（带代际前缀时唯一正确的一项）；
    ② 从本地 part 文件名反推（`part-u00023-000.ndjson.gz` → `…-u00023.tar.gz`）；
    ③ 按单元下标兜底。
    `unit_ns` = 切分不兼容时给新单元包加的代际前缀（`r<planhash8>-`），避免 --clobber 盖旧包。"""
    ck = ck or {}
    explicit = (ck.get("unit_package") or {}).get(str(idx))
    if explicit:
        return explicit
    ns = str(ck.get("unit_ns") or "")
    files = (ck.get("unit_files") or {}).get(str(idx)) or []
    for f in files:
        m = PKG_IDX_RE.search(os.path.basename(f or ""))
        if m:
            return "%s-%su%s.tar.gz" % (layer, ns, m.group(1))
    try:
        return "%s-%su%05d.tar.gz" % (layer, ns, int(idx))
    except (TypeError, ValueError):
        return ""


def package_map(ck: dict, layer: str) -> dict:
    """包名 → {idx, rows, uploaded}。包名是唯一的去重键（不靠下标对齐）。"""
    out = {}
    for k, rows in unit_rows_map(ck).items():
        name = pkg_name(layer, k, ck)
        if not name:
            continue
        up = ((ck or {}).get("unit_uploaded") or {}).get(k)
        rec = out.setdefault(name, {"idx": k, "rows": 0, "uploaded": True})
        rec["rows"] = max(rec["rows"], rows)
        rec["uploaded"] = bool(rec["uploaded"] and up is not False)
    return out


def assets_index(assets) -> dict:
    """把 `gh release view --json assets` 的结果（或名字列表）整理成 name → {size,state}。"""
    out = {}
    for a in assets or []:
        if isinstance(a, str):
            out[a] = {"size": None, "state": "uploaded"}
        elif isinstance(a, dict) and a.get("name"):
            out[a["name"]] = {"size": a.get("size"), "state": a.get("state") or "uploaded"}
    return out


def package_downloadable(assets_idx: dict | None, name: str) -> bool | None:
    """True=在且可下载（uploaded、size>0）；False=明确不在；None=查不到（不敢当没在）。"""
    if assets_idx is None:
        return None
    a = assets_idx.get(name)
    if not a:
        return False
    if str(a.get("state") or "uploaded") != "uploaded":
        return False
    size = a.get("size")
    return True if size is None else int(size) > 0


# ---------------- 备份（覆盖前） ----------------
def backup_name(layer: str, run_id) -> str:
    return "%s-checkpoint.bak-%s.json" % (layer, now_ish(run_id))


def backup_local(path: str, run_id, keep: int = KEEP_BACKUPS) -> str:
    """本地检查点先复制一份 `_checkpoint.bak-<RUN_ID>.json`（同目录），只留 keep 代。"""
    if not path or not os.path.exists(path):
        return ""
    d, base = os.path.split(path)
    stem = base[:-5] if base.endswith(".json") else base
    dst = os.path.join(d, "%s.bak-%s.json" % (stem, now_ish(run_id)))
    try:
        shutil.copy2(path, dst)
    except Exception:                                   # noqa: BLE001
        return ""
    olds = sorted([p for p in os.listdir(d)
                   if p.startswith(stem + ".bak-") and p.endswith(".json")
                   and os.path.join(d, p) != dst],
                  key=lambda p: os.path.getmtime(os.path.join(d, p)))
    for p in olds[:max(0, len(olds) - (keep - 1))]:
        try:
            os.remove(os.path.join(d, p))
        except Exception:                               # noqa: BLE001
            pass
    return dst


def backup_assets_to_delete(assets_idx: dict, layer: str, run_id,
                            keep: int = KEEP_BACKUPS) -> list:
    """该层历史上留了哪些 bak 资产、该删哪几个（只留最近 keep 代，含本次这份）。"""
    prefix = "%s-checkpoint.bak-" % layer
    names = sorted([n for n in (assets_idx or {}) if n.startswith(prefix) and n.endswith(".json")])
    if backup_name(layer, run_id) not in names:
        names.append(backup_name(layer, run_id))
    return names[:-keep] if len(names) > keep else []


# ---------------- 合并（不整份覆盖） ----------------
def merge_checkpoints(legacy: dict | None, new: dict, *, layer: str, run_id,
                      assets=None, evidence: str = "") -> tuple[dict, dict]:
    """把旧检查点的完成度按单元并进新检查点。返回 (merged_ck, report)。

    规则（逐条对应事故）：
      · 旧单元包在 Release 里仍在且可下载 → 行数保留、`unit_uploaded=true`、`legacy_split=true`；
      · 本 run 用同名包覆盖了旧包 → 按包名去重，取两者行数较大者（不双算），并标
        `overwritten_by_run`；
      · 旧包已不在 Release（真没了）→ 这部分的完成度不再计入，**必须**有 `evidence`
        说明它去哪了，否则 `assert_rows_not_shrunk` 会拦住；
      · 查不到 Release 资产清单（assets=None）→ 保守按「还在」处理，绝不用「不知道」当理由丢行。
    """
    legacy = legacy or {}
    new = new or {}
    assets_idx = assets
    before = rows_of(legacy)
    legacy_pkgs = package_map(legacy, layer)
    new_pkgs = package_map(new, layer)
    merged_rows_by_pkg, units_legacy, units_new = {}, [], []
    dropped = []

    for name, l in sorted(legacy_pkgs.items()):
        present = package_downloadable(assets_idx, name)
        collided = name in new_pkgs and new_pkgs[name].get("uploaded") is not False
        entry = {"package": name, "idx": l["idx"], "rows": l["rows"],
                 "present": present, "legacy_split": True, "kept_rows": 0}
        if collided:
            rows = max(l["rows"], new_pkgs[name]["rows"])
            merged_rows_by_pkg[name] = rows
            entry.update({"kept_rows": 0, "counted_as": "units_new",
                          "dedupe": "same_package_name", "overwritten_by_run": now_ish(run_id),
                          "note": "本 run 用同名包覆盖了旧包：行数取两者较大者，不双算"})
        elif present is False:
            entry.update({"kept_rows": 0, "counted_as": None,
                          "dropped_reason": "单元包在 Release 中已不存在或不可下载"})
            dropped.append(entry["package"])
        else:
            merged_rows_by_pkg[name] = l["rows"]
            entry.update({"kept_rows": l["rows"], "counted_as": "units_legacy",
                          "verified": present is True})
        units_legacy.append(entry)

    for name, n in sorted(new_pkgs.items()):
        merged_rows_by_pkg.setdefault(name, n["rows"])
        units_new.append({"package": name, "idx": n["idx"], "rows": n["rows"],
                          "uploaded": bool(n.get("uploaded")),
                          "collides_with_legacy": name in legacy_pkgs})

    after = sum(merged_rows_by_pkg.values())
    report = {
        "at_merge_run_id": now_ish(run_id),
        "layer": layer,
        "rows_before": before,
        "rows_after": after,
        "rows_new": rows_of(new),
        "rows_legacy_kept": sum(u["kept_rows"] for u in units_legacy),
        "units_legacy": len(units_legacy),
        "units_new": len(units_new),
        "packages_dropped": dropped,
        "split_compatible": (legacy.get("plan_hash") in (None, new.get("plan_hash"))),
        "plan_hash_legacy": legacy.get("plan_hash"),
        "plan_hash_new": new.get("plan_hash"),
        "legacy_verified_against_release": (None if assets_idx is None else True),
        "evidence": evidence or "",
    }

    merged = dict(new)
    merged["units_legacy"] = units_legacy
    merged["units_new"] = units_new
    merged["rows_by_package"] = merged_rows_by_pkg
    merged["rows_total"] = after
    merged["rows_new_plan"] = rows_of(new)
    merged["rows_legacy_kept"] = report["rows_legacy_kept"]
    merged["legacy"] = {"run_id": report["at_merge_run_id"],
                        "plan_hash": legacy.get("plan_hash"),
                        "rows": before, "units": len(legacy_pkgs),
                        "snapshot": legacy or None}
    merged["merge_history"] = list((new or {}).get("merge_history") or []) + [{
        k: report[k] for k in ("rows_before", "rows_after", "rows_new",
                               "rows_legacy_kept", "units_legacy", "units_new",
                               "packages_dropped", "split_compatible", "at_merge_run_id")}]
    return merged, report


# ---------------- 护栏：行数只许涨 ----------------
def assert_rows_not_shrunk(before: int, after: int, *, layer: str, run_id,
                           reason: str = "", evidence: str = "") -> dict | None:
    """after < before 时：有实证 → 返回 {regression_reason, evidence}；没实证 → RowsRegression。"""
    if int(after or 0) >= int(before or 0):
        return None
    detail = {"layer": layer, "run_id": now_ish(run_id), "rows_before": int(before or 0),
              "rows_after": int(after or 0),
              "delta": int(after or 0) - int(before or 0),
              "regression_reason": reason or "重跑后行数变小，未给出原因",
              "evidence": evidence or ""}
    if not evidence:
        raise RowsRegression(
            "%s 行数变小：%s → %s（少 %s 行），且没有证据路径 → 拒绝写入"
            % (layer, f"{before:,}", f"{after:,}", f"{before - after:,}"), detail)
    if not os.path.exists(evidence):
        raise RowsRegression(
            "%s 行数变小：证据路径不存在（%s）→ 拒绝写入" % (layer, evidence), detail)
    return detail


def row_regressions(old_records, new_records, evidence_map=None) -> list:
    """账本口径：逐层比对 rows，返回「变小」的层。evidence_map[layer] = 证据路径。"""
    evidence_map = evidence_map or {}
    old = {str(r.get("layer") or r.get("layer_id") or ""): r for r in (old_records or [])}
    out = []
    for r in new_records or []:
        k = str(r.get("layer") or r.get("layer_id") or "")
        if k not in old:
            continue
        b = _safe_int(old[k].get("rows"))
        a = _safe_int(r.get("rows"))
        if a >= b:
            continue
        ev = evidence_map.get(k) or r.get("row_regression_evidence") or ""
        out.append({"layer": k, "rows_before": b, "rows_after": a, "delta": a - b,
                    "regression_reason": r.get("regression_reason")
                    or "重跑后行数变小，未给出原因",
                    "evidence": ev,
                    "stage_status": old[k].get("status"), "run_status": r.get("status")})
    return out


def guard_ledger_rows(old_records, new_records, *, stage: str, run_id,
                      evidence_map=None, allow_shrink=None) -> list:
    """写账本前的总闸门：任何一层 rows 变小都要带证据，否则抛 RowsRegression。

    `allow_shrink` = {layer: evidence_path}（CLI `--row-shrink-evidence layer=path` 的解析结果）。
    返回被放行的回归清单（要写进账本 revisions，不许静默）。
    """
    evidence_map = dict(evidence_map or {})
    evidence_map.update(allow_shrink or {})
    regs = row_regressions(old_records, new_records, evidence_map)
    bad = [r for r in regs if not (r["evidence"] and os.path.exists(r["evidence"]))]
    if bad:
        raise RowsRegression(
            "账本 %s 拒绝写入：有 %d 层行数变小且无证据：%s"
            % (stage, len(bad), ", ".join("%s(%s→%s)" % (b["layer"], b["rows_before"],
                                                          b["rows_after"]) for b in bad[:5])),
            {"stage": stage, "run_id": now_ish(run_id), "regressions": bad})
    return regs


def _safe_int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def load_json(path: str):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:                                   # noqa: BLE001
        return None
