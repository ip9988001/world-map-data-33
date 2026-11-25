#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 9 步 · 字段映射核心（被 map_layers.py 与体检共用）。

输入：`dist/intake-full/layers/<layer>/part-u*.ndjson.gz`（采集侧信封行，只读）
输出：11 列 ndjson（house_number/street_name/city/state/zip5/lat/lon/source_layer/tier/grade/addrkey）

口径（全部落在这里，不散落在 runner 里）：
- house_number：占位值（0/000/-1/-9/NULL/N/A/NONE/UNKNOWN/空/纯符号）= 缺失；**绝不生成门牌**
  （plan §二：`-9` 必须算缺失 —— muse-000258 增量第 6 条）
- street_name：pre_dir + st_name + st_suf + post_dir 按序拼接（原生字段，不猜）
- city：信封 city 原样（不补、不猜）
- state：合法 2 字母大写州码（含 DC/PR/VI/GU/AS/MP），否则 null
- zip5：`12345-6789` 取前 5；**恰好 5 位数字**才算有效，否则 null（不补零、不截断）
- lat/lon：范围校验；(0,0)/缺省 → null，绝不写 0 冒充
- source_layer：**url**（plan §二；不是 layer_id；无 url 的层退回 layer_id 并在覆盖表标注）
- tier：分档表 `analysis/grading-rerun-20261125/auto-recognized.csv`（Tier1 = 410 那版）按 url 取；未命中 → unrated
- grade：按 pilot.yaml grades（特征全为真才命中，S→C 依次试）；阈值为空（无硬编码阈值）
- grade 封顶：邮编非法/缺失 → 不许落需要 zip5 的级（配置里就是 S/A）→ 自动落到 B/C（plan §二 封顶 B）
- addrkey：**engine 档 v3**（`engine/outlet_clean.py:addrkey_v3`）
  parts = [state2, zip5, num_key, street_key(TYPE|CORE|DIR), unit_key]，include_unit 读 pilot.yaml
  num 或 street 缺 → 不可键 → null（engine 口径，进 unkeyed）

方言：registry/dialects.v1.yaml 按 agol org 匹配（本批 3,550 层不在 17,168 分档分母内，url/layer_id 命中 0，
org 命中 115）→ 未命中一律 dialect_id=minimal_safe（pool=manual，a_pool_eligible=false，永不进 A 货池）。
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "engine"))
import split_addr as SA  # noqa: E402  （唯一角色表装载口：registry ∪ engine/dialects）
import outlet_clean as OC  # noqa: E402  （addrkey v3 唯一实现口，不重写）

STATES_OK = {"AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA",
             "ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR",
             "PA","RI","SC","SD","TN","TX","UT","VT","VA","WA","WV","WI","WY","PR","VI","GU","AS","MP"}
STATE_KEYS = {"state", "st", "stateabbr", "state_abbr", "statecode", "state_code", "stabb", "statealpha"}
# 占位值（plan §二 清单 + muse-000258 增量第 6 条补 -9；数值化变体一并算缺失）
PLACEHOLDERS = {"", "0", "000", "NULL", "NONE", "N/A", "NA", "UNKNOWN", "-1", "-9", "-", "--", ".", "?",
                "0.0", "-1.0", "-9.0", "0000", "-09"}
RX_DIGITS5 = re.compile(r"^(\d{5})(?:-\d{4})?$")
RX_ONLY_SYMBOLS = re.compile(r"^[^0-9A-Za-z]+$")

FIELDS = ["house_number", "street_name", "city", "state", "zip5", "lat", "lon",
          "source_layer", "tier", "grade", "addrkey"]


def load_pilot_cfg(path=None):
    import yaml
    p = path or os.path.join(ROOT, "engine", "config", "pilot.yaml")
    doc = yaml.safe_load(open(p, encoding="utf-8"))
    return {"grades": doc["grades"], "tier_rank": doc["tier_rank"], "addrkey": doc["addrkey"]}


