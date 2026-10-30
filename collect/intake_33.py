#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三仓 intake v1 —— 把已发布层资产按 SCHEMA 2.0 归一化，分流成 addr / aux_* 三表。

契约要点（照二仓 schema/SCHEMA.json rev2 + 三仓 INTAKE-33 草案）：
  · 目标字段名逐字取自 SCHEMA 2.0；本文件不定义任何新规范字段（只用 19 主字段 + 4 溯源列）
  · **宗地绝不出地址行**：parcel_situs 的行只进 aux_parcel。
    实测 55 个宗地层里 12 层 situs 与 mailing 字段并存，冲突率 100% —— mailing 多是业主
    外地/PO 信箱，与房产地址天然不同，拿 mailing 当 situs 会把地址系统性写错，所以宗地层
    一行都不许进 addr（见测试 test_parcel_never_emits_addr）。
  · 线层（street_line）只进 aux_street：没有门牌号，天然不可能是地址行。
  · 硬门禁不过的行 → REJECT.json（逐条计数 + 抽样），**禁止静默丢**
  · 每层落账：rows_total / read / with_number / without_number / dropped_reason{} / geo_missing

用法：
  python3 collect/intake_33.py pick                       # 推荐 5 层测试集（2 点 + 2 宗地 + 1 线）
  python3 collect/intake_33.py run --layer <id> [--layer <id> ...] --out dist/intake
  python3 collect/intake_33.py selftest                   # 跑 5 层 + 对账 + 主键不交集断言
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "analysis"))
sys.path.insert(0, HERE)

REPO = "ip9988001/world-map-data-33"
REPO_ONE = "ip9988001/World-US-Map-Data"      # 一仓：TIGER 县界/addrfeat（已发布资产）

import field_map_v2 as FMV2                    # noqa: E402  归一化函数复用，避免两套口径
import county_tiger as CT                      # noqa: E402

FMAP = os.path.join(ROOT, "schema", "field-map-v2.json")
UA = {"User-Agent": "world-map-data-33/intake"}

SUFFIX = FMV2  # 别名：归一化表都在 field_map_v2 里

# fips 前两位 → 州邮政码（TIGER 权威；用于「层清单没州 / 州码非法」时反推，不是启发式猜测）
FIPS2STATE = {str(v).zfill(2): k for k, v in getattr(CT, "STATE_FIPS", {}).items()}

GATES = ["no_house_number", "no_street_name", "state_invalid", "geo_missing", "county_unresolved"]


# ------------------------------------------------------------------ 归一化
def up(v) -> str:
    return re.sub(r"\s+", " ", str(v)).strip().upper()


def norm_street(row: dict) -> dict:
    """街道后缀/方向统一成 SCHEMA 要求的口径（Street / North 全称）。"""
    for k in ("street_pre_dir", "street_post_dir"):
        if row.get(k):
            row[k] = FMV2.norm_dir(row[k]) or up(row[k])
    if row.get("street_post_type"):
        row["street_post_type"] = FMV2.norm_post_type(row["street_post_type"]) or up(row["street_post_type"])
    if row.get("street_name"):
        row["street_name"] = up(row["street_name"])
    if not row.get("street_full") and row.get("street_name"):
        parts = [row.get("street_pre_dir"), row["street_name"],
                 row.get("street_post_type"), row.get("street_post_dir")]
        row["street_full"] = " ".join(p for p in parts if p)
    return row


def addr_key(row: dict) -> str:
    """SCHEMA 的比对键：号 + 街名 + 后缀 + 前后方向 + unit + zip。"""
    parts = [row.get("house_number") or "", row.get("house_number_suffix") or "",
             row.get("street_pre_dir") or "", row.get("street_name") or "",
             row.get("street_post_type") or "", row.get("street_post_dir") or "",
             row.get("unit") or "", row.get("zip5") or ""]
    return "|".join(up(p) for p in parts)


def addr_id(row: dict) -> str:
    return hashlib.sha1(("%s|%s|%s" % (row.get("state_abbr") or "", row.get("county_fips") or "",
                                       addr_key(row))).encode()).hexdigest()


