#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W33-062 —— `--force-fresh`：让「force 补采」真的重采，而不是 checkpoint 续跑。

## 为什么要有这个开关（实测 run 45010130014）

`--force-layers` 只绕 plan 的 `skip_done`、把层提到队首；`run_step_05` 仍走 pilot 的
checkpoint 续跑 → 点名重采的 3 层 elapsed 1.9~3.0s、日志写着「本次续跑：跳过 N 个已完成
单元，新采 0 行」、行数直接取上轮包。后果是**连锁**的：PR #39 的 supersede 逻辑在
`ckpt_guard.merge_checkpoints()` 里，**不重采就永远不触发** —— 所以 2× 的 100 层再跑一百轮
也不会归位。

## 本文件锁的四件事（都是行为，不是代码形状）

  A. `force + resume`（默认，不传 fresh）：`elapsed` 极短、**新采 0 行**、旧包不 supersede
     —— 现状语义一个字不许变（否则会把全量重采一遍）。
  B. `force + fresh`：新采行数 > 0、单元包带新代际前缀、旧代际 `superseded_by`、
     `rows_total` = 新代单算（1200，不是 2400）、行数等式成立。
  C. 名单**外**的层：fresh 与否都一次不动（`run_layer` 调用次数 0），且新代际前缀/环境变量
     不许泄漏到它们身上。
  D. 反例：`force + fresh` 但上游 0 行 → 层记录必须写 `fresh_but_upstream_empty`，
     不许静默当成「重采成功」。

