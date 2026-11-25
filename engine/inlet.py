"""入口层：3 类适配器 + 方言解析（registry 优先，engine 扩展表次之，否则 unsupported）。

适配器
  1. 服务型：`arcgis`（Query/MapServer 分页，json/geojson；outSR=4326）
  2. 落盘型：`ndjson`（.ndjson / .ndjson.gz）、`zip_csv`（OpenAddresses 打 zip 的 CSV）、
             `samples_csv`（第 6 步前置落盘的坐标样本，逐层采样的地址字段）
  3. 其它源：`zip_shp`（TIGER addrfeat 街段+门牌区间，只做街道确认，不出点）、
            `parquet`（Overture，几何在 WKB 列里）

方言解析顺序：registry/dialects.v1.yaml（冻结只读）→ engine/dialects/*.yaml → unsupported。
装不进来的源/方言一律进 `unsupported` 清单（写进产物），不猜、不静默丢。
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import os
import struct
import sys
import zipfile

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(ROOT, "registry", "dialects.v1.yaml")
ENGINE_DIALECTS = os.path.join(ROOT, "engine", "dialects")
ADAPTERS = ("arcgis", "ndjson", "zip_csv", "samples_csv", "zip_shp", "parquet")


class Unsupported(Exception):
    """方言或适配器不支持 → 上层落清单，不猜。"""


def load_registry(path: str = REGISTRY) -> dict:
    doc = yaml.safe_load(open(path, encoding="utf-8"))
    out = {}
    for d in doc.get("dialects") or []:
        t = d.get("template") or {}
        out[d["id"]] = {"id": d["id"], "origin": "registry", "provider_kind": (d.get("provider") or {}).get("kind"),
                        "crs": d.get("crs"), "geom": d.get("geom"), "precision": d.get("precision") or "unknown",
                        "a_pool_eligible": d.get("a_pool_eligible"),
                        "fields": {"number": t.get("number_aliases") or [], "street": t.get("street_aliases") or [],
                                   "unit": t.get("unit_aliases") or [], "city": t.get("place_aliases") or [],
                                   "state": t.get("state_aliases") or [], "zip": t.get("zip_aliases") or []},
                        "raw": d}
    return out


def load_engine_dialects(dirpath: str = ENGINE_DIALECTS) -> dict:
    out = {}
    for p in sorted(__import__("glob").glob(os.path.join(dirpath, "*.yaml"))):
        for d in (yaml.safe_load(open(p, encoding="utf-8")) or {}).get("dialects") or []:
            d = dict(d)
            d["origin"] = "engine"
            out[d["id"]] = d
    return out


def resolve_dialect(dialect_id: str, registry: dict, engine: dict) -> dict:
    if dialect_id in registry:
        return registry[dialect_id]
    if dialect_id in engine:
        return engine[dialect_id]
    raise Unsupported(f"dialect_not_defined:{dialect_id}")


def _val(row: dict, names) -> str:
    for n in names or []:
        v = row.get(n)
        if v is not None and str(v).strip() not in ("", "None", "NULL", "null"):
            return str(v)
    return ""


def map_row(row: dict, spec: dict, source: dict) -> dict:
    """按方言字段表把原始行映射成 canonical 键（不归一，归一在 outlet_clean）。"""
    f = spec.get("fields") or {}
    out = {k: _val(row, f.get(k)) for k in
           ("number", "number_suffix", "pre_dir", "street", "post_type", "post_dir",
            "unit", "city", "state", "zip", "id", "combined", "from_hn", "to_hn")}
    if not out["number"] and out["number_suffix"]:
        out["number"] = out["number"] + out["number_suffix"]
    out["lon"], out["lat"] = _val(row, f.get("lon")), _val(row, f.get("lat"))
    if not out["state"] and spec.get("state_from"):
        v = row.get(spec["state_from"])
        if isinstance(v, list) and v:
            out["state"] = str((v[0] or {}).get("value") or "")
    gmode = spec.get("geometry")
    if gmode in ("wkb_point", "wkb_any"):
        if gmode == "wkb_any":                       # 面/线取真实顶点，绝不用质心
            lon, lat, gtype = wkb_vertex(row.get("geometry"))
        else:
            lon, lat, gtype = (*wkb_point(row.get("geometry")), wkb_geom_type(row.get("geometry")))
        out["lon"], out["lat"] = ("" if lon is None else str(lon)), ("" if lat is None else str(lat))
        if gtype:
            out["geom_type"] = gtype
    elif row.get("geom_type"):                       # 样本 CSV 自带实测几何类型
        out["geom_type"] = str(row.get("geom_type"))
    out["source_id"], out["source_family"], out["source_ref"] = source["id"], source["family"], source.get("_ref", "")
    out["source_ref_url"] = str(row.get("layer_url") or "")     # 方言层样本：按 url 找实测 Tier
    out["is_interpolated"] = spec.get("is_interpolated", False)
    return out


def wkb_point(blob):
    """WKB/GeoArrow 点解码（Point=1，支持 2D/3D/Z）；解不了返回 (None, None)，不猜。"""
    if not isinstance(blob, (bytes, bytearray)) or len(blob) < 21:
        return None, None
    order = "<" if blob[0] == 1 else ">"
    typ = struct.unpack(order + "I", blob[1:5])[0] % 1000
    if typ != 1:
        return None, None
    x, y = struct.unpack(order + "dd", blob[5:21])
    return x, y


WKB_KIND = {1: "point", 2: "polyline", 3: "polygon", 4: "multipoint", 5: "polyline", 6: "polygon", 7: "polygon"}


def _wkb_head(blob):
    """WKB 头 → (order, 基础类型号, 维度偏移)。类型号取 %1000 去掉 Z/M 标记（1002=LineStringZ）。"""
    if not isinstance(blob, (bytes, bytearray)) or len(blob) < 5:
        return None
    order = "<" if blob[0] == 1 else ">"
    typ = struct.unpack(order + "I", blob[1:5])[0]
    dim = typ // 1000
    return order, typ % 1000, (3 if dim in (1, 3) else 2)      # Z / ZM 多一个 z 分量


def wkb_geom_type(blob) -> str:
    """WKB 几何类型名（point/polygon/polyline/multipoint）；解不了返回空串。"""
    h = _wkb_head(blob)
    return WKB_KIND.get(h[1], "") if h else ""


def wkb_vertex(blob):
    """任意 WKB 几何 → (lon, lat, geom_type)：点取自身坐标，面/线取**真实顶点**（rings[0][0] / paths[0][0]）。

    只取真实顶点，不做质心、不做插值；解不了返回 (None, None, "")，不猜。
    """
    h = _wkb_head(blob)
    if not h:
        return None, None, ""
    order, typ, ndim = h
    kind = WKB_KIND.get(typ, "")
    pos, off = 5, 5
    try:
        if typ in (5, 6):                                   # MultiLineString / MultiPolygon：先跳到第 1 个成员
            off += 4
            order2 = "<" if blob[off] == 1 else ">"
            typ2 = struct.unpack(order2 + "I", blob[off + 1:off + 5])[0] % 1000
            order, off = order2, off + 5
            if typ2 != {5: 2, 6: 3}.get(typ):
                return None, None, kind
        if typ in (2, 3, 5, 6, 7):                          # 线/面/多线/多面：跳 numX（member 已是单几何）
            off += 4
            if typ in (3, 6, 7):
                off += 4                                    # 跳 rings/points 数量 → 第一个环的第一个点
        x, y = struct.unpack(order + "dd", blob[off:off + 16])
    except (struct.error, IndexError):
        return None, None, kind
    return x, y, kind


def _open_text(path: str):
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if path.endswith(".gz") \
        else open(path, "rt", encoding="utf-8", errors="replace")


def iter_ndjson(path: str, spec: dict, source: dict):
    with _open_text(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            yield map_row(row, spec, source)


def iter_zip_csv(path: str, spec: dict, source: dict, member_contains: str = ".csv"):
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if member_contains in n.lower()]
        if not names:
            raise Unsupported(f"zip_member_missing:{path}")
        for n in names:
            with z.open(n) as raw:
                for row in csv.DictReader(io.TextIOWrapper(raw, "utf-8", errors="replace")):
                    yield map_row(row, spec, source)


def iter_zip_shp(path: str, spec: dict, source: dict):
    """TIGER addrfeat：只有街段 + 门牌区间，没有门牌点 → 只供街道确认，不出坐标。"""
    import shapefile
    import tempfile
    with zipfile.ZipFile(path) as z:
        base = tempfile.mkdtemp(prefix="shp_", dir=os.environ.get("ENGINE_TMP") or None)
        for n in z.namelist():
            if n.lower().endswith((".shp", ".dbf", ".shx")):
                z.extract(n, base)
    shp = [os.path.join(base, n) for n in os.listdir(base) if n.lower().endswith(".shp")]
    if not shp:
        raise Unsupported(f"shp_missing:{path}")
    with shapefile.Reader(shp[0], encoding="latin-1") as r:
        fields = [f[0] for f in r.fields[1:]]
        for rec in r.iterRecords():
            row = dict(zip(fields, rec))
            row.pop("geometry", None)
            yield map_row(row, spec, source)


def iter_parquet(path: str, spec: dict, source: dict):
    import pyarrow.parquet as pq
    pf = pq.ParquetFile(path)
    for batch in pf.iter_batches(batch_size=20000):
        for row in batch.to_pylist():
            yield map_row(row, spec, source)


def iter_samples_csv(path: str, spec: dict, source: dict):
    """第 6 步前置的坐标样本：一行一点，地址字段在 addr_fields_json 里。"""
    with open(path, encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            try:
                af = json.loads(row.get("addr_fields_json") or "{}")
            except json.JSONDecodeError:
                af = {}
            merged = dict(af)
            merged.update({"lon": row.get("lon"), "lat": row.get("lat"), "layer_id": row.get("layer_id"),
                           "layer_url": row.get("layer_url"),
                           "state_abbr": row.get("state"), "geom_type": row.get("geom_type")})
            yield map_row(merged, spec, source)


def iter_arcgis(base_url: str, spec: dict, source: dict, page_size: int = 1000, max_pages: int = 50):
    """ArcGIS REST 分页（json/geojson）。试点不联网，此适配器供生产与单测调用。"""
    import urllib.parse
    import urllib.request
    offset = 0
    for _ in range(max_pages):
        q = {"where": "1=1", "outFields": "*", "returnGeometry": "true", "outSR": "4326",
             "resultOffset": offset, "resultRecordCount": page_size, "f": "json"}
        url = base_url.rstrip("/") + "/query?" + urllib.parse.urlencode(q)
        with urllib.request.urlopen(url, timeout=30) as r:
            doc = json.loads(r.read().decode("utf-8"))
        if isinstance(doc, dict) and doc.get("error"):
            raise Unsupported(f"arcgis_error:{doc['error'].get('code')}")
        feats = doc.get("features") or []
        for ft in feats:
            attrs = dict(ft.get("attributes") or {})
            g = ft.get("geometry") or {}
            if g.get("x") is not None and g.get("y") is not None:
                attrs["_lon"], attrs["_lat"] = g["x"], g["y"]
            spec2 = {**spec, "fields": {**(spec.get("fields") or {}), "lon": ["_lon"], "lat": ["_lat"]}}
            yield map_row(attrs, spec2, source)
        if len(feats) < page_size or not doc.get("exceededTransferLimit"):
            return
        offset += page_size


ITERATORS = {"ndjson": iter_ndjson, "zip_csv": iter_zip_csv, "zip_shp": iter_zip_shp,
             "parquet": iter_parquet, "samples_csv": iter_samples_csv, "arcgis": iter_arcgis}


def iterate(source: dict, spec: dict):
    """按 source.adapter 分发。适配器未实现 → Unsupported（进清单，不静默）。"""
    ad = source.get("adapter") or spec.get("adapter")
    if ad not in ITERATORS:
        raise Unsupported(f"adapter_not_implemented:{ad}")
    if ad not in ADAPTERS:
        raise Unsupported(f"adapter_not_declared:{ad}")
    return ITERATORS[ad](source["path"], spec, source)


def probe_sources(sources, registry, engine):
    """开跑前的支持性体检：返回 (可跑源, unsupported 清单)。"""
    ok, bad = [], []
    for s in sources:
        try:
            spec = resolve_dialect(s["dialect"], registry, engine)
            ad = s.get("adapter") or spec.get("adapter")
            if ad not in ITERATORS:
                raise Unsupported(f"adapter_not_implemented:{ad}")
            if s.get("adapter") and s["adapter"] != spec.get("adapter"):
                # 适配器与方言声明不一致：以源为准，但记一笔（不静默）
                spec = {**spec, "adapter": s["adapter"], "_adapter_override": True}
            ok.append((s, spec))
        except Unsupported as e:
            bad.append({"source_id": s.get("id"), "family": s.get("family"), "dialect": s.get("dialect"),
                        "path": s.get("path", ""), "reason": str(e)})
    return ok, bad