def full_formatted(row: dict) -> str:
    line1 = " ".join(p for p in [row.get("house_number"), row.get("house_number_suffix") or "",
                                 row.get("street_full") or row.get("street_name")] if p)
    tail = ", ".join(p for p in [row.get("postal_city"), row.get("state_abbr")] if p)
    z = row.get("zip5") or ""
    if z and tail:
        return "%s, %s %s" % (line1, tail, z)
    if z:
        return "%s %s" % (line1, z)
    return "%s, %s" % (line1, tail) if tail else line1


# ------------------------------------------------------------------ 取行
def release_assets(tag: str, repo: str = REPO) -> list[dict]:
    out = subprocess.run(["gh", "release", "view", tag, "--repo", repo, "--json", "assets",
                          "-q", '[.assets[]|{n:.name,u:.url,s:.size}]'],
                         capture_output=True, text=True, timeout=300).stdout or "[]"
    return json.loads(out)


def declared_rows(tag: str, repo: str = REPO) -> int | None:
    out = subprocess.run(["gh", "release", "view", tag, "--repo", repo, "--json", "assets",
                          "-q", '[.assets[]|select(.name|endswith("checkpoint.json"))|{n:.name,u:.url}]'],
                         capture_output=True, text=True, timeout=300).stdout or "[]"
    a = json.loads(out)
    if not a:
        return None
    import urllib.request
    try:
        with urllib.request.urlopen(urllib.request.Request(a[0]["u"], headers={
                **UA, "Accept": "application/octet-stream"}), timeout=120) as r:
            j = json.loads(r.read().decode())
    except Exception:      # noqa: BLE001
        return None
    ur = j.get("unit_rows") or {}
    return sum(int(v) for v in ur.values()) if ur else None


def iter_layer_rows(tag: str, limit: int = 0, repo: str = REPO, names: list | None = None):
    """逐行产出 ndjson 记录（信封格式，原始字段在 rec['raw']）。

    names 给了就用它（调用方从「一次性 release 快照」里拿），不再逐层打 API —— 全量
    2,364 层逐层 `gh release view` 会撞 5,000 次/小时的配额，快照一次只要几十次。
    """
    if names is not None:
        # 快照里给的是 [{n,u,s}]；也兼容只给名字列表的工作流
        dicts = [x if isinstance(x, dict) else {"n": x} for x in names]
        assets = sorted([a for a in dicts if str(a.get("n") or "").endswith(".tar.gz")],
                        key=lambda a: a["n"])
    else:
        assets = sorted([a for a in release_assets(tag, repo) if a["n"].endswith(".tar.gz")],
                        key=lambda a: a["n"])
    if not assets:
        return
    if limit:                      # 只要前若干行：Range 拉第一段，走部分解压
        try:
            from profile import partial_targz_rows  # analysis/profile.py
            got = 0
            for ln in partial_targz_rows(assets[0].get("b") or assets[0]["u"], 4 << 20, limit):
                if ln.strip():
                    try:
                        yield json.loads(ln)
                        got += 1
                    except Exception:  # noqa: BLE001
                        continue
            if got:
                return
        except Exception:          # noqa: BLE001
            pass                   # 部分解压不可用（鉴权/重定向/压缩头）→ 退回整包，绝不假成功
    CHUNK = 8          # 一次 gh 调用下 8 个单元：进程启动开销才是小层的大头
    with tempfile.TemporaryDirectory() as td:
        for i in range(0, len(assets), CHUNK):
            group = assets[i:i + CHUNK]
            cmd = ["gh", "release", "download", tag, "--repo", repo, "-D", td, "--clobber"]
            for a in group:
                cmd += ["-p", a["n"]]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            missing = [a["n"] for a in group if not os.path.exists(os.path.join(td, a["n"]))]
            if missing:
                raise SystemExit("资产下载失败 %s：%s" % (missing[:2], (r.stderr or "")[-160:]))
        for a in assets:
            p = os.path.join(td, a["n"])
            if not os.path.exists(p):
                continue
            with tarfile.open(p, "r:gz") as tf:
                for m in tf.getmembers():
                    if not m.name.endswith(".ndjson.gz"):
                        continue
                    fh = tf.extractfile(m)
                    if fh is None:
                        continue
                    with gzip.GzipFile(fileobj=fh) as gz:
                        for ln in gz:
                            if ln.strip():
                                try:
                                    yield json.loads(ln)
                                except Exception:  # noqa: BLE001
                                    continue
            os.unlink(p)