def load_registry_orgs(path=None):
    """registry → {agol_org: [dialect_id,...]}（只用来判方言归属，不改 registry）。"""
    import yaml
    p = path or os.path.join(ROOT, "registry", "dialects.v1.yaml")
    doc = yaml.safe_load(open(p, encoding="utf-8"))
    org2dial, meta = {}, {}
    for d in doc.get("dialects") or []:
        meta[d["id"]] = {"a_pool_eligible": d.get("a_pool_eligible"), "template": d.get("template") or {}}
        for pair in ((d.get("provider") or {}).get("orgs") or []):
            org2dial.setdefault(pair[0], []).append(d["id"])
    return org2dial, meta, doc.get("fallback") or {}


RX_AGOL_ORG = re.compile(r"//(?:services\d*|utility\.arcgis|www\.arcgis)\.com/(?:usrsvcs/servers/[0-9a-f]+/)?([A-Za-z0-9]+)/",
                         re.I)


def agol_org(url: str) -> str:
    m = RX_AGOL_ORG.search(url or "")
    return m.group(1) if m else ""


def clean_number(v) -> str:
    s = "" if v is None else str(v).strip()
    if s.upper() in PLACEHOLDERS or RX_ONLY_SYMBOLS.match(s):
        return ""
    return s


def clean_street(pre, name, suf, post) -> str:
    parts = [("" if x is None else str(x).strip()) for x in (pre, name, suf, post)]
    parts = [p for p in parts if p and p.upper() not in PLACEHOLDERS]
    return " ".join(parts)


def clean_city(v) -> str:
    s = "" if v is None else str(v).strip()
    return "" if s.upper() in PLACEHOLDERS else s


def clean_state(v) -> str:
    s = "" if v is None else str(v).strip().upper()
    return s if s in STATES_OK else ""


def clean_zip5(v):
    """返回 (zip5, reason)：恰好 5 位数字才算有效；12345-6789 取前 5；其它一律 null。"""
    s = "" if v is None else str(v).strip()
    if not s:
        return "", "missing"
    m = RX_DIGITS5.match(s)
    if m:
        return m.group(1), ""
    return "", "invalid"


def clean_coord(lat, lon):
    """返回 (lat, lon, reason)：范围外 / (0,0) / 缺省 → (None, None)。"""
    try:
        la = float(lat)
        lo = float(lon)
    except (TypeError, ValueError):
        return None, None, "missing"
    if not (-90.0 <= la <= 90.0) or not (-180.0 <= lo <= 180.0):
        return None, None, "out_of_range"
    if la == 0.0 and lo == 0.0:
        return None, None, "null_island"
    return round(la, 7), round(lo, 7), ""


def addrkey_v3(number, street, state, zip5, unit="", include_unit=True,
              post_type="", pre_dir="", post_dir=""):
    """千一下不自己算：全部交给 engine/outlet_clean.addrkey_v3（v3 = a3 + include_unit + sha1-20hex）。

    num 或 street 缺 → 返回 ""（engine 口径：不可键、进 unkeyed）。
    """
    return OC.addrkey_v3({"state": state, "zip": zip5, "number": number,
                          "street": street, "post_type": post_type,
                          "pre_dir": pre_dir, "post_dir": post_dir, "unit": unit},
                         include_unit=include_unit)


def features_of(rec):
    """clean() 口径的特征：number/street/city/state/zip5/point(真实点)/point_any。"""
    return {"number": bool(rec["house_number"]), "street": bool(rec["street_name"]),
            "city": bool(rec["city"]), "state": bool(rec["state"]), "zip5": bool(rec["zip5"]),
            "point": rec["lat"] is not None and rec["lon"] is not None and not rec.get("_interp"),
            "point_any": rec["lat"] is not None and rec["lon"] is not None}


def grade_of(rec, grades_cfg):
    feats = features_of(rec)
    for g, need in grades_cfg.items():                    # S→C 依次试，全为真才命中
        if all(feats.get(k) for k in need):
            return g
    return None


def load_roles():
    """raw 字段别名表（registry ∪ engine/dialects 合并；不新增、不猜）。"""
    roles = SA.roles_of(os.path.join(ROOT, "registry", "dialects.v1.yaml"),
                        os.path.join(ROOT, "engine", "dialects"))
    num = {k for k, v in roles.items() if "number" in v}
    st = {k for k, v in roles.items() if "street" in v}
    zp = {k for k, v in roles.items() if "zip" in v}
    return {"number": num, "street": st, "zip": zp}


