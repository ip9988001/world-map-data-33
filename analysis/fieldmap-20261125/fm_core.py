#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第 9 步 · 字段映射核心（被 map_layers.py 与体检共用）。

输入：`dist/intake-full/layers/<layer>/part-u*.ndjson.gz`（采集侧信封行，只读）
输出：11 列 ndjson（house_number/street_name/city/state/zip5/lat/lon/source_layer/tier/grade/addrkey）

口径（全部落在这里，不散落在 runner 里）：
- house_number：占位值（0/000/-1/-9/NULL/N/A/NONE/UNKNOWN/空/纯符号）= 缺失；**绝不生成门牌**
  （plan §二：`-9` 必须算缺失 —— muse-000258 增量第 6 条）
- house_number 浮点整形（muse-000275）：`1009.0` / `"1009.00"` / float `1009.0` → `1009`（**只改写法不改数值**）；
  非零小数（`1009.5`）**原样保留**（不四舍五入）；`0.0` 仍走占位值分支判缺失（占位语义优先，见 clean_number 注释）
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
RX_FLOAT_INT = re.compile(r"^(\d+)\.0+$")   # 1009.0 / "1009.00"：整数值的浮点写法（muse-000275）
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
    """门牌清洗：占位值/纯符号 → 空；整数值的浮点写法归一成整数字面（muse-000275）。

    归一规则（**只改字符串写法，不改数值、不改判定口径**）：
      `"1009.0"` → `"1009"`；`1009.0`(float) → `"1009"`；`" 1009.0 "` → `"1009"`；`"1009.00"` → `"1009"`
      非零小数 `"1009.5"` → **原样返回**（不四舍五入；调用方如需统计自行判定）
      `"0.0"` / `0.0`(float) → **空串**：`0` / `0.0` / `000` 是既定占位值（PLACEHOLDERS），
        占位语义优先于浮点整形 —— 若归一成 `"0"` 就会写出 `house_number="0"` 并凭空把 grade 从 C 抬到 B，
        违反「不改数值、不改分级」；故 2.3「不碰 placeholder 语义」优先于 2.1 里 `"0.0"→"0"` 的示例。
    """
    s = "" if v is None else str(v).strip()
    if s.upper() in PLACEHOLDERS or RX_ONLY_SYMBOLS.match(s):
        return ""
    m = RX_FLOAT_INT.match(s)
    if m:
        n = m.group(1)
        # 归一后再判一次占位值："0.00" → "0" 仍是占位值（0/000），绝不许变成真门牌
        return "" if (n.upper() in PLACEHOLDERS or RX_ONLY_SYMBOLS.match(n)) else n
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
    la, lo = round(la, 7), round(lo, 7)
    if la == 0.0 and lo == 0.0:      # 先 round 再判 (0,0)：|v|<5e-7 的坐标会被 round 成 0.0，
        return None, None, "null_island"   # 旧写法先判后 round，会在输出里漏出 107 行 (0,0)（muse-000266 修）
    return la, lo, ""


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


LAYER_ALIASES_PATH = os.path.join(ROOT, "registry", "layer-aliases.v1.yaml")
_LAYER_ALIAS_CACHE = {}


def load_layer_aliases(path=None):
    """层级别名（registry/layer-aliases.v1.yaml）→ {("id"|"url", key): entry}。

    只对「字段名过泛」（NAME/TYPE/STR/PARCEL_LOC/Street_derived…）的少数层生效，**不进全局角色表**。
    文件不存在时返回空表（不影响既有行为）。
    """
    p = path or LAYER_ALIASES_PATH
    if p in _LAYER_ALIAS_CACHE:
        return _LAYER_ALIAS_CACHE[p]
    import yaml
    idx = {}
    if os.path.isfile(p):
        doc = yaml.safe_load(open(p, encoding="utf-8")) or {}
        for e in doc.get("layers") or []:
            if e.get("layer_id"):
                idx[("id", e["layer_id"])] = e
            if e.get("url"):
                idx[("url", e["url"])] = e
    _LAYER_ALIAS_CACHE[p] = idx
    return idx