# ------------------------------------------------------------------ 映射
class LayerMapper:
    def __init__(self, lid: str, fmap: dict):
        e = fmap["layers"].get(lid)
        if e is None:
            raise SystemExit("field-map 里没有这层：%s（先跑 analysis/field_map_v2.py）" % lid)
        self.lid = lid
        self.e = e
        self.kind = e.get("src_kind") or "address_point"
        self._idx = None

    def county_index(self, state: str = ""):
        """判县用**全国**索引：层的 state 会错也会空，按州索引会把它整层判成未定位。
        （2026-10-30 实测：KY 911 层被标成 IN、另一层 state 为空 → 490 万行假 unlocated）"""
        if self._idx is None:
            try:
                from county_index import get_national
                self._idx = get_national()
            except Exception:      # noqa: BLE001
                self._idx = False
        return self._idx or None

    def _val(self, raw: dict, field: str):
        spec = self.e.get(field) or {}
        src = spec.get("src")
        if not src or src.startswith("[[") or src.startswith("value_rules."):
            return None
        v = raw.get(src)
        if v in (None, ""):
            return None
        tr = spec.get("transform")
        if tr == "extract_number":
            return FMV2.extract_number(v)
        if tr == "strip_number":
            return FMV2.strip_number(v)
        if tr == "strip_type_dir":
            return FMV2.strip_type_dir(v)
        if tr == "norm_zip":
            return FMV2.norm_zip(v)
        if tr == "norm_fips":
            return FMV2.norm_fips(v)
        if tr == "norm_state":
            return FMV2.norm_state(v)
        if tr == "norm_county":
            return FMV2.norm_county(v)
        if tr == "name_to_abbr":
            return FMV2.STATE_ABBR.get(up(v)) or FMV2.norm_state(v)
        return v if not isinstance(v, str) else v.strip()

    def map_row(self, rec: dict) -> tuple[dict, list[str]]:
        raw = rec.get("raw") if isinstance(rec.get("raw"), dict) else rec
        row = {}
        for f in ("house_number", "house_number_suffix", "street_pre_dir", "street_name",
                  "street_post_type", "street_post_dir", "street_full", "unit", "postal_city",
                  "municipal_city", "county_name", "county_fips", "state_abbr", "zip5"):
            row[f] = self._val(raw, f)

        # 采集信封里的归一化结果优先补（采集器已做过一次
        #  city/zip/street 归一，信封是权威）
        for k_src, k_dst in (("add_num", "house_number"), ("st_name", "street_name"),
                             ("st_suf", "street_post_type"), ("pre_dir", "street_pre_dir"),
                             ("city", "postal_city"), ("zip", "zip5"), ("unit", "unit")):
            if not row.get(k_dst) and rec.get(k_src):
                row[k_dst] = rec[k_src]
        for f in ("house_number", "house_number_suffix", "unit", "zip5"):
            if row.get(f):
                row[f] = up(row[f]) if not isinstance(row[f], (int, float)) else str(row[f])
        if row.get("zip5"):
            row["zip5"] = FMV2.norm_zip(row["zip5"])
        if row.get("state_abbr"):
            row["state_abbr"] = FMV2.norm_state(row["state_abbr"]) or row["state_abbr"]
        if not row.get("state_abbr"):
            row["state_abbr"] = (self.e.get("state_abbr") or {}).get("value")
        row = norm_street(row)

        lat, lon = rec.get("lat"), rec.get("lon")
        row["latitude"] = float(lat) if isinstance(lat, (int, float)) else None
        row["longitude"] = float(lon) if isinstance(lon, (int, float)) else None

        # 县：层名单县直接用；否则逐行 TIGER 多边形判定（禁用 bbox）
        if self.e.get("county_scope") == "single":
            row["county_name"] = row.get("county_name") or (self.e.get("county_name") or {}).get("value")
            row["county_fips"] = row.get("county_fips") or (self.e.get("county_fips") or {}).get("value")
        elif row.get("latitude") is not None and row.get("longitude") is not None:
            idx = self.county_index(row.get("state_abbr") or "")
            if idx:
                fips = idx.locate(row["latitude"], row["longitude"])
                if fips:
                    row["county_fips"] = fips
                    row["county_name"] = idx.by_fips[fips]["name"]

        # 州码兜底：层清单没州 / 州码非法时，用县 fips 前两位反推（权威，不猜）
        if (not row.get("state_abbr")) or row["state_abbr"] not in FMV2.ABBR:
            fips = row.get("county_fips")
            if fips:
                st2 = FIPS2STATE.get(str(fips)[:2])
                if st2:
                    row["state_abbr"] = st2

        # 溯源 4 列
        row["src_kind"] = self.kind
        row["src_layer_id"] = self.lid
        row["src_layer_url"] = self.e.get("src_layer_url")
        pid = None if self.kind != "parcel_situs" else (self.e.get("src_parcel_id") or {}).get("src")
        row["src_parcel_id"] = up(raw.get(pid)) if (pid and raw.get(pid) not in (None, "")) else None

        # addr_type（v1 一律 Unknown，除非 field-map 判为逐值可映射的层）
        spec = self.e.get("addr_type") or {}
        row["addr_type"] = "Unknown"
        row["nad_addr_type_raw"] = None
        if spec.get("src") and spec.get("map"):
            rv = raw.get(spec["src"])
            if rv not in (None, ""):
                row["nad_addr_type_raw"] = str(rv).strip()
                row["addr_type"] = (spec["map"].get(row["nad_addr_type_raw"])
                                    or spec.get("default") or "Unknown")

        # city 源列（SCHEMA 原生溯源）：有值才写，没值写 null；值再被清空时下面 public_row 会同步置 null
        row["postal_city_source"] = (self.e.get("postal_city_source")
                                      if row.get("postal_city") else None)
        row["municipal_city_source"] = (self.e.get("municipal_city_source")
                                        if row.get("municipal_city") else None)

        # 硬门禁
        bad = []
        if not row.get("house_number") or row["house_number"] in ("0", "000"):
            bad.append("no_house_number")
        if not row.get("street_name") or not re.search(r"[A-Za-z]", str(row["street_name"])):
            bad.append("no_street_name")
        if not row.get("state_abbr") or row["state_abbr"] not in FMV2.ABBR:
            bad.append("state_invalid")
        if row.get("latitude") is None or row.get("longitude") is None:
            bad.append("geo_missing")
        elif not row.get("county_fips"):
            bad.append("county_unresolved")
        return row, bad


