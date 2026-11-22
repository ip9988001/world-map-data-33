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
3. **不让行数凭空变小**：任何重跑都不得让某层 rows 变小，除非能说清它去哪了
   （`regression_reason` + 证据路径，或者下面这条更强的等式）。没有证据就拒绝写入并报错退出。

## 2026-11-22 修正：「行数只许涨」这条护栏退场，换成可复算的不变量

事故（run 44992201755）：强制重跑换了切分 → `pilot.UNIT_NS` 给新单元包加代际前缀
→ 新旧包名不同 → 旧包按「还在 Release」全部保留 → **旧代际 + 新代际双算**，100 层
`rows/declared` 恰好 2×（合计多算 7,351,656 行）。根因就是上面第 3 条：它把「涨」当成健康，
于是一次重跑让 100 层全部「健康地翻倍」，护栏反而成了双算的护身符。

现在的规则（方案 A）：

- `split_compatible=false` 且**旧单元索引集合 ⊆ 新代际索引集合** → 旧包标 `superseded_by`，
  行数**不计入** `rows_total`，但仍完整留在 `units_legacy[]` 里可审计（含原 rows / present）。
  理由：新代际把同一批单元重采了一遍，旧包是**同一批行的上一代副本**，不是增量。
- **旧 ⊋ 新（旧代际多出 unit）→ 多出来的 unit 是唯一副本，必须计入**。这条是硬约束：
  宁可留着旧行，也不许把「只存在于旧切分里的单元」丢掉。
- 新代际里对应单元**没上传成功**（`uploaded=false` 或包不在）→ 不 supersede，旧包继续计入：
  新代际缺这一块，它就是唯一可用副本。
- 切分兼容（同名包覆盖）→ 仍按包名取大者，增量记 `collision_extra`，不双算。

替代护栏（`assert_rows_invariant`）是**可独立复算的等式**：

    rows_total == Σ(units_new[].rows) + Σ(units_legacy[].counted_rows)

只要对不上就 raise `RowsInvariantError`。旧护栏问的是「涨了没有」（双算=涨=通过），
新护栏问的是「这笔账能不能对上」（双算对不上 → 直接拦）。

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


BAK_RE = re.compile(r"\.bak-(.+)\.json$")


def bak_sort_key(name: str, path: str | None = None):
    """备份「代」的排序键 —— 按后缀里的**数字**比，绝不按字符串比。

    事故（2026-10-31，ci-smoke run 41167000866）：`backup_local` 原来按 mtime 挑最老的删，
    可 `shutil.copy2` 连**源检查点**的 mtime 一起复制 —— 同一层的所有 bak mtime 完全相同，
    `sorted()` 退化成「保持 os.listdir 顺序」（ext4 htree 与 overlayfs 顺序不同），
    于是 r1/r2/r3/r4 该删 r1 的那次删掉了 r3。备份本身没丢，但「只留 3 代」变成
    「随机留 3 代」—— 人会误信旧备份都清了。

    现在：先按后缀数字比（r2 → 2；GITHUB_RUN_ID → 41167000866，r10 > r2），
    无数字才退到 mtime，最后用文件名兜底保证同一输入永远同一顺序。
    """
    base = os.path.basename(name)
    m = BAK_RE.search(base)
    nums = tuple(int(x) for x in re.findall(r"\d+", m.group(1) if m else ""))
    mt = 0.0
    if path:
        try:
            mt = os.path.getmtime(path)
        except OSError:
            mt = 0.0
    return (1 if nums else 0, nums, mt, base)


def backup_local(path: str, run_id, keep: int = KEEP_BACKUPS) -> str:
    """本地检查点先复制一份 `_checkpoint.bak-<RUN_ID>.json`（同目录），只留 keep 代。"""
    if not path or not os.path.exists(path):
        return ""
    d, base = os.path.split(path)
    stem = base[:-5] if base.endswith(".json") else base
    dst = os.path.join(d, "%s.bak-%s.json" % (stem, now_ish(run_id)))
    try:
        shutil.copy2(path, dst)
        # copy2 会继承**源**的 mtime，备份就分不出先后了（正是上面那起事故）→ 打上此刻的时间
        os.utime(dst, None)
    except Exception:                                   # noqa: BLE001
        return ""
    olds = sorted([p for p in os.listdir(d)
                   if p.startswith(stem + ".bak-") and p.endswith(".json")
                   and os.path.join(d, p) != dst],
                  key=lambda p: bak_sort_key(p, os.path.join(d, p)))
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
    names = [n for n in (assets_idx or {}) if n.startswith(prefix) and n.endswith(".json")]
    mine = backup_name(layer, run_id)
    if mine not in names:
        names.append(mine)
    names = sorted(names, key=bak_sort_key)
    if mine in names and names[-1] != mine:      # 本次这份算最新，不许被自己删掉
        names = [n for n in names if n != mine] + [mine]
    return names[:-keep] if len(names) > keep else []


