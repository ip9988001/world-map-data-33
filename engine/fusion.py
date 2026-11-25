"""融合层：按 addrkey v3 多源同址合并 + 分档(Tier)×完整度(S/A/B/C) 分级。

设计要点（全部可由 engine/config/pilot.yaml 覆盖，代码里没有硬编码阈值）：
  · 去重键 = addrkey v3（engine/outlet_clean.py），版本前缀 a3:
  · 冲突（同一 key 的多源坐标相差 > coord_conflict_m）→ 按源优先级保留，provenance 里记全部来源与坐标
  · Tier 取「贡献源里最好的档」：tier1 < tier2 < tier3 < unrated（rank 由配置给）
  · 完整度 S/A/B/C 由 features 布尔 + 配置规则判定，规则里没列出的特征不参与
  · 低于 min_grade 的行不入库，计数 dropped_low_grade
  · 用 sqlite 落盘去重表（可复算、可断点），不是内存 dict —— 行数上百万也不会炸内存
"""
from __future__ import annotations

import json
import math
import os
import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS fused (
  addrkey TEXT PRIMARY KEY,
  number TEXT, street TEXT, post_type TEXT, pre_dir TEXT, post_dir TEXT, unit TEXT,
  city TEXT, state TEXT, zip5 TEXT, lon REAL, lat REAL,
  precision TEXT, is_interpolated INTEGER, geom_type TEXT, point_kind TEXT, pos_estimated INTEGER,
  tier TEXT, tier_rank INTEGER, tier_basis TEXT,
  grade TEXT, source_id TEXT, source_family TEXT, record_id TEXT,
  n_sources INTEGER, contributors TEXT, coord_conflict INTEGER
);
CREATE TABLE IF NOT EXISTS unkeyed (
  rowid_ INTEGER PRIMARY KEY AUTOINCREMENT,
  number TEXT, street TEXT, unit TEXT, city TEXT, state TEXT, zip5 TEXT, lon REAL, lat REAL,
  precision TEXT, is_interpolated INTEGER, geom_type TEXT, point_kind TEXT, pos_estimated INTEGER,
  tier TEXT, tier_basis TEXT, grade TEXT, source_id TEXT, source_family TEXT, record_id TEXT
);
CREATE INDEX IF NOT EXISTS idx_fused_state ON fused(state);
CREATE INDEX IF NOT EXISTS idx_unkeyed_state ON unkeyed(state);
"""


def haversine_m(a, b) -> float:
    dx = (a[0] - b[0]) * 111320.0 * math.cos(math.radians((a[1] + b[1]) / 2))
    return math.hypot(dx, (a[1] - b[1]) * 110540.0)


class Fusion:
    def __init__(self, db_path: str, cfg: dict, fresh: bool = True):
        self.cfg = cfg
        self.priority = cfg["priority"]
        self.tier_rank = cfg["tier_rank"]
        self.grades = cfg["grades"]
        self.min_grade = cfg.get("min_grade", "C")
        self.conflict_m = float(cfg.get("coord_conflict_m", 100))
        self.include_unit = bool((cfg.get("addrkey") or {}).get("include_unit", True))
        self.grade_order = {g: i for i, g in enumerate(("S", "A", "B", "C", "X"))}
        if fresh and os.path.exists(db_path):
            os.remove(db_path)
        self.db = sqlite3.connect(db_path, isolation_level=None)
        self.db.executescript("PRAGMA journal_mode=MEMORY; PRAGMA synchronous=OFF; PRAGMA cache_size=-200000;")
        self.db.executescript(DDL)
        self.cols = [d[0] for d in self.db.execute("SELECT * FROM fused LIMIT 0").description]
        self.stats = {"in_rows": 0, "kept": 0, "dup": 0, "conflict": 0, "unkeyed": 0,
                      "low_grade": 0, "out_of_state": 0, "source_rows": {},
                      "geom_type_in": {}, "point_kind_in": {}, "pos_estimated_in": 0}

    # ------------------------------------------------------------------ 分级
    def grade(self, rec: dict) -> str:
        from engine.outlet_clean import grade_of
        return grade_of(rec["features"], self.grades)

    def better(self, a: dict, b: dict) -> bool:
        """a 是否应替换库里已有的 b：真实点/顶点永远优先于插值，其次源优先级，再次完整度。

        「插值行永远不能盖掉真实点/顶点」是硬约束，放在优先级之前判（第 7 步口径 2.3）。
        """
        real_a, real_b = not a.get("is_interpolated"), not b.get("is_interpolated")
        if real_a != real_b:
            return real_a
        pa, pb = self.priority.get(a["source_family"], 999), self.priority.get(b["source_family"], 999)
        ga, gb = self.grade_order.get(a["grade"], 9), self.grade_order.get(b["grade"], 9)
        return (pa, ga) < (pb, gb)

    # ------------------------------------------------------------------ 主流程
    def add(self, rec: dict, tier: str = "unrated", tier_basis: str = "") -> None:
        self.stats["in_rows"] += 1
        fam = rec.get("source_family", "")
        self.stats["source_rows"][fam] = self.stats["source_rows"].get(fam, 0) + 1
        gtype = rec.get("geom_type") or "unknown"
        self.stats["geom_type_in"][gtype] = self.stats["geom_type_in"].get(gtype, 0) + 1
        pkind = rec.get("point_kind") or "none"
        self.stats["point_kind_in"][pkind] = self.stats["point_kind_in"].get(pkind, 0) + 1
        self.stats["pos_estimated_in"] += int(bool(rec.get("pos_estimated")))
        g = self.grade(rec)
        if self.grade_order.get(g, 9) > self.grade_order.get(self.min_grade, 3):
            self.stats["low_grade"] += 1
            return
        key = rec.get("addrkey") or ""
        rank = self.tier_rank.get(tier, self.tier_rank.get("unrated", 9))
        if not key:
            self.stats["unkeyed"] += 1
            self.db.execute(
                "INSERT INTO unkeyed (number,street,unit,city,state,zip5,lon,lat,precision,is_interpolated,"
                "geom_type,point_kind,pos_estimated,tier,tier_basis,grade,source_id,source_family,record_id) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (rec["number"], rec["street"], rec["unit"], rec["city"], rec["state"], rec["zip5"],
                 rec["lon"], rec["lat"], rec["precision"], int(rec["is_interpolated"]),
                 gtype, rec.get("point_kind") or "", int(bool(rec.get("pos_estimated"))), tier, tier_basis,
                 g, rec["source_id"], fam, rec["record_id"]))
            return
        row = self.db.execute("SELECT * FROM fused WHERE addrkey=?", (key,)).fetchone()
        prov = {"src": rec["source_id"], "fam": fam, "tier": tier, "tier_basis": tier_basis, "grade": g,
                "lon": rec["lon"], "lat": rec["lat"], "precision": rec["precision"],
                "interp": rec["is_interpolated"], "rid": rec["record_id"],
                "geom_type": gtype, "point_kind": rec.get("point_kind") or "",
                "pos_estimated": bool(rec.get("pos_estimated"))}
        if row is None:
            self.stats["kept"] += 1
            self.db.execute(
                "INSERT INTO fused (addrkey,number,street,post_type,pre_dir,post_dir,unit,city,state,zip5,lon,"
                "lat,precision,is_interpolated,geom_type,point_kind,pos_estimated,tier,tier_rank,tier_basis,"
                "grade,source_id,source_family,record_id,n_sources,contributors,coord_conflict) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (key, rec["number"], rec["street"], rec["post_type"], rec["pre_dir"], rec["post_dir"],
                 rec["unit"], rec["city"], rec["state"], rec["zip5"], rec["lon"], rec["lat"],
                 rec["precision"], int(rec["is_interpolated"]), gtype, rec.get("point_kind") or "",
                 int(bool(rec.get("pos_estimated"))), tier, rank, tier_basis, g, rec["source_id"], fam,
                 rec["record_id"], 1, json.dumps([prov], ensure_ascii=False), 0))
            return
        cur = dict(zip(self.cols, row))
        provs = json.loads(cur["contributors"])
        conflict = 0
        if cur["lon"] is not None and rec["lon"] is not None:
            if haversine_m((cur["lon"], cur["lat"]), (rec["lon"], rec["lat"])) > self.conflict_m:
                conflict = 1
        self.stats["dup"] += 1
        self.stats["conflict"] += conflict
        keeping_cur = not self.better({"source_family": fam, "grade": g,
                                       "is_interpolated": rec["is_interpolated"]}, cur)
        best_tier = cur["tier"] if self.tier_rank.get(cur["tier"], 9) <= rank else tier
        if keeping_cur:
            self.db.execute("UPDATE fused SET n_sources=n_sources+1, contributors=?, coord_conflict=?, "
                            "tier=?, tier_rank=? WHERE addrkey=?",
                            (json.dumps(provs + [prov], ensure_ascii=False),
                             max(conflict, cur["coord_conflict"]), best_tier,
                             self.tier_rank.get(best_tier, 9), key))
        else:
            self.stats["kept"] += 1
            self.stats["kept"] -= 1        # 替换不是新增，抵消
            self.db.execute(
                "UPDATE fused SET number=?,street=?,post_type=?,pre_dir=?,post_dir=?,unit=?,city=?,state=?,"
                "zip5=?,lon=?,lat=?,precision=?,is_interpolated=?,geom_type=?,point_kind=?,pos_estimated=?,"
                "tier=?,tier_rank=?,tier_basis=?,grade=?,source_id=?,source_family=?,record_id=?,"
                "n_sources=n_sources+1,"
                "contributors=?,coord_conflict=? WHERE addrkey=?",
                (rec["number"], rec["street"], rec["post_type"], rec["pre_dir"], rec["post_dir"],
                 rec["unit"], rec["city"], rec["state"], rec["zip5"], rec["lon"], rec["lat"],
                 rec["precision"], int(rec["is_interpolated"]), gtype, rec.get("point_kind") or "",
                 int(bool(rec.get("pos_estimated"))), best_tier,
                 self.tier_rank.get(best_tier, 9), tier_basis, g, rec["source_id"], fam, rec["record_id"],
                 json.dumps(provs + [prov], ensure_ascii=False), max(conflict, cur["coord_conflict"]), key))

    # ------------------------------------------------------------------ 输出
    def commit(self) -> None:
        self.db.commit()

    def summaries(self, state: str | None = None) -> dict:
        where, args = ("WHERE state=?", (state,)) if state else ("", ())
        q = lambda sql: self.db.execute(sql + where, args).fetchall()  # noqa: E731
        total = q("SELECT COUNT(*) FROM fused ")[0][0]
        by_grade = dict(q("SELECT grade, COUNT(*) FROM fused GROUP BY grade") if not state
                        else self.db.execute("SELECT grade, COUNT(*) FROM fused WHERE state=? GROUP BY grade",
                                             (state,)).fetchall())
        grid = {}
        for t, g, n in (self.db.execute(
                "SELECT tier, grade, COUNT(*) FROM fused " + where + " GROUP BY tier, grade", args).fetchall()):
            grid.setdefault(t, {})[g] = n
        for t in ("tier1", "tier2", "tier3", "unrated"):
            for g in ("S", "A", "B", "C"):
                grid.setdefault(t, {}).setdefault(g, 0)
        by_geom = {}
        for gt, n, wp in self.db.execute(
                "SELECT geom_type, COUNT(*), SUM(CASE WHEN lon IS NOT NULL THEN 1 ELSE 0 END) FROM fused "
                + (where or "WHERE 1=1") + " GROUP BY geom_type", args).fetchall():
            by_geom[gt or "unknown"] = {"rows": n, "with_point": wp or 0}
        by_kind = dict(self.db.execute(
            "SELECT point_kind, COUNT(*) FROM fused " + (where or "WHERE 1=1") + " GROUP BY point_kind",
            args).fetchall())
        s_est = self.db.execute("SELECT COUNT(*) FROM fused " + (where or "WHERE 1=1")
                                + " AND grade='S' AND pos_estimated=1", args).fetchone()[0]
        return {"deduped_rows": total, "by_grade": by_grade, "by_tier_grade": grid,
                "by_geom_type": by_geom, "geom_type_in": self.stats["geom_type_in"],
                "by_point_kind": by_kind, "point_kind_in": self.stats["point_kind_in"],
                "pos_estimated_in": self.stats["pos_estimated_in"],
                "pos_estimated_rows": self.db.execute(
                    "SELECT COUNT(*) FROM fused " + (where or "WHERE 1=1") + " AND pos_estimated=1",
                    args).fetchone()[0],
                "s_with_pos_estimated": s_est,
                "with_point": (self.db.execute(
                    "SELECT COUNT(*) FROM fused " + (where or "WHERE 1=1") + " AND lon IS NOT NULL", args)
                    .fetchone()[0] if total else 0),
                "multi_source": (self.db.execute(
                    "SELECT COUNT(*) FROM fused " + (where or "WHERE 1=1") + " AND n_sources>1", args)
                    .fetchone()[0] if total else 0),
                "coord_conflict": (self.db.execute(
                    "SELECT COUNT(*) FROM fused " + (where or "WHERE 1=1") + " AND coord_conflict=1", args)
                    .fetchone()[0] if total else 0),
                "unkeyed_rows": (self.db.execute(
                    "SELECT COUNT(*) FROM unkeyed " + where, args).fetchone()[0] if total else 0)}

    def export(self, prefix: str, state: str | None = None, shard_mb: int = 40) -> int:
        """导出为 `prefix.partNN.ndjson.gz` 分片（每片 ≤shard_mb 未压缩，避免单文件撞 GitHub 100MB 上限）。"""
        import gzip
        cols = ("addrkey,number,street,post_type,pre_dir,post_dir,unit,city,state,zip5,lon,lat,precision,"
                "is_interpolated,geom_type,point_kind,pos_estimated,tier,grade,source_id,source_family,"
                "record_id,n_sources,coord_conflict,tier_basis")
        sql = f"SELECT {cols}, contributors FROM fused" + (" WHERE state=?" if state else "")
        limit, n, part = shard_mb * 1024 * 1024, 0, 0
        fh = gzip.open(f"{prefix}.part{part:02d}.ndjson.gz", "wt", encoding="utf-8")
        size = 0
        for row in self.db.execute(sql, (state,) if state else ()):
            line = json.dumps(dict(zip(cols.split(",") + ["contributors"], row)), ensure_ascii=False) + "\n"
            if size + len(line) > limit:
                fh.close()
                part += 1
                fh = gzip.open(f"{prefix}.part{part:02d}.ndjson.gz", "wt", encoding="utf-8")
                size = 0
            fh.write(line)
            size += len(line)
            n += 1
        fh.close()
        return n