# ------------------------------------------------------------------ 分流
def route(row: dict, bad: list[str], kind: str) -> tuple[str, str | None]:
    """返回 (表名, 拒绝原因)。宗地/线层永远不进 addr。"""
    if kind == "parcel_situs":
        return "aux_parcel", None
    if kind == "street_line":
        return "aux_street", None
    if bad:
        # 点层里「有街名没门牌号」是合法的一类：进 aux_addr_nohouse，不当丢弃
        if bad == ["no_house_number"] and row.get("street_name"):
            return "aux_addr_nohouse", None
        return "reject", bad[0] if len(bad) == 1 else "+".join(bad)
    return "addr", None


# 几何旁挂字段：`rings`（采集侧 2026-10-30 起面层会落简化 rings）与 `rings_skipped` 标记
# **一律不进任何表**（不进 addr / aux_parcel / aux_street / aux_addr_nohouse / reject，
# 不进五元组、不参与去重、不参与 addr_id）。理由：
#   · 几何的归属是 (src_layer_id, src_oid)，不是地址行；塞进 addr 会让同一宗地几何按地址数复制；
#   · 二仓读取走 `rings_ref` 引用（SCHEMA.json rev3 方案 B），几何本体留三仓边车。
GEOM_SIDECAR_FIELDS = ("rings", "rings_skipped", "paths", "geometry")