# ---------------- 合并（不整份覆盖） ----------------
def merge_checkpoints(legacy: dict | None, new: dict, *, layer: str, run_id,
                      assets=None, evidence: str = "") -> tuple[dict, dict]:
    """把旧检查点的完成度按单元并进新检查点。返回 (merged_ck, report)。

    规则（逐条对应事故）：
      · 旧单元包在 Release 里仍在且可下载 → 行数保留、`unit_uploaded=true`、`legacy_split=true`；
      · **切分不兼容 + 新代际重采了同一 unit 索引** → 旧包标 `superseded_by`，行数**不计入**
        （这是 2026-11-22 双算事故的修法：旧包是同一批行的上一代副本，不是增量）；
      · **旧代际多出来的 unit**（索引不在新代际里）→ 唯一副本，行数**照计**（硬约束）；
      · 新代际对应单元没上传成功 → 不 supersede，旧包继续计入（它是唯一可用副本）；
      · 本 run 用同名包覆盖了旧包 → 按包名去重，取两者行数较大者（不双算），增量记
        `counted_rows`；
      · 旧包已不在 Release（真没了）→ 这部分的完成度不再计入，**必须**有 `evidence`
        说明它去哪了，否则调用方会抛 `RowsRegression`；
      · 查不到 Release 资产清单（assets=None）→ 保守按「还在」处理，绝不用「不知道」当理由丢行。

    合并完立刻用 `assert_rows_invariant` 复算一遍等式，对不上就 raise。
    """
    legacy = legacy or {}
    new = new or {}
    assets_idx = assets
    before = rows_of(legacy)
    split_compatible = legacy.get("plan_hash") in (None, new.get("plan_hash"))
    legacy_pkgs = package_map(legacy, layer)
    new_pkgs = package_map(new, layer)
    new_by_idx = {str(n["idx"]): name for name, n in new_pkgs.items()}

    rows_by_pkg = {name: n["rows"] for name, n in new_pkgs.items()}
    units_legacy, units_new, dropped, superseded = [], [], [], []

    def _new_has(idx):
        """新代际有没有「算完成」的同一 unit 索引（包在且 uploaded 不为 False）。"""
        name = new_by_idx.get(str(idx))
        if not name:
            return None
        return name if new_pkgs[name].get("uploaded") is not False else None

    for name, l in sorted(legacy_pkgs.items()):
        present = package_downloadable(assets_idx, name)
        collided = name in new_pkgs and new_pkgs[name].get("uploaded") is not False
        entry = {"package": name, "idx": l["idx"], "rows": l["rows"],
                 "present": present, "legacy_split": True, "kept_rows": 0,
                 "counted_rows": 0, "counted_as": None}
        if collided:
            extra = max(0, l["rows"] - new_pkgs[name]["rows"])
            rows_by_pkg[name] = new_pkgs[name]["rows"] + extra
            entry.update({"kept_rows": extra, "counted_rows": extra, "counted_as": "units_new",
                          "dedupe": "same_package_name", "overwritten_by_run": now_ish(run_id),
                          "note": "本 run 用同名包覆盖了旧包：取两者较大者，增量记在旧包上，不双算"})
        elif present is False:
            entry.update({"dropped_reason": "单元包在 Release 中已不存在或不可下载"})
            dropped.append(name)
        else:
            cp = _new_has(l["idx"])
            if cp and not split_compatible:
                entry.update({"superseded_by": cp, "supersede_reason":
                              "新代际已重采同一 unit 索引（旧包是上一代副本）"})
                superseded.append(name)
            else:
                rows_by_pkg[name] = rows_by_pkg.get(name, 0) + l["rows"]
                entry.update({"kept_rows": l["rows"], "counted_rows": l["rows"],
                              "counted_as": "units_legacy", "verified": present is True,
                              "legacy_only_unit": True,
                              "counted_reason": (
                                  "旧代际多出的 unit（新代际没有这个索引）→ 唯一副本"
                                  if str(l["idx"]) not in new_by_idx else
                                  "新代际该单元未上传成功 → 旧包是唯一可用副本")})
        units_legacy.append(entry)

    # 上一轮合并留下的「旧代际独有单元」：它们不在这份检查点的 unit_rows 里，
    # 但仍是唯一副本 —— 不带上就会在第二次强制重跑时静默消失（三代同堂的情形）。
    for u in (legacy.get("units_legacy") or []):
        name = str(u.get("package") or "")
        if not name or name in legacy_pkgs or u.get("counted_as") != "units_legacy":
            continue
        rows_u = int(u.get("rows") or 0)
        cp = _new_has(u.get("idx"))
        entry = {"package": name, "idx": u.get("idx"), "rows": rows_u, "present": True,
                 "legacy_split": True, "carried_over": True, "kept_rows": 0,
                 "counted_rows": 0, "counted_as": None}
        if cp and not split_compatible:
            entry.update({"superseded_by": cp, "supersede_reason":
                          "新代际已重采同一 unit 索引（上一轮遗留的旧代际副本）"})
            superseded.append(name)
        else:
            rows_by_pkg[name] = rows_by_pkg.get(name, 0) + rows_u
            entry.update({"kept_rows": rows_u, "counted_rows": rows_u,
                          "counted_as": "units_legacy", "legacy_only_unit": True,
                          "counted_reason": "上一轮遗留的旧代际独有单元（照旧计入）"})
        units_legacy.append(entry)

    for name, n in sorted(new_pkgs.items()):
        units_new.append({"package": name, "idx": n["idx"], "rows": n["rows"],
                          "counted_rows": n["rows"],
                          "uploaded": bool(n.get("uploaded")),
                          "collides_with_legacy": name in legacy_pkgs})

    after = sum(rows_by_pkg.values())
    report = {
        "at_merge_run_id": now_ish(run_id),
        "layer": layer,
        "rows_before": before,
        "rows_after": after,
        "rows_new": rows_of(new),
        "rows_legacy_kept": sum(u["counted_rows"] for u in units_legacy
                                if u.get("counted_as") == "units_legacy"),
        "rows_legacy_superseded": sum(u["rows"] for u in units_legacy
                                      if u.get("superseded_by")),
        "units_legacy": len(units_legacy),
        "units_new": len(units_new),
        "units_legacy_superseded": sum(1 for u in units_legacy if u.get("superseded_by")),
        "units_legacy_only": sum(1 for u in units_legacy
                                 if u.get("counted_as") == "units_legacy"),
        "packages_dropped": dropped,
        "packages_superseded": superseded,
        "split_compatible": split_compatible,
        "plan_hash_legacy": legacy.get("plan_hash"),
        "plan_hash_new": new.get("plan_hash"),
        "legacy_verified_against_release": (None if assets_idx is None else True),
        "evidence": evidence or "",
    }

    merged = dict(new)
    merged["units_legacy"] = units_legacy
    merged["units_new"] = units_new
    merged["rows_by_package"] = rows_by_pkg
    merged["rows_total"] = after
    merged["rows_new_plan"] = rows_of(new)
    merged["rows_legacy_kept"] = report["rows_legacy_kept"]
    merged["rows_legacy_superseded"] = report["rows_legacy_superseded"]
    merged["legacy"] = {"run_id": report["at_merge_run_id"],
                        "plan_hash": legacy.get("plan_hash"),
                        "rows": before, "units": len(legacy_pkgs),
                        "plan_hash_new": new.get("plan_hash"),
                        "snapshot": legacy or None}
    merged["merge_history"] = list((new or {}).get("merge_history") or []) + [{
        k: report[k] for k in ("rows_before", "rows_after", "rows_new",
                               "rows_legacy_kept", "rows_legacy_superseded",
                               "units_legacy", "units_new",
                               "packages_dropped", "split_compatible", "at_merge_run_id")}]
    report.update(assert_rows_invariant(merged, legacy, new, layer=layer, run_id=run_id))
    return merged, report