用法: python3 -m unittest discover -s collect/tests -p "test_*.py"
"""
import gzip
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ckpt_guard as CG      # noqa: E402
import full_shard as FS      # noqa: E402
import ledger_merge as LM    # noqa: E402
import pilot                 # noqa: E402


# ---------------------------------------------------------------- 假上游（忠实 ArcGIS 语义）
def _bounds_any(where):
    lo, hi = 1, None
    m = re.search(r"(\w+)\s*>=\s*(-?\d+)", where or "")
    if m:
        lo = int(m.group(2))
    m = re.search(r"(\w+)\s*<=\s*(-?\d+)", where or "")
    if m:
        hi = int(m.group(2))
    return lo, hi


def _bounds(oid, where):
    lo, hi = 1, None
    m = re.search(r"%s>=(-?\d+)" % re.escape(oid), where or "")
    if m:
        lo = int(m.group(1))
    m = re.search(r"%s<=(-?\d+)" % re.escape(oid), where or "")
    if m:
        hi = int(m.group(1))
    m = re.search(r"%s>(?!=)(-?\d+)" % re.escape(oid), where or "")
    return lo, hi, (int(m.group(1)) if m else None)


class Svc:
    """count / keyset 分页 / outStatistics / 元数据，一行不少也不多。"""

    def __init__(self, n=1200, page=200, oid="OBJECTID"):
        self.n, self.page, self.oid = n, page, oid
        self.queries = []

    def meta(self):
        return {"objectIdField": self.oid, "maxRecordCount": self.page,
                "fields": [{"name": self.oid, "type": "esriFieldTypeOID"},
                           {"name": "Addr", "type": "esriFieldTypeString"}],
                "geometryType": "esriGeometryPoint", "definitionExpression": None}

    def feat(self, i):
        return {"attributes": {self.oid: i, "Addr": "a%d" % i},
                "geometry": {"x": 1.0, "y": 2.0}}

    def __call__(self, url, timeout=180, tries=3):
        q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(url).query))
        self.queries.append(q)
        if "f" in q and len(q) == 1:                       # ?f=json → 元数据
            return self.meta()
        if q.get("returnCountOnly") == "true":
            lo, hi = _bounds_any(q.get("where", ""))
            return {"count": max(0, min(hi or self.n, self.n) - lo + 1)}
        if "outStatistics" in q:
            return {"features": [{"attributes": {"mn": 1, "mx": self.n}}]}
        if q.get("returnIdsOnly") == "true":
            return {"objectIdFieldName": self.oid, "objectIds": list(range(1, self.n + 1))}
        return self.page_query(q)

    def page_query(self, q):
        ps = int(q.get("resultRecordCount") or self.page)
        lo, hi, after = _bounds(self.oid, q.get("where", ""))
        hi = self.n if hi is None else min(hi, self.n)
        start = (after + 1) if after is not None else lo
        end = min(hi, start + ps - 1)
        if start > end:
            return {"features": [], "exceededTransferLimit": False}
        return {"features": [self.feat(i) for i in range(start, end + 1)],
                "exceededTransferLimit": end < hi}


# ---------------------------------------------------------------- A/B. pilot 行为
class FreshBase(unittest.TestCase):
    """把 pilot 圈在临时目录里跑：真采（假上游）、真落盘、真检查点、假上传/假 Release。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="fresh-")
        self.legacy = None                 # `_fetch_ckpt_asset` 的假返回值（raw 检查点）
        self.assets = {}
        self.uploads = []                  # [{name, rows, ns}]
        self._orig = (pilot.OUTBASE, dict(pilot.CUR), pilot.get_json, pilot._upload,
                      pilot.UNIT_ROWS, pilot._pub, pilot.PROG_DIR, pilot._q,
                      pilot.FRESH, dict(pilot.FRESH_MERGE_REPORT), pilot.UNIT_NS,
                      pilot._fetch_ckpt_asset, pilot._list_assets, pilot._backup_legacy_ckpt,
                      pilot.RUN_ID)
        pilot.OUTBASE = self.tmp
        pilot.PROG_DIR = os.path.join(self.tmp, "progress")
        pilot.UNIT_ROWS = 500              # 1200 行 → 3 个单元（400/400/400）
        # ★ `_pub` 的真实契约是 `(rc, 输出)`；打桩也必须返回二元组 ——
        #   返回 True 只会在**本机**侥幸通过（GITHUB_REPOSITORY 未设 → _publish_ckpt 早退），
        #   到 CI 上 GITHUB_REPOSITORY 一定存在 → `rc, o = True` → TypeError（smoke 45020368971）。
        pilot._pub = lambda *a, **k: (0, "")
        pilot.RUN_ID = "99999"
        pilot.UNIT_NS = ""
        pilot.FRESH = False
        pilot.CUR.update({"id": "L", "title": "L",
                          "url": "http://fake.local/FeatureServer/0", "svc": "FeatureServer"})

        def fake_upload(files, log=None, tag=None):
            got = sum(sum(1 for ln in gzip.open(f, "rt") if ln.strip()) for f in files)
            uid = os.path.basename(files[0]).split("-")[1]
            name = "%s-%s%s.tar.gz" % (pilot.CUR["id"], pilot.UNIT_NS, uid)  # 与真 _upload 同口径
            self.uploads.append({"name": name, "rows": got, "ns": pilot.UNIT_NS})
            return name

        pilot._upload = fake_upload
        pilot._fetch_ckpt_asset = lambda ph, log, with_raw=False: (
            (None, self.legacy) if with_raw else None)
        pilot._list_assets = lambda log=None: dict(self.assets)
        pilot._backup_legacy_ckpt = lambda ck, log, idx=None: ""

    def tearDown(self):
        (pilot.OUTBASE, cur, gj, up, pilot.UNIT_ROWS, pilot._pub, pilot.PROG_DIR, pilot._q,
         pilot.FRESH, report, pilot.UNIT_NS, pilot._fetch_ckpt_asset, pilot._list_assets,
         pilot._backup_legacy_ckpt, pilot.RUN_ID) = self._orig
        pilot.get_json = gj
        pilot.FRESH_MERGE_REPORT.clear()
        pilot.FRESH_MERGE_REPORT.update(report)
        pilot.CUR.clear()
        pilot.CUR.update(cur)
        shutil.rmtree(self.tmp, ignore_errors=True)

    # ---- 工具 ----
    def run_collect(self, svc):
        pilot.get_json = svc
        pilot._q = lambda api, params, timeout=180: svc(
            api + "/query?" + urllib.parse.urlencode(params), timeout)
        return pilot.collect_arcgis_v2(pilot.CUR["url"], 0, lambda m: None, 2, False)

    def ckpt(self):
        return json.load(open(os.path.join(self.tmp, "L", "_checkpoint.json"), encoding="utf-8"))