def public_row(row: dict) -> dict:
    """只输出 SCHEMA 2.0 的 19 主字段 + 4 三仓溯源列 + 3 个 SCHEMA 原生溯源列。

    ★ 几何字段在这里被**显式剔除**（`GEOM_SIDECAR_FIELDS`），不靠「keep 白名单碰巧没列到」——
    白名单一旦有人加字段就会漏，所以剔完还要断言（`assert_no_geom_fields`）。
    """
    keep = ["house_number", "house_number_suffix", "street_pre_dir", "street_name",
            "street_post_type", "street_post_dir", "street_full", "unit", "postal_city",
            "municipal_city", "county_name", "county_fips", "state_abbr", "zip5",
            "latitude", "longitude", "full_formatted_address",
            "src_kind", "src_layer_id", "src_layer_url", "src_parcel_id",
            "postal_city_source", "municipal_city_source", "nad_addr_type_raw"]
    out = {k: row.get(k) for k in keep}
    # addr_type：v1 一律 Unknown；只有 field-map 判为「明确分类列可映射」的层才落映射值
    out["addr_type"] = row.get("addr_type") or "Unknown"
    out["source_confidence"] = "B-Tier"     # 单层单源 → B-Tier（SCHEMA grade_rules）
    # 城市源与值必须同步：值为空则 source 必为 None（宁可空不可错）
    for v, s in (("postal_city", "postal_city_source"),
                 ("municipal_city", "municipal_city_source")):
        if not out.get(v):
            out[s] = None
    for k in GEOM_SIDECAR_FIELDS:
        out.pop(k, None)
    return out


def assert_no_geom_fields(row: dict, where: str = "") -> None:
    """硬断言：任何要落表的行里出现几何字段 → 当场炸（不许静默落进 addr/aux）。"""
    bad = [k for k in GEOM_SIDECAR_FIELDS if k in row]
    if bad:
        raise AssertionError("几何字段混进表 %s：%s（几何只能做旁挂，见 GEOM_SIDECAR_FIELDS）"
                             % (where or "?", bad))


def run_layer(lid: str, fmap: dict, outdir: str, limit: int = 0,
              compress: bool = False, declared_hint: int | None = None,
              extra_keys=None, tag_hint: str | None = None,
              assets_hint: list | None = None, write_reject: bool = True) -> dict:
    """逐层跑：读资产 → 逐行过门禁 → 分流四表。

    compress     True 时落 `<table>.<layer>.ndjson.gz`（全量盘点用，省 5~7 倍磁盘）
    declared_hint 计划期声明行数（layer_plan.csv），给了就不再为每层下载 checkpoint
    extra_keys   row → dict，附加**辅助列**（台账聚合用，如 `_street_norm`）
    """
    m = LayerMapper(lid, fmap)
    tag = tag_hint
    if tag is None:
        for cand in ("collect-step10-", "collect-step04-", "collect-step05-", "collect-step07-",
                     "collect-step03-"):
            t = cand + lid
            if release_assets(t):
                tag = t
                break
    if not tag:
        raise SystemExit("找不到 Release：%s" % lid)

    declared = declared_rows(tag) if declared_hint is None else declared_hint
    led = {"layer": lid, "tag": tag, "kind": m.kind, "state": (fmap["layers"][lid] or {}).get("state_abbr"),
           "rows_total": declared, "read": 0, "unlocated": 0, "read_errors": 0,
           "with_number": 0, "without_number": 0, "dropped_reason": {},
           "geo_missing": 0, "tables": {"addr": 0, "aux_parcel": 0, "aux_street": 0,
                                        "aux_addr_nohouse": 0, "reject": 0},
           "partial_read": bool(limit)}
    os.makedirs(outdir, exist_ok=True)
    _open = gzip.open if compress else open
    _ext = ".ndjson.gz" if compress else ".ndjson"
    # write_reject=False 时 reject 行**只记数不落盘**（保留 5 条抽样进账本）：
    # 全量盘点里 reject 占一半行，落盘纯属写垃圾；计数与抽样已经足够定位原因。
    _ks = ("addr", "aux_parcel", "aux_street", "aux_addr_nohouse") + \
          (("reject",) if write_reject else ())
    fh = {k: _open(os.path.join(outdir, "%s.%s%s" % (led_tag(k), lid, _ext)), "wt",
                   encoding="utf-8") for k in _ks}
    fh.setdefault("reject", None)
    led["reject_samples"] = []
    try:
        for rec in iter_layer_rows(tag, limit, names=assets_hint):
            row, bad = m.map_row(rec)
            led["read"] += 1
            if row.get("house_number"):
                led["with_number"] += 1
            else:
                led["without_number"] += 1
            if "geo_missing" in bad:
                led["geo_missing"] += 1
            if row.get("latitude") is not None and not row.get("county_fips"):
                led["unlocated"] += 1        # 有坐标但判不出县（含州界缺失）
            table, reason = route(row, bad, m.kind)
            if reason:
                led["dropped_reason"][reason] = led["dropped_reason"].get(reason, 0) + 1
            led["tables"][table] += 1
            pr = public_row(row)
            if extra_keys is not None:
                pr.update(extra_keys(row) or {})
            assert_no_geom_fields(pr, table)      # 几何字段进了表 → 当场炸，不静默
            if table == "addr":
                pr["addr_id"] = addr_id(row)
                pr["full_formatted_address"] = full_formatted(row)
            elif table == "aux_parcel":
                pr["aux_key"] = "p:" + hashlib.sha1(
                    ("%s|%s" % (lid, row.get("src_parcel_id") or pr.get("latitude"))).encode()).hexdigest()
            elif table == "aux_street":
                pr["aux_key"] = "s:" + hashlib.sha1(
                    ("%s|%s|%s" % (lid, pr.get("street_full"), pr.get("latitude"))).encode()).hexdigest()
            else:
                pr["aux_key"] = "n:" + hashlib.sha1(
                    ("%s|%s|%s" % (lid, pr.get("street_full"), pr.get("zip5"))).encode()).hexdigest()
            if table == "reject":
                pr["reject_reason"] = reason
            if fh.get(table) is None:            # reject 不落盘时留抽样
                if len(led["reject_samples"]) < 5:
                    led["reject_samples"].append(
                        {"reason": reason, "layer": lid, "raw": pr})
            else:
                fh[table].write(json.dumps(pr, ensure_ascii=False) + "\n")
    finally:
        for f in fh.values():
            if f is not None:
                f.close()

    if declared is not None and not limit:
        led["reconcile_ok"] = (led["with_number"] + led["without_number"] == declared == led["read"])
    led["route_ok"] = (led["read"] == sum(led["tables"].values()))
    led["reject_ok"] = (led["tables"]["reject"] == sum(led["dropped_reason"].values()))
    return led