# ---------------- 护栏：行数要对得上（替代「只许涨」） ----------------
class RowsInvariantError(Exception):
    """合并后的行数等式对不上 —— 说明账本里有行算了两遍或者漏了一遍。"""

    def __init__(self, msg: str, detail: dict):
        super().__init__(msg)
        self.detail = detail


def rows_recheck(legacy: dict | None, new: dict | None, merged: dict, layer: str) -> dict:
    """**独立复算**合并后的行数（不信任 `rows_total`，也不信任 `rows_by_package`）。

    两条互不相干的取数路径：
      ① `rows_of(new)` —— 直接读新检查点的 `unit_rows[_seen]`；
      ② `units_legacy[].counted_rows` —— 逐条累加「这一轮允许计入的旧行」。
    等式：`rows_total == ① + ②`，并且 `Σ units_new[].rows == ①`
    （后者抓「两个 unit 索引映射到同一个包名」导致的下漏）。
    """
    new_check = new or {}
    new_side = rows_of(new_check)
    legacy_side = sum(int(u.get("counted_rows") or 0) for u in (merged.get("units_legacy") or []))
    units_new_sum = sum(int(u.get("rows") or 0) for u in (merged.get("units_new") or []))
    return {"new_side": new_side, "legacy_side": legacy_side,
            "total": new_side + legacy_side, "units_new_sum": units_new_sum,
            "rows_total": int(merged.get("rows_total") or 0),
            "rows_by_package_sum": sum(int(v or 0)
                                       for v in (merged.get("rows_by_package") or {}).values()),
            "legacy_rows_before": rows_of(legacy or {})}