class TestForceResumeUnchanged(FreshBase):
    """A. force+resume（默认）：新采 0 行、旧包不动 —— 既有语义一个字不变。"""

    def test_resume_reports_full_rows_but_collects_nothingnew(self):
        svc = Svc()
        rows1, count1, err1, parts1 = self.run_collect(svc)
        self.assertEqual((rows1, count1, err1), (1200, 1200, ""))
        self.assertEqual(len(self.uploads), 3, "首次采集：3 个单元包")
        self.assertEqual(sum(u["rows"] for u in self.uploads), 1200)

        self.uploads.clear()
        rows2, count2, err2, parts2 = self.run_collect(svc)      # 第二次跑 = 续跑
        self.assertEqual((rows2, count2, err2), (1200, 1200, ""), "rows 仍取检查点里那 1200 行")
        self.assertEqual(self.uploads, [], "续跑必须新采 0 行（不许重采）")
        self.assertEqual(parts2, parts1)

    def test_resume_does_not_mark_fresh_or_supersede(self):
        self.run_collect(Svc())
        self.run_collect(Svc())
        ck = self.ckpt()
        self.assertFalse(ck.get("fresh_rerun"))
        self.assertFalse(ck.get("units_legacy"), "同切分续跑不该产生 legacy 记录（更不该 supersede）")
        self.assertEqual(pilot.FRESH_MERGE_REPORT, {})


class TestForceFreshReallyRecollects(FreshBase):
    """B. force+fresh：真重采 + 旧代际 supersede + rows_total = 新代单算。"""

    def _fresh_run(self):
        svc = Svc()
        self.run_collect(svc)                                   # 旧代际（UNIT_NS=""）
        self.legacy = json.loads(json.dumps(self.ckpt()))        # 上一轮检查点（3 个单元包）
        self.assets = {u["name"]: {"size": 1024, "state": "uploaded"}
                       for u in self.uploads}
        self.uploads.clear()
        pilot.FRESH = True
        return self.run_collect(svc)

    def test_new_rows_are_collected_and_old_generation_superseded(self):
        rows, count, err, parts = self._fresh_run()
        self.assertEqual(err, "")
        self.assertTrue(self.uploads, "fresh 必须有新采（否则和续跑没区别）")
        self.assertEqual(sum(u["rows"] for u in self.uploads), 1200, "新采行数 = 全层 1200")
        self.assertTrue(all(u["ns"].startswith("f") for u in self.uploads),
                        "新单元包必须带新代际前缀，才碰不到旧包：%r"
                        % [u["ns"] for u in self.uploads])

        ck = self.ckpt()
        sup = [u for u in (ck.get("units_legacy") or []) if u.get("superseded_by")]
        self.assertEqual(len(sup), 3, "旧代际 3 个单元包全部标 superseded_by")
        self.assertEqual(ck["rows_legacy_superseded"], 1200)
        self.assertEqual(ck["rows_total"], 1200, "rows_total 必须是新代际单算，不是 2400")
        self.assertEqual(rows, 1200)
        self.assertEqual(ck["rows_before_fresh"], 1200)
        self.assertTrue(ck.get("fresh_rerun"))
        self.assertEqual(pilot.FRESH_MERGE_REPORT["rows_superseded_by_fresh"], 1200)
        # 整层 3/3 单元都采完 → 整代 supersede（切分粒度变了也不怕按索引对不齐）
        self.assertEqual(pilot.FRESH_MERGE_REPORT["supersede_mode"], "fresh_all")

    def test_rows_invariant_holds_after_fresh(self):
        self._fresh_run()
        ck = self.ckpt()
        rep = CG.rows_recheck(self.legacy, ck, ck, "L")
        self.assertEqual(ck["rows_total"], rep["total"])
        self.assertEqual(rep["legacy_side"], 0, "旧代际被 supersede → counted_rows 全是 0")
        self.assertEqual(sum(u["counted_rows"] for u in ck["units_legacy"]), 0)
        self.assertEqual(rep["units_new_sum"], rep["new_side"])

    def test_second_fresh_run_does_not_double_count(self):
        """连跑两次 fresh：旧代际（含上一轮 fresh 的包）照样 supersede，行数不叠加。"""
        self._fresh_run()
        self.legacy = json.loads(json.dumps(self.ckpt()))
        self.assets.update({u["name"]: {"size": 1024, "state": "uploaded"} for u in self.uploads})
        self.uploads.clear()
        pilot.RUN_ID = "100000"                                 # 换一轮 = 换代际前缀
        rows, count, err, parts = self.run_collect(Svc())
        self.assertEqual(err, "")
        ck = self.ckpt()
        self.assertEqual(ck["rows_total"], 1200, "两轮 fresh 之后仍是 1200（不是 2400/3600）")
        self.assertEqual(rows, 1200)