def led_tag(k: str) -> str:
    return k


# ------------------------------------------------------------------ 线层（TIGER addrfeat）
def _find_one_release_with(asset_name: str) -> str | None:
    """在一仓所有 Release 里找含该资产的 tag（资产名带州码，先按州收窄再翻页）。"""
    m = re.search(r"-US-([A-Z]{2})-", asset_name)
    st = m.group(1) if m else ""
    # 快路径：一仓 Release 按州命名 raw-US-<ST>-v1[-pN]
    for tag in (["raw-US-%s-v1" % st, "raw-US-%s-v1-p1" % st, "raw-US-%s-v1-p2" % st] if st else []):
        out = subprocess.run(["gh", "api", f"repos/{REPO_ONE}/releases/tags/{tag}",
                              "--jq", "[.assets[].name]"], capture_output=True, text=True).stdout
        if any(str(n).startswith(asset_name) for n in json.loads(out or "[]")):
            return tag
    for page in range(1, 12):
        out = subprocess.run(["gh", "api", f"repos/{REPO_ONE}/releases?per_page=100&page={page}",
                              "--jq", "[.[].tag_name]"], capture_output=True, text=True).stdout
        tags = json.loads(out or "[]")
        if not tags:
            break
        cand = [t for t in tags if not st or ("-%s-" % st) in t or t.endswith("-" + st) or
                re.search(r"US-%s" % st, t)]
        for t in (cand or tags):
            if any(a["n"].startswith(asset_name) for a in release_assets(t, REPO_ONE)):
                return t
    return None