def load_roles():
    """raw 字段别名表（registry ∪ engine/dialects 合并；不新增、不猜）。

    muse-000271 起分“强 / 弱”两档：
      · 强（street/number/zip）= 既有方言 + 既有别名扩展条目，取值优先级同旧版（在 split 之前）；
      · 弱（street_weak/number_weak）= registry 里 `alias_strength: weak` 的新增别名，
        **只在 split 也没给出 street/number 时才兑底**——否则新别名会把原本靠拆串拿到
        门牌+完整街名的行（grade A/B）压成只有街名的 C，等于反向退化。
    """
    import yaml
    reg = os.path.join(ROOT, "registry", "dialects.v1.yaml")
    roles = SA.roles_of(reg, os.path.join(ROOT, "engine", "dialects"))
    num = {k for k, v in roles.items() if "number" in v}
    st = {k for k, v in roles.items() if "street" in v}
    zp = {k for k, v in roles.items() if "zip" in v}
    weak = set()
    doc = yaml.safe_load(open(reg, encoding="utf-8")) or {}
    for d in doc.get("dialects") or []:
        if d.get("alias_strength") != "weak":
            continue
        tpl = d.get("template") or {}
        weak |= {SA._norm(a) for a in (tpl.get("street_aliases") or [])}
        weak |= {SA._norm(a) for a in (tpl.get("number_aliases") or [])}
    return {"number": num - weak, "street": st - weak, "zip": zp,
            "number_weak": num & weak, "street_weak": st & weak}


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
        self._laliases = load_layer_aliases()
        self.begin_layer("")

    def begin_layer(self, url="", layer_id=""):
        """每层开始：重置字段名缓存（**必须每层调**）+ 记住本层 url（喂 source_layer / tier）。

        layer_id 只用于匹配层级别名（registry/layer-aliases.v1.yaml）；不传时退回 url 匹配。
        """
        self._url = url or ""
        self._keys = None            # {"number": [...], "street": [...], "zip": [...], "state": [...]}
        self._split_key = ""
        self._split_tried = False    # 已弃用（muse-000271 取消首行短路）；保留字段只为旧调用兼容
        self._lalias = (self._laliases.get(("id", layer_id or ""))
                        or self._laliases.get(("url", url or "")) or {})
        self._lsplit = list(self._lalias.get("split_fields") or [])
        self._ldrop = {str(x).strip().lower() for x in (self._lalias.get("drop_values") or [])}

    def tier_for(self, url):
        return self.tiers.get(url or "", "unrated")

    def _probe_keys(self, raw):
        """第一行时确定本层 raw 的字段名映射（role → [key...]），之后整层复用。"""
        k = {"number": [], "street": [], "zip": [], "state": [],
             "number_weak": [], "street_weak": [],
             # 层级别名：只对本层生效，顺序按 registry 里声明（不参与长度排序）
             "number_l": list(self._lalias.get("number_fields") or []),
             "street_l": list(self._lalias.get("street_fields") or [])}
        for name in raw.keys():
            nk = SA._norm(name)
            if nk in self.roles["number"]:
                k["number"].append(name)
            if nk in self.roles["street"]:
                k["street"].append(name)
            if nk in self.roles.get("number_weak", ()):
                k["number_weak"].append(name)
            if nk in self.roles.get("street_weak", ()):
                k["street_weak"].append(name)
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
        if not street and raw:
            # 组合串（一整串含门牌+街名）：按 engine/split_addr.py 拆；拆不出不猜。
            # muse-000271：① 取消「首行拆不出→整层永久不试」的短路（逐行都试）；
            #             ② 候选键从「前 40 键」扩到全部字段（层级别名 split_fields 排最前）。
            best = None
            if self._split_key:
                cand_keys = [self._split_key]     # 已找到可在全层复用的组合列：先试它、成则跳出
            else:
                head = [k for k in self._lsplit if k in raw]
                seen = set(head)
                cand_keys = head + [k for k in raw.keys() if k not in seen]
            for k in cand_keys:
                v = raw.get(k)
                if not isinstance(v, str) or len(v) < 4 or len(v) > 160:
                    continue
                if self._ldrop and v.strip().lower() in self._ldrop:
                    continue
                r = SA.split_number_street(v)
                if r["reason"] == "ok" and r["street_name"] and r["confidence"] > 0:
                    if best is None or r["confidence"] > best[1]["confidence"]:
                        best = (k, r)
                        if self._split_key:
                            break
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
        if raw:
            # 弱源（muse-000271）：registry 里 alias_strength=weak 的新增别名 + 层级别名。
            # 只在「强别名与拆串都没给出」时兜底 —— 否则新别名会把原本靠拆串拿到门牌+完整街名
            # 的行（grade A/B）压成只有街名的 C，属反向退化（muse-000271 回归专项查出过 4 层）。
            keys = self._keys if self._keys is not None else self._probe_keys(raw)
            if not num and keys.get("number_weak"):
                for k in keys["number_weak"]:
                    cand = clean_number(raw.get(k))
                    if cand:
                        num, used = cand, used | {k}
                        break
            if not street and keys.get("street_weak"):
                got = []
                for k in keys["street_weak"]:
                    if k in used:
                        continue
                    v = raw.get(k)
                    sv = "" if v is None else str(v).strip()
                    if sv and not SA.is_placeholder(sv):
                        got.append((k, sv))
                if got:
                    got.sort(key=lambda x: -len(x[1]))
                    street, used = " ".join(v for _, v in got[:4]), used | {k for k, _ in got}
            if not num and keys.get("number_l"):
                for k in keys["number_l"]:
                    cand = clean_number(raw.get(k))
                    if cand:
                        num, used = cand, used | {k}
                        break
            if not street and keys.get("street_l"):
                vals = []
                for k in keys["street_l"]:
                    v = raw.get(k)
                    sv = "" if v is None else str(v).strip()
                    if sv and not SA.is_placeholder(sv) and sv.lower() not in self._ldrop:
                        vals.append(sv)
                if vals:
                    street = " ".join(vals)
                    used = used | set(keys["street_l"])
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