# ---------------------------------------------------------------- C. 名单外层的层
class TestNonForcedLayersUntouched(unittest.TestCase):
    """C. 名单外的层：fresh 与否都一次不动（run_layer 调用 0 次），fresh 也不许外溢。"""

    def _run(self, force_fresh: bool):
        tmp = tempfile.mkdtemp(prefix="shard-")
        plan = {"size": 10, "unit_rows": 1000, "done_from": "05", "force_fresh": force_fresh,
                "shards": [{"shard": 0, "layers": ["A", "B", "C"]}]}
        path = os.path.join(tmp, "plan.json")
        json.dump(plan, open(path, "w", encoding="utf-8"))
        calls = []
        orig_here, orig_run = FS.HERE, FS.run_layer
        import worker_core
        orig_done, orig_rel = worker_core.done_layers, worker_core.release_done
        FS.HERE = tmp
        FS.run_layer = lambda step, lid, *a, **k: (
            calls.append((lid, k.get("fresh"))) or
            {"layer": lid, "status": "ok", "rows": 1, "declared": 1})
        worker_core.done_layers = lambda base: ["A", "C"]        # 名单外两层都已采过
        worker_core.release_done = lambda base: {"B": {"assets": []}}
        argv = sys.argv
        try:
            sys.argv = ["full_shard.py", "--stage", "05b", "--shard", "0", "--plan", path,
                        "--force-layers", "B"] + (["--force-fresh"] if force_fresh else [])
            rc = FS.main()
        finally:
            sys.argv = argv
            FS.HERE, FS.run_layer = orig_here, orig_run
            worker_core.done_layers, worker_core.release_done = orig_done, orig_rel
        led = json.load(open(os.path.join(tmp, "ledger", "05b_shard00.json"), encoding="utf-8"))
        return rc, calls, led

    def test_fresh_does_not_touch_layers_outside_force_list(self):
        rc, calls, led = self._run(True)
        self.assertEqual(rc, 0)
        self.assertEqual([c[0] for c in calls], ["B"], "名单外层的 run_layer 调用次数必须 0")
        self.assertIs(calls[0][1], True, "名单内那层必须是 fresh")
        recs = {r["layer"]: r for r in led["records"]}
        # 层记录上「请求了 fresh」= force_fresh（run_layer 里另有 fresh=采集侧证据，见下一组用例）
        self.assertTrue(recs["B"].get("force_fresh"))
        self.assertEqual([k for k, r in recs.items() if r.get("force_fresh")], ["B"],
                         "fresh 不许外溢到名单外")

    def test_without_fresh_nothing_changes(self):
        rc, calls, led = self._run(False)
        self.assertEqual(rc, 0)
        self.assertEqual([c[0] for c in calls], ["B"])
        self.assertIs(calls[0][1], False, "不传 --force-fresh → 仍是续跑（现状语义）")
        recs = {r["layer"]: r for r in led["records"]}
        self.assertFalse(recs["B"].get("force_fresh"))
        self.assertFalse(led["force_fresh"])