def run_line(asset: str, outdir: str, state: str, limit: int = 0) -> dict:
    """线层（street_line）只进 aux_street：无门牌号 → 永远不可能成为地址行。"""
    tag = _find_one_release_with(asset)
    if not tag:
        raise SystemExit("一仓找不到资产 %s" % asset)
    led = {"layer": asset, "tag": tag, "kind": "street_line", "rows_total": None, "read": 0,
           "with_number": 0, "without_number": 0, "dropped_reason": {}, "geo_missing": 0,
           "tables": {"addr": 0, "aux_parcel": 0, "aux_street": 0, "aux_addr_no_house": 0,
                      "aux_addr_nohouse": 0, "reject": 0}, "partial_read": bool(limit)}
    idx = CT.fetch_state(state)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, asset + ".zip")
    r = subprocess.run(["gh", "release", "download", tag, "--repo", REPO_ONE, "-p", asset + ".zip",
                        "-D", outdir, "--clobber"], capture_output=True, text=True, timeout=1800)
    if r.returncode != 0:
        raise SystemExit("线层资产下载失败：%s %s" % (asset, (r.stderr or "")[-200:]))
    try:
        import shapefile as pyshp          # pyshp
    except Exception:      # noqa: BLE001
        raise SystemExit("线层需要 pyshp：pip install pyshp（未装则拒跑，不静默跳层）")
    import zipfile
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(path) as z:
            z.extractall(td)
        shp = [os.path.join(td, f) for f in os.listdir(td) if f.endswith(".shp")][0]
        rd = pyshp.Reader(shp, encoding="utf-8", encodingErrors="replace")
        fields = [f[0] for f in rd.fields[1:]]
        fname = next((f for f in fields if f.upper() in ("FULLNAME", "NAME", "STREET")), None)
        fout = open(os.path.join(outdir, "aux_street.%s.ndjson" % asset), "w", encoding="utf-8")
        try:
            for sr in rd.iterShapeRecords():
                sh, rec_obj = sr.shape, sr.record
                if limit and led["read"] >= limit:
                    break
                pts = getattr(sh, "points", None) or []
                if not pts:
                    continue
                lon, lat = pts[0][0], pts[0][1]
                rec = rec_obj.as_dict()
                full = up(rec.get(fname) or "") if fname else ""
                row = {"street_full": full, "street_name": FMV2.strip_type_dir(full) or full,
                       "house_number": None, "state_abbr": FMV2.norm_state(state),
                       "latitude": lat, "longitude": lon}
                fips = idx.locate(lat, lon)
                row["county_fips"] = fips
                row["county_name"] = idx.by_fips[fips]["name"] if fips else None
                row.update({"src_kind": "street_line", "src_layer_id": asset,
                            "src_layer_url": asset, "src_parcel_id": None})
                pr = public_row(row)
                pr["aux_key"] = "s:" + hashlib.sha1(("%s|%s|%s" % (asset, full, lat)).encode()).hexdigest()
                led["read"] += 1
                led["without_number"] += 1
                led["tables"]["aux_street"] += 1
                fout.write(json.dumps(pr, ensure_ascii=False) + "\n")
        finally:
            fout.close()
    led["rows_total"] = led["read"] if not limit else None
    led["route_ok"] = led["read"] == sum(led["tables"].values())
    led["reconcile_ok"] = True
    led["reject_ok"] = True
    return led


# ------------------------------------------------------------------ 5 层测试集
def pick_layers(fmap: dict) -> list[tuple[str, str]]:
    """固定 5 层测试集（可复现）：2 点层 + 2 宗地层 + 1 线层。

    选取标准：有已发布 Release（只读）、行数适中（能全量读完做严格对账）、州已定位。
    点层选 TX（州内多县 → 强制走逐行 TIGER 多边形判县，正好压测 B 项）；
    宗地选 TX 多县 + WA 单县（两条 county 路径都覆盖）。
    线层用一仓 TIGER addrfeat（三仓 1,946 个 Polyline 层目前**一个都没采**，无三仓线层资产）。
    """
    FIXED = [
        ("8lct5k3LSbyO_arcgis_rest_services_AddressULM_FeatureServer_1", "point"),      # TX 28,996
        ("Gr3P_arcgis_rest_services_ETJ_addresses_WFL1_FeatureServer_1", "point"),      # TX 25,081
        ("7ABWQBGTG_arcgis_rest_services_Hutto_Parcels_FeatureServer_0", "parcel"),     # TX 24,655 多县
        ("cgis_rest_services_AGOL_Parcels_PacificTime_FeatureServer_17", "parcel"),     # WA 211,139 单县
        ("TIGER-US-GA-13151-addrfeat", "line"),                                          # GA Clayton 线
    ]
    out = [(l, k) for l, k in FIXED if k == "line" or fmap["layers"].get(l)]
    missing = [l for l, _ in FIXED if l not in [x for x, _ in out]]
    if missing:
        print("⚠️ 测试集缺层（field-map 里没有）：%s" % missing, file=sys.stderr)
    return out