def _raw_get(raw, names, ban=()):
    """raw 里按角色别名取值：跳过占位值、跳过 ban（已用作别的角色），取第一个非空。"""
    hits = []
    for k, v in raw.items():
        if not isinstance(v, (str, int, float)) or isinstance(v, bool):
            continue
        nk = SA._norm(k)
        if nk in names and nk not in ban:
            sv = str(v).strip()
            if sv and not SA.is_placeholder(sv):
                hits.append((nk, sv))
    return hits


def load_tier_map(path=None):
    """分档表 → {url: tier}。版本锁定：plan §一「Tier1 = 410 层那版」= grading-rerun-20261125。"""
    import csv as _csv
    p = path or os.path.join(ROOT, "analysis", "grading-rerun-20261125", "auto-recognized.csv")
    rank = {"tier1": 1, "tier2": 2, "tier3": 3}
    best = {}
    with open(p, encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            t, u = r.get("tier"), r.get("url")
            if not u or t not in rank:
                continue
            if u not in best or rank[t] < rank[best[u]]:
                best[u] = t
    return best


class LayerMapper:
    """单层：信封行 → 11 列，带逐层计数（in/mapped/dropped_*）与字段质量计数。"""

    def __init__(self, cfg, org2dial, dialect_meta, tier_map=None):
        self.cfg = cfg
        self.org2dial = org2dial
        self.meta = dialect_meta
        self.grades = cfg["grades"]
        ak = cfg.get("addrkey") or {}
        self.ak_version = ak.get("version")
        self.ak_hash = ak.get("hash")
        self.include_unit = bool(ak.get("include_unit", True))
        if self.ak_version != "v3" or self.ak_hash != "sha1-20hex":
            raise SystemExit(f"addrkey 配置与 engine 实现不一致：{ak}")
        self.tiers = tier_map if tier_map is not None else load_tier_map()
        self.roles = load_roles()
        self.begin_layer("")

    def begin_layer(self, url=""):
        """每层开始：重置字段名缓存（**必须每层调**）+ 记住本层 url（喂 source_layer / tier）。"""
        self._url = url or ""
        self._keys = None            # {"number": [...], "street": [...], "zip": [...], "state": [...]}
        self._split_key = ""
        self._split_tried = False

    def tier_for(self, url):
        return self.tiers.get(url or "", "unrated")

    def _probe_keys(self, raw):
        """第一行时确定本层 raw 的字段名映射（role → [key...]），之后整层复用。"""
        k = {"number": [], "street": [], "zip": [], "state": []}
        for name in raw.keys():
            nk = SA._norm(name)
            if nk in self.roles["number"]:
                k["number"].append(name)
            if nk in self.roles["street"]:
                k["street"].append(name)
            if nk in self.roles["zip"]:
                k["zip"].append(name)
            if nk in STATE_KEYS:
                k["state"].append(name)
        self._keys = k
        return k

    def dialect_for(self, url):
        org = agol_org(url)
        cands = self.org2dial.get(org) or []
        if cands:
            d = cands[0]
            return d, "registry", (self.meta.get(d) or {}).get("a_pool_eligible")
        return "minimal_safe", "fallback", False

    def map_row(self, row):
        """返回 (out|None, reason, fstats)：reason 只在丢弃时有值。

        取值优先级（逐字段）：信封原生值 → raw 角色别名（registry ∪ engine 表）→ 组合串拆分。
        provenance：native（信封/单字段别名原值）/ split（组合串拆出来的）——
        split 出来的值**一律不许进 S**（S 级要求全要素原生）。
        """
        prov = "native"
        num = clean_number(row.get("add_num"))
        street = clean_street(row.get("pre_dir"), row.get("st_name"), row.get("st_suf"), row.get("post_dir"))
        city = clean_city(row.get("city"))
        state = clean_state(row.get("state") or row.get("st"))
        zip5, zreason = clean_zip5(row.get("zip"))
        raw = row.get("raw") if isinstance(row.get("raw"), dict) else {}
        used = set()
        if raw:
            keys = self._keys if self._keys is not None else self._probe_keys(raw)
            if not num:
                for k in keys["number"]:
                    cand = clean_number(raw.get(k))
                    if cand:
                        num, used = cand, used | {k}
                        break
            if not street:
                got = []
                for k in keys["street"]:
                    if k in used:
                        continue
                    v = raw.get(k)
                    sv = "" if v is None else str(v).strip()
                    if sv and not SA.is_placeholder(sv):
                        got.append((k, sv))
                if got:
                    got.sort(key=lambda x: -len(x[1]))
                    street, used = " ".join(v for _, v in got[:4]), used | {k for k, _ in got}
            if not state:
                for k in keys["state"]:
                    cand = clean_state(raw.get(k) if isinstance(raw.get(k), str) else "")
                    if cand:
                        state = cand
                        break
            if not zip5:
                for k in keys["zip"]:
                    if k in used:
                        continue
                    z, _ = clean_zip5(raw.get(k))
                    if z:
                        zip5, zreason, used = z, "", used | {k}
                        break
        if not street and raw and not (self._split_tried and not self._split_key):
            # 组合串（一整串含门牌+街名）：按 engine/split_addr.py 拆；拆不出不猜
            best = None
            cand_keys = [self._split_key] if self._split_key else list(raw.keys())[:40]
            for k in cand_keys:
                v = raw.get(k)
                if not isinstance(v, str) or len(v) < 4 or len(v) > 160:
                    continue
                r = SA.split_number_street(v)
                if r["reason"] == "ok" and r["street_name"] and r["confidence"] > 0:
                    if best is None or r["confidence"] > best[1]["confidence"]:
                        best = (k, r)
                        if self._split_key:
                            break
            self._split_tried = True
            if best:
                self._split_key = best[0]
            if best:
                r = best[1]
                if not street:
                    street = r["street_name"]
                if not num and r["house_number"]:
                    num = clean_number(r["house_number"])
                prov = "split"
                if not zip5:
                    t = SA.split_city_tail(best[0] and raw.get(best[0]) or "")
                    if t.get("zip"):
                        z, _ = clean_zip5(t["zip"])
                        zip5 = z or zip5
                    if not city and t.get("city"):
                        city = clean_city(t["city"])
        lat, lon, creason = clean_coord(row.get("lat"), row.get("lon"))
        rec = {"house_number": num or None, "street_name": street or None, "city": city or None,
               "state": state or None, "zip5": zip5 or None, "lat": lat, "lon": lon,
               "source_layer": self._url or row.get("src_layer") or None, "tier": None, "grade": None,
               "addrkey": None, "_interp": bool(row.get("pos_estimated"))}
        g = grade_of({k: v for k, v in rec.items() if k != "tier"}, self.grades)
        if g == "S" and prov == "split":
            g = "A"                     # split/推断来的值一律降级，S 级只许全原生
        g = self.cap_no_zip(g, rec)      # 邮编非法/缺失 → 封顶 B（plan §二）
        rec["grade"] = g
        rec["_prov"] = prov
        rec["_zreason"] = zreason
        rec["_creason"] = creason
        if g is None:                                     # 低于 C：丢弃（记 dropped_low_grade）
            return None, "below_c", rec
        rec["addrkey"] = addrkey_v3(num, street, state, zip5, row.get("unit") or "",
                                    include_unit=self.include_unit,
                                    post_type=row.get("st_suf") or "",
                                    pre_dir=row.get("pre_dir") or "",
                                    post_dir=row.get("post_dir") or "") or None
        return rec, "", rec

    def cap_no_zip(self, g, rec):
        """邮编非法/缺失 → 不许命中「需要 zip5」的级（由配置推出，不硬编码 S/A）。"""
        req = {k for k, need in self.grades.items() if "zip5" in need}
        if g in req and not rec.get("zip5"):
            return grade_of(rec, {k: v for k, v in self.grades.items() if k not in req})
        return g