# ---------------------------------------------------------------- D. 反例 & 传透链
class TestRunLayerWiring(unittest.TestCase):
    """D. 反例 + 环境变量传透（plan → shard → pilot 的最后一跳就是这两个 env）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rl-")
        os.makedirs(os.path.join(self.tmp, "reports"))
        self._orig = (FS.HERE, FS.subprocess.run, os.environ.get("GITHUB_RUN_ID"))

    def tearDown(self):
        FS.HERE, FS.subprocess.run = self._orig[0], self._orig[1]
        if self._orig[2] is None:
            os.environ.pop("GITHUB_RUN_ID", None)
        else:
            os.environ["GITHUB_RUN_ID"] = self._orig[2]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _stub(self, report):
        FS.HERE = self.tmp
        json.dump(report, open(os.path.join(self.tmp, "reports", "L.json"), "w",
                               encoding="utf-8"))
        seen = {}

        class R:
            returncode = 0
            stdout = ""
            stderr = ""

        def fake_run(cmd, **kw):
            seen.update(kw.get("env") or {})
            return R()

        FS.subprocess.run = fake_run
        return seen

    def test_fresh_env_is_passed_to_pilot(self):
        os.environ["GITHUB_RUN_ID"] = "777"
        seen = self._stub({"count": 100, "rows": 100, "err": "", "diff": 0.0, "fresh": True,
                           "rows_before_fresh": 200, "rows_superseded_by_fresh": 100,
                           "units_legacy_superseded": 1, "units_new": 1})
        rec = FS.run_layer("05b", "L", 2, 1000, force_rerun=True, fresh=True)
        self.assertEqual(seen.get("PILOT_FORCE_FRESH"), "1", "fresh 必须真的传到 pilot")
        self.assertEqual(seen.get("PILOT_FORCE_RERUN"), "1", "fresh 同时要有旧检查点备份")
        self.assertTrue(rec.get("fresh"))
        self.assertEqual(rec["rows_superseded_by_fresh"], 100)
        self.assertEqual(rec["row_regression_evidence"], "collect/ledger/05b_run777.json")
        self.assertIn("superseded_by", rec["regression_reason"])
        self.assertEqual(rec["status"], "ok")

    def test_not_fresh_env_absent(self):
        seen = self._stub({"count": 100, "rows": 100, "err": "", "diff": 0.0})
        rec = FS.run_layer("05b", "L", 2, 1000, force_rerun=True, fresh=False)
        self.assertNotIn("PILOT_FORCE_FRESH", seen, "不传 fresh 时 pilot 必须完全走原路")
        self.assertNotIn("fresh", rec)

    def test_fresh_but_upstream_empty_is_flagged(self):
        """反例：fresh 传了但一行没采到 → 必须写 fresh_but_upstream_empty，不许当成功。"""
        seen = self._stub({"count": 500, "rows": 0, "err": "", "diff": 1.0, "fresh": True})
        rec = FS.run_layer("05b", "L", 2, 1000, force_rerun=True, fresh=True)
        self.assertEqual(seen.get("PILOT_FORCE_FRESH"), "1")
        self.assertTrue(rec.get("fresh_but_upstream_empty"))
        self.assertEqual(rec["status"], "failed")
        self.assertIn("不当作重采成功", rec["reason"])


# ---------------------------------------------------------------- supersede 语义（ckpt_guard）
def _ck(ns, rows_per_unit, plan_hash="h16", pkgs=None):
    n = len(rows_per_unit)
    return {"ver": 2, "url": "u", "plan_hash": plan_hash, "unit_ns": ns,
            "unit_rows": {str(i): r for i, r in enumerate(rows_per_unit)},
            "unit_files": {str(i): ["part-u%05d-000.ndjson.gz" % i] for i in range(n)},
            "unit_uploaded": {str(i): True for i in range(n)},
            "unit_package": dict(pkgs or {}),
            "done_units": list(range(n)),
            "rows_total": sum(rows_per_unit)}


class TestSupersedeMode(unittest.TestCase):
    """`supersede_legacy=True` 才在「切分兼容」时也 supersede —— 这就是 2× 的生成器开关。"""

    def test_fresh_supersedes_even_when_split_compatible(self):
        legacy = _ck("", [100, 100])
        new = _ck("f99999-", [100, 100])
        assets = {"L-u00000.tar.gz": {"size": 1, "state": "uploaded"},
                  "L-u00001.tar.gz": {"size": 1, "state": "uploaded"},
                  "L-f99999-u00000.tar.gz": {"size": 1, "state": "uploaded"},
                  "L-f99999-u00001.tar.gz": {"size": 1, "state": "uploaded"}}
        merged, rep = CG.merge_checkpoints(legacy, new, layer="L", run_id="1",
                                           assets=assets, supersede_legacy=True)
        self.assertEqual(rep["supersede_mode"], "fresh")
        self.assertTrue(rep["split_compatible"], "切分本来就一致（旧代际只是没带前缀）")
        self.assertEqual(rep["units_legacy_superseded"], 2)
        self.assertEqual(merged["rows_total"], 200, "新代单算，不是 400")
        self.assertEqual(merged["rows_legacy_superseded"], 200)

    def test_without_fresh_split_compatible_keeps_legacy(self):
        """不传 supersede_legacy → 保持既有语义（旧包当唯一副本计入），改前行为不变。"""
        legacy = _ck("", [100, 100])
        new = _ck("f99999-", [100, 100])
        merged, rep = CG.merge_checkpoints(legacy, new, layer="L", run_id="1",
                                           assets=None, supersede_legacy=False)
        self.assertEqual(rep["supersede_mode"], "none")
        self.assertEqual(rep["units_legacy_superseded"], 0)
        self.assertEqual(merged["rows_total"], 400)

    def _real_shape(self):
        """实测 qKAFwdGU 的检查点形状：unit_rows 是本代（r 前缀 2 包），`units_legacy` 里
        还挂着上一代的两个无前缀包；新代际只有一个单元（切分粒度变了）。"""
        legacy = _ck("r33297e41-", [90736, 90735], plan_hash="33297e4106002e9d")
        legacy["rows_total"] = 363000
        legacy["units_legacy"] = [
            {"package": "L-u00000.tar.gz", "idx": "0", "rows": 90765, "present": True,
             "counted_as": "units_legacy"},
            {"package": "L-u00001.tar.gz", "idx": "1", "rows": 90764, "present": True,
             "counted_as": "units_legacy"}]
        new = _ck("f99999-", [181471], plan_hash="33297e4106002e9d")
        return legacy, new

    def test_fresh_all_supersedes_across_unit_granularity(self):
        """整层重采完 → 旧代际整代 supersede（不按 unit 索引对齐，粒度变了也不重复计入）。"""
        legacy, new = self._real_shape()
        merged, rep = CG.merge_checkpoints(legacy, new, layer="L", run_id="1", assets=None,
                                           supersede_legacy=True, supersede_all=True)
        self.assertEqual(rep["supersede_mode"], "fresh_all")
        self.assertEqual(merged["rows_total"], 181471, "新代单算")
        self.assertEqual(rep["rows_legacy_superseded"], 363000, "旧那 363,000 行整代落档")
        self.assertEqual(rep["rows_before_incl_legacy_units"], 363000)
        self.assertEqual(sum(u["counted_rows"] for u in merged["units_legacy"]), 0)
        self.assertEqual(CG.rows_recheck(legacy, new, merged, "L")["total"], 181471)

    def test_without_supersede_all_unit_granularity_leaks_legacy_rows(self):
        """反证：只按 unit 索引 supersede（旧 2 单元 / 新 1 单元）会漏掉旧 u00001 —— 这就是
        为什么 fresh 整层采完必须走 supersede_all。"""
        legacy, new = self._real_shape()
        merged, rep = CG.merge_checkpoints(legacy, new, layer="L", run_id="1", assets=None,
                                           supersede_legacy=True, supersede_all=False)
        self.assertEqual(rep["supersede_mode"], "fresh")
        self.assertEqual(merged["rows_total"], 362970,
                         "新代 181,471 + 旧 u00001(90,764) + 旧本代 u00001(90,735) 都被照计")

    def test_fresh_keeps_legacy_when_new_unit_not_uploaded(self):
        """新代际该单元没上传成功 → 旧包是唯一可用副本，照计（fresh 也不许丢数据）。"""
        legacy = _ck("", [100, 100])
        new = _ck("f99999-", [100, 100])
        new["unit_uploaded"]["1"] = False
        merged, rep = CG.merge_checkpoints(legacy, new, layer="L", run_id="1",
                                           assets=None, supersede_legacy=True)
        self.assertEqual(rep["units_legacy_superseded"], 1, "只 supersede 上传成功的那个索引")
        self.assertEqual(merged["rows_total"], 300, "新代 200 + 旧包唯一副本 100")


# ---------------------------------------------------------------- `_pub` 契约（不许被测试掩盖）
class TestPubContractNotStubbed(unittest.TestCase):
    """`_pub` 必须是 `(rc, 输出)` 二元组 —— 这条测试**不打桩 `_pub`**。

    ★ 为什么必须有（2026-11-22 CI 真红，smoke run 45020368971 / PR #41）：
      上一版把 `pilot._pub` 打桩成返回 `True`。本机 `GITHUB_REPOSITORY` 未设置 →
      `_publish_ckpt` 在 `/tmp` 之前就 `return False`，解包那行永远不执行 → 本机「569 OK」；
      CI 上 `GITHUB_REPOSITORY` 一定存在 → `rc, o = True` → TypeError，5 个用例全红。
      打桩可以把契约错掩盖住，所以这里只把 `subprocess.run` 换成假进程，`_pub` 走真实实现。
    """

    def setUp(self):
        self._orig = (pilot.CUR.get("id"), os.environ.get("GITHUB_REPOSITORY"),
                      pilot.subprocess.run, pilot._tag)
        self.real_run = pilot.subprocess.run                 # 真 run（给「真跑一次」那条用）
        pilot.CUR["id"] = "L"
        os.environ["GITHUB_REPOSITORY"] = "owner/repo"        # ★ CI 上它一定存在，本机靠它复现
        pilot._tag = lambda: "collect-test-L"
        self.calls = []

        class R:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def fake_run(cmd, **kw):
            self.calls.append(cmd)
            return R()

        self.fake_run = fake_run
        pilot.subprocess.run = fake_run                       # 只拦进程，不拦契约

    def tearDown(self):
        cid, rep, run_, tag = self._orig
        pilot.subprocess.run, pilot._tag = run_, tag
        pilot.CUR["id"] = cid
        if rep is None:
            os.environ.pop("GITHUB_REPOSITORY", None)
        else:
            os.environ["GITHUB_REPOSITORY"] = rep

    def test_pub_returns_rc_and_output_tuple(self):
        """真跑一次子进程（`_pub` 与 `subprocess.run` 都不打桩）：返回值必须是 (int, str)。"""
        pilot.subprocess.run = self.real_run
        try:
            rc, out = pilot._pub([sys.executable, "-c", "print('hello')"])
        finally:
            pilot.subprocess.run = self.fake_run
        self.assertIsInstance(rc, int)
        self.assertIsInstance(out, str)
        self.assertIn("hello", out)

    def test_publish_ckpt_unpacks_pub_as_tuple(self):
        """`_publish_ckpt` 直接按 (rc, o) 解包 → `_pub` 一改契约就在这里红（本机也红）。"""
        ok = pilot._publish_ckpt({"ver": 2, "plan_hash": "h"}, lambda m: None)
        self.assertIs(ok, True)
        last = self.calls[-1]
        self.assertEqual(last[:4], ["gh", "release", "upload", "collect-test-L"])
        self.assertIn("--clobber", last)


# ---------------------------------------------------------------- 账本口径
class TestFreshInLedgerMerge(unittest.TestCase):
    def test_fresh_rerun_is_authoritative_not_bigger_rows(self):
        base = [{"layer": "q", "status": "ok", "rows": 363000, "declared": 181471}]
        run = [{"layer": "q", "status": "ok", "rows": 181471, "declared": 181471,
                "fresh": True, "regression_reason": "fresh 真重采：旧代际 supersede",
                "row_regression_evidence": os.path.abspath(__file__)}]
        merged, stats = LM.merge_records(base, run)
        self.assertEqual(merged[0]["rows"], 181471, "fresh 记录是权威值，不许被大数挤掉")

    def test_non_fresh_still_keeps_bigger_rows(self):
        base = [{"layer": "q", "status": "ok", "rows": 363000, "declared": 181471}]
        run = [{"layer": "q", "status": "ok", "rows": 181471, "declared": 181471}]
        merged, stats = LM.merge_records(base, run)
        self.assertEqual(merged[0]["rows"], 363000, "没 fresh 标记 → 旧行为（保大数）不变")

    def test_failed_fresh_does_not_override_ok(self):
        base = [{"layer": "q", "status": "ok", "rows": 100, "declared": 100}]
        run = [{"layer": "q", "status": "failed", "rows": 0, "declared": 100, "fresh": True}]
        merged, _ = LM.merge_records(base, run)
        self.assertEqual(merged[0]["rows"], 100, "fresh 失败也不许把 ok 值冲掉")


class TestAnnotateLedgerFile(unittest.TestCase):
    """被旧代码 merge 抹掉的 `rows_suspect` 标记要能补回来，且 rows 一个 digit 都不动。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ann-")
        self.path = os.path.join(self.tmp, "05b_ledger.json")
        json.dump({"schema": "collect-ledger-agg/v1", "layers_n": 3, "rows": 400,
                   "records": [{"layer": "a", "status": "ok", "rows": 200, "declared": 100},
                               {"layer": "b", "status": "ok", "rows": 100, "declared": 100},
                               {"layer": "c", "status": "ok", "rows": 100, "declared": 100}]},
                  open(self.path, "w", encoding="utf-8"))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_markers_restored_and_rows_untouched(self):
        res = LM.annotate_ledger_file(self.path, run_id="45010130014")
        self.assertEqual((res["marked_before"], res["marked_after"]), (0, 1))
        self.assertTrue(res["rows_unchanged"])
        d = json.load(open(self.path, encoding="utf-8"))
        a = [r for r in d["records"] if r["layer"] == "a"][0]
        self.assertEqual(a["rows"], 200, "rows 不回改")
        self.assertEqual(a["rows_legacy_kept"], 100)
        self.assertEqual(a["rows_suspect"], "legacy_double_count")
        self.assertEqual(d["rows_suspect"]["layers"], 1)
        self.assertEqual(d["rows_suspect"]["overcounted_rows"], 100)

    def test_idempotent(self):
        LM.annotate_ledger_file(self.path, run_id="r1")
        first = open(self.path, encoding="utf-8").read()
        res2 = LM.annotate_ledger_file(self.path, run_id="r2")
        second = open(self.path, encoding="utf-8").read()
        self.assertEqual((res2["marked_before"], res2["marked_after"]), (1, 1))
        self.assertTrue(res2["rows_unchanged"])
        strip = lambda s: [ln for ln in s.splitlines() if "detected_at" not in ln
                           and "run_id" not in ln]
        self.assertEqual(strip(first), strip(second), "除了判定时间/轮次，结果必须逐字相同")


if __name__ == "__main__":
    unittest.main()