# ------------------------------------------------------------------ CLI
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "selftest", "pick"])
    ap.add_argument("--layer", action="append", default=[])
    ap.add_argument("--out", default=os.path.join(ROOT, "dist", "intake"))
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()

    fmap = json.load(open(FMAP, encoding="utf-8"))
    if a.cmd == "pick":
        for lid, k in pick_layers(fmap):
            print("%-8s %s" % (k, lid))
        return 0

    picked = pick_layers(fmap)
    layers = [(l, "") for l in a.layer] or picked
    if a.cmd == "selftest":
        layers = picked
    leds = []
    for lid, _k in layers:
        if lid.startswith("TIGER-US-"):
            st = re.search(r"TIGER-US-([A-Z]{2})-", lid).group(1)
            led = run_line(lid, a.out, st, a.limit)
            leds.append(led)
            print(json.dumps({k: led[k] for k in ("layer", "kind", "rows_total", "read",
                                                  "with_number", "without_number", "tables")},
                             ensure_ascii=False))
            continue
        led = run_layer(lid, fmap, a.out, a.limit)
        leds.append(led)
        print(json.dumps({k: led[k] for k in ("layer", "kind", "rows_total", "read",
                                              "with_number", "without_number", "tables",
                                              "reconcile_ok", "route_ok", "reject_ok")},
                         ensure_ascii=False))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "ledger.json"), "w", encoding="utf-8") as f:
        json.dump({"schema": "intake33-ledger/v1", "layers": leds}, f, ensure_ascii=False, indent=1)

    if a.cmd == "selftest":
        return check_all(leds, a.out)
    return 0


def _ids(path: str, key: str) -> set:
    ids = set()
    if not os.path.exists(path):
        return ids
    with open(path, encoding="utf-8") as f:
        for ln in f:
            try:
                ids.add(json.loads(ln)[key])
            except Exception:      # noqa: BLE001
                continue
    return ids


def check_all(leds: list[dict], outdir: str) -> int:
    bad = []
    for led in leds:
        print("\n[%s] %s" % (led["kind"], led["layer"]))
        if led.get("rows_total") is not None and not led.get("partial_read"):
            okr = led["with_number"] + led["without_number"] == led["rows_total"] == led["read"]
            print("  对账 rows_total=%s = with(%d) + without(%d)  → %s"
                  % (led["rows_total"], led["with_number"], led["without_number"],
                     "✅" if okr else "❌"))
            bad += [] if okr else ["对账不成恒：%s" % led["layer"]]
        print("  分流 %s  丢弃原因 %s" % (led["tables"], led["dropped_reason"] or "{}"))
        if not led.get("route_ok"):
            bad.append("分行计数不守恒：%s" % led["layer"])
        if not led.get("reject_ok"):
            bad.append("拒绝原因计数不守恒：%s" % led["layer"])

    addr_ids = set()
    for led in leds:
        addr_ids |= _ids(os.path.join(outdir, "addr.%s.ndjson" % led["layer"]), "addr_id")
    aux_ids = set()
    for led in leds:
        for t in ("aux_parcel", "aux_street", "aux_addr_nohouse"):
            aux_ids |= _ids(os.path.join(outdir, "%s.%s.ndjson" % (t, led["layer"])), "aux_key")

    print("\n主键集合：addr %d 个 / aux_* %d 个 / 交集 %d 个"
          % (len(addr_ids), len(aux_ids), len(addr_ids & aux_ids)))
    if addr_ids & aux_ids:
        bad.append("addr 与 aux 主键有交集")
    if any(led["tables"]["addr"] and led["kind"] != "address_point" for led in leds):
        bad.append("非点层产出了 addr 行")

    # addr 行零缺失
    empty = 0
    for led in leds:
        p = os.path.join(outdir, "addr.%s.ndjson" % led["layer"])
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as f:
            for ln in f:
                r = json.loads(ln)
                if not r.get("house_number") or not r.get("street_name"):
                    empty += 1
    print("addr 行缺 house_number/street_name：%d 条" % empty)
    if empty:
        bad.append("addr 行有空壳")

    print("\n%s" % ("❌ " + "; ".join(bad) if bad else "✅ 5 层 selftest 全绿"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