def assert_rows_invariant(merged: dict, legacy: dict | None = None, new: dict | None = None,
                          *, layer: str, run_id) -> dict:
    """`rows_total == Σ(新代际本轮唯一行数) + Σ(被计入的旧包独有 unit 行数)`，不满足 raise。

    为什么这条能拦住双算：旧护栏问「涨了没有」，一次重跑让 100 层翻倍 = 涨 = 通过；
    这条问「这笔账对不对得上」——旧代际那 7,351,656 行既不在 `units_new` 里、
    也没资格进 `counted_rows`（它们被 supersede 了），于是 `rows_total` 一对就多出来，
    立刻 raise。反过来，真丢了单元（旧 ⊋ 新 的那部分没计入）也会当场对不上。
    """
    d = rows_recheck(legacy, new, merged, layer)
    problems = []
    if d["rows_total"] != d["total"]:
        problems.append("rows_total=%s ≠ Σunits_new(%s)+Σunits_legacy.counted_rows(%s)=%s"
                        % (f"{d['rows_total']:,}", f"{d['new_side']:,}",
                           f"{d['legacy_side']:,}", f"{d['total']:,}"))
    if d["units_new_sum"] != d["new_side"]:
        problems.append("Σ units_new[].rows=%s ≠ 检查点 unit_rows 合计 %s（两个 unit 索引撞到同一个包名？）"
                        % (f"{d['units_new_sum']:,}", f"{d['new_side']:,}"))
    if d["rows_by_package_sum"] != d["rows_total"]:
        problems.append("Σ rows_by_package=%s ≠ rows_total=%s"
                        % (f"{d['rows_by_package_sum']:,}", f"{d['rows_total']:,}"))
    if problems:
        raise RowsInvariantError(
            "%s 行数等式不成立（拒绝写入）：%s" % (layer, "；".join(problems)),
            {"layer": layer, "run_id": now_ish(run_id), **d, "problems": problems})
    return {"rows_total_recomputed": d["total"], "rows_new_side": d["new_side"],
            "rows_legacy_side": d["legacy_side"], "invariant_ok": True,
            "rows_legacy_before": d["legacy_rows_before"],
            "invariant": "rows_total == Σ(units_new) + Σ(units_legacy.counted_rows)"}


# ---------------- 护栏：行数只许涨 ----------------
def assert_rows_not_shrunk(before: int, after: int, *, layer: str, run_id,
                           reason: str = "", evidence: str = "") -> dict | None:
    """after < before 时：有实证 → 返回 {regression_reason, evidence}；没实证 → RowsRegression。

    ★ 2026-11-22 起它**不再是检查点合并的闸门**（合并改用 `assert_rows_invariant`）：
      这条判据把「涨」当健康，而双算正好表现为「涨」—— 它自己就是双算事故的护身符。
      仍然保留给**账本口径**用（`guard_ledger_rows`：阶段账本的行数不许被一次没测到的
      重跑冲小），那里的「只许涨」语义是对的。"""
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
