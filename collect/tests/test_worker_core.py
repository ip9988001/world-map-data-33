# -*- coding: utf-8 -*-
"""worker_core 选层逻辑单测（零网络、零文件依赖：全部用临时文件）"""
import csv
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import worker_core as W  # noqa: E402


class TestSelect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="wc-")
        self.csv = os.path.join(self.tmp, "plan.csv")
        rows = [
            dict(layer_id="a1", state="KS", title="A1", svc="FeatureServer", url="http://x/a1",
                 row_count="500000", pagination="true", defexpr="", maxrc="2000", nfields="10",
                 geom="Point", pagesize="2000", plan="keyset", note=""),
            dict(layer_id="a2", state="KS", title="A2", svc="FeatureServer", url="http://x/a2",
                 row_count="100", pagination="true", defexpr="", maxrc="2000", nfields="10",
                 geom="Polygon", pagesize="2000", plan="keyset", note=""),
            dict(layer_id="a3", state="KS", title="A3", svc="FeatureServer", url="http://x/a3",
                 row_count="", pagination="false", defexpr="", maxrc="2000", nfields="10",
                 geom="", pagesize="2000", plan="skip", note=""),
            dict(layer_id="b1", state="TX", title="B1", svc="FeatureServer", url="http://x/b1",
                 row_count="900000", pagination="true", defexpr="", maxrc="2000", nfields="10",
                 geom="Point", pagesize="2000", plan="keyset", note=""),
        ]
        with open(self.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        self._old = (W.PLAN_F, W.LAYERS_F)
        W.PLAN_F, W.LAYERS_F = self.csv, os.path.join(self.tmp, "layers.json")

    def tearDown(self):
        W.PLAN_F, W.LAYERS_F = self._old

    def pol(self, **kw):
        return dict(kw)

    def test_state_filter(self):
        out = W.select_layers("03", policy=self.pol(select={"state": "KS"}, geom_in=["point"]))
        self.assertEqual([r["id"] for r in out], ["a1"])

    def test_geom_whitelist_drops_polygon(self):
        """默认 policy（含 geom_in）必须把 Polygon / 未知几何剔除"""
        out = W.select_layers("03", policy=W.load_policy("03"))
        ids = [r["id"] for r in out]
        self.assertIn("a1", ids)
        self.assertNotIn("a2", ids)      # Polygon
        self.assertNotIn("a3", ids)      # 几何未知

    def test_where_filter(self):
        out = W.select_layers("04", policy=self.pol(select={"where": "row_count>300000"}, geom_in=["point"]))
        self.assertEqual([r["id"] for r in out], ["a1", "b1"])

    def test_bulk_skips_skip_and_slices(self):
        out = W.select_layers("05", policy=self.pol(select={"mode": "bulk", "offset": 0, "batch": 0},
                                                    geom_in=["point"], batch=1))
        self.assertNotIn("a3", [r["id"] for r in out])          # plan=skip 必须剔除
        self.assertEqual(len(out), 1)                            # 批量切片生效

    def test_missing_url_dropped(self):
        rows = [{"layer_id": "nourl", "state": "KS", "url": "", "row_count": "10", "geom": "Point"}]
        with open(self.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        self.assertEqual(W.select_layers("03", policy=self.pol(select={"state": "KS"})), [])



class TestStepsConfig(unittest.TestCase):
    """C1：steps.json 是唯一参数来源，校验器必须真的拦得住错配置"""

    def test_real_config_is_valid(self):
        ok, errs = W.validate(W.STEPS_F)
        self.assertTrue(ok, errs)

    def test_catches_bad_kind(self):
        import tempfile
        d = tempfile.mkdtemp()
        p = os.path.join(d, "steps.json")
        cfg = json.load(open(W.STEPS_F, encoding="utf-8"))
        cfg["steps"]["03"]["kind"] = "whatever"
        json.dump(cfg, open(p, "w"))
        ok, errs = W.validate(p)
        self.assertFalse(ok)
        self.assertTrue(any("kind" in e for e in errs))

    def test_catches_missing_layer_placeholder_in_tag(self):
        import tempfile
        d = tempfile.mkdtemp()
        p = os.path.join(d, "steps.json")
        cfg = json.load(open(W.STEPS_F, encoding="utf-8"))
        cfg["steps"]["04"]["tag"] = "collect-step04"          # 少了 {layer} → 7 个层会共用一个 tag
        json.dump(cfg, open(p, "w"))
        ok, errs = W.validate(p)
        self.assertFalse(ok)
        self.assertTrue(any("{layer}" in e for e in errs))



class TestStep10(unittest.TestCase):
    """STEP-10 宗地扩采：四个曾让选层静默归零的坑，逐个钉住

    2026-10-26 实测踩出来的，不写测试就会在下次迁移时原样复现：
      1) 批清单列名是 layer 而非 layer_id → 曾全部落到空键、被唯一化成 "@NC-1"、选中 0 层
      2) 批清单没有 url 列 → 必须从 situs_layers.csv 回填
      3) eff 用 0~100 百分数，eff_min 用 0~1 小数 → 直接比较会把 100.0 判成不达标
      4) 宗地层是 Polygon → 不显式 geom_in=[] 就会被 engine.geom_allow 全部过滤掉
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="s10-")
        with open(os.path.join(self.tmp, "situs_layers.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["layer_id", "state", "geom", "rows", "grade", "url"])
            w.writeheader()
            w.writerows([
                dict(layer_id="p1", state="KS", geom="Polygon", rows="5000", grade="strong", url="http://x/p1"),
                dict(layer_id="p2", state="TX", geom="Polygon", rows="200", grade="weak", url="http://x/p2"),
                dict(layer_id="p3", state="KS", geom="Polygon", rows="10", grade="weak", url="http://x/p3"),
            ])
        with open(os.path.join(self.tmp, "batch1.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["layer", "state", "grade", "declared", "eff"])
            w.writeheader()
            w.writerows([
                dict(layer="p1", state="KS", grade="strong", declared="5000", eff="100.0"),
                dict(layer="p2", state="TX", grade="weak", declared="200", eff="50.0"),
                dict(layer="p3", state="KS", grade="weak", declared="10", eff="5.0"),      # 有效率不达标
                dict(layer="p9", state="KS", grade="weak", declared="10", eff="100.0"),    # situs 无此层 → 无 url
            ])
        self._old = (W.ROOT, W.HERE, W._URL_IDX, os.environ.get("WC_OFFLINE"))
        W.ROOT, W.HERE, W._URL_IDX = self.tmp, self.tmp, None
        os.environ["WC_OFFLINE"] = "1"      # 单测不许打 gh api（会真的拉几十页 Releases）

    def tearDown(self):
        W.ROOT, W.HERE, W._URL_IDX, offline = self._old
        if offline is None:
            os.environ.pop("WC_OFFLINE", None)
        else:
            os.environ["WC_OFFLINE"] = offline

    def sel(self, **kw):
        s = {"source": "layer_plan", "file": "batch1.csv",
             "grade": ["strong", "weak"], "eff_min": 0.2}
        s.update(kw)
        return {"kind": "parcel_situs", "title": "宗地地址扩采", "select": s,
                "workers": 4, "unit_rows": 100000, "tag": "collect-step10-{layer}", "geom_in": []}

    def test_layer_column_and_url_backfill(self):
        """列名 layer、清单无 url：仍须选到层，且 url 从 situs 回填（曾整批归零）"""
        out = W.select_layers("10", policy=self.sel())
        self.assertEqual(sorted(r["id"] for r in out), ["p1", "p2"])
        self.assertTrue(all(r["url"].startswith("http://x/") for r in out), out)

    def test_eff_percent_scale(self):
        """eff 百分数 100.0 满足 eff_min=0.2；5.0 不满足"""
        ids = [r["id"] for r in W.select_layers("10", policy=self.sel())]
        self.assertIn("p1", ids)
        self.assertNotIn("p3", ids)
        self.assertNotIn("p9", ids)          # 无 url 必须剔除

    def test_polygon_survives_when_geom_in_empty(self):
        """geom_in=[] 必须是「不过滤」；否则 Polygon 宗地层被点几何白名单全杀"""
        self.assertTrue(W.select_layers("10", policy=self.sel()))

    def test_bulk_window_slices(self):
        out = W.select_layers("10", policy=self.sel(mode="bulk", offset=1, batch=1))
        self.assertEqual([r["id"] for r in out], ["p2"])

    def test_resolve_strips_bulk_window(self):
        """matrix 第 N 层反查会剥掉 mode/offset/batch：剥掉后必须能选到全量"""
        pol = self.sel(mode="bulk", offset=1, batch=1)
        win = W.select_layers("10", policy=pol)
        bare = {k: v for k, v in pol["select"].items() if k not in ("mode", "offset", "batch")}
        self.assertEqual(len(win), 1)
        self.assertEqual(len(W.select_layers("10", policy=dict(pol, select=bare))), 2)

    def test_real_config_has_step10(self):
        """真 steps.json：STEP-10 必须齐 tag / evidence(releases) / workers / unit_rows"""
        cfg = json.load(open(W.STEPS_F, encoding="utf-8"))["steps"]["10"]
        self.assertIn("{layer}", cfg["tag"])
        self.assertIn("releases", cfg["evidence"])
        self.assertGreater(cfg["workers"], 0)
        self.assertGreater(cfg["unit_rows"], 0)
        self.assertEqual(cfg["geom_in"], [])
    def _write_done(self, complete=(), partial=()):
        doc = {"source": "test", "layers": {}}
        for x in complete:
            doc["layers"][x] = {"complete": True, "rows": 1}
        for x in partial:
            doc["layers"][x] = {"complete": False, "rows": 1}
        with open(os.path.join(self.tmp, "parcel_done.json"), "w", encoding="utf-8") as f:
            json.dump(doc, f)

    def test_skip_done_drops_complete_layers(self):
        """parcel_done.json 里 complete=true 的层必须被剔掉，partial 的保留"""
        self._write_done(complete=["p1"], partial=["p2"])
        out = W.select_layers("10", policy=self.sel(skip_done=True))
        self.assertEqual([r["id"] for r in out], ["p2"])

    def test_skip_done_off_keeps_everything(self):
        """skip_done=False 用于 --layer 反查：已采层也必须查得到，否则 unknown_layer"""
        self._write_done(complete=["p1", "p2"])
        out = W.select_layers("10", policy=self.sel(skip_done=False))
        self.assertEqual(sorted(r["id"] for r in out), ["p1", "p2"])

    def test_skip_done_happens_before_bulk_window(self):
        """剔除必须在窗口切片之前：否则切出的 2 层里还混着已采层，等于白跑"""
        self._write_done(complete=["p1"])
        out = W.select_layers("10", policy=self.sel(skip_done=True, mode="bulk", offset=0, batch=2))
        # p1 已采 → 待采 [p2]；窗口 size=2 只能取到 p2
        self.assertEqual([r["id"] for r in out], ["p2"])



class TestReleaseScanLoud(unittest.TestCase):
    """Releases 扫不全绝不能被当成「这些层没采过」。

    2026-10-30 实测：翻到第 3 页失败 → 只认出 185 个 tag（真值 288），剩下的已采层
    全被判「没采过」→ 续跑会把它们重采一遍（几百小时带宽）。宁可炸，不许装。
    """

    def setUp(self):
        self._gh, self._off = W._gh, os.environ.pop("WC_OFFLINE", None)

    def tearDown(self):
        W._gh = self._gh
        if self._off is not None:
            os.environ["WC_OFFLINE"] = self._off

    def test_page_failure_raises(self):
        W._gh = lambda p: None
        with self.assertRaises(RuntimeError):
            W._gh_page("repos/x/releases?page=1", tries=1)

    def test_page_retry_then_success(self):
        calls = {"n": 0}

        def flaky(p):
            calls["n"] += 1
            return None if calls["n"] == 1 else [{"tag_name": "collect-step04-a"}]
        W._gh = flaky
        self.assertEqual(W._gh_page("p", tries=3), [{"tag_name": "collect-step04-a"}])
        self.assertEqual(calls["n"], 2)

    def test_offline_mode_is_explicit_empty(self):
        W._gh = lambda p: None
        os.environ["WC_OFFLINE"] = "1"
        try:
            self.assertEqual(W._gh_page("p"), [])
        finally:
            os.environ.pop("WC_OFFLINE", None)


class TestLedgerVeto(unittest.TestCase):
    """W33-040：短采层（`status=failed` 且 `rows>0`）不许被 Release 浅判算成「已完成」。

    2026-10-31 实测（run `41167836540` 收尾）：5 层「片账本 failed、rows 不是 0、checkpoint 已传」→
    `release_done` 只看「tag + 有 checkpoint」就判完成 → 这 5 层再也不会排进计划，
    缺口永久钉死；而且看上去「有数据」，比 `failed(0 行)` 难发现得多。
    """

    LAYERS = ("short", "done_ok", "done_empty", "done_capped", "done_unstable")

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="veto-")
        with open(os.path.join(self.tmp, "batch1.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["layer", "state", "grade", "declared", "eff"])
            w.writeheader()
            w.writerows([dict(layer=x, state="KS", grade="strong", declared="5000", eff="100.0")
                         for x in self.LAYERS])
        # batch1.csv 不存 url，url 从 situs_layers.csv 回填（没 url 的行会被整行剔掉）
        with open(os.path.join(self.tmp, "situs_layers.csv"), "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["layer_id", "state", "geom", "rows", "grade", "url"])
            w.writeheader()
            w.writerows([dict(layer_id=x, state="KS", geom="Point", rows="5000", grade="strong",
                              url="http://x/%s" % x) for x in self.LAYERS])
        self._old = (W.ROOT, W.HERE, W._URL_IDX, W.release_done, os.environ.get("WC_OFFLINE"))
        W.ROOT, W.HERE, W._URL_IDX = self.tmp, self.tmp, None
        os.environ["WC_OFFLINE"] = "1"
        # Release 浅判：五层都有 tag + checkpoint（对旧实现来说这五层全都「已完成」）
        W.release_done = lambda step="05", use_cache=True: {
            x: {"tag": "collect-step%s-%s" % (step, x), "assets": ["%s-checkpoint.json" % x],
                "complete": True, "how": "shallow"} for x in self.LAYERS}

    def tearDown(self):
        W.ROOT, W.HERE, W._URL_IDX, W.release_done, offline = self._old
        if offline is None:
            os.environ.pop("WC_OFFLINE", None)
        else:
            os.environ["WC_OFFLINE"] = offline

    def _ledger(self, records):
        with open(os.path.join(self.tmp, "05b_ledger.json"), "w", encoding="utf-8") as f:
            json.dump({"schema": "collect-ledger-agg/v1", "stage": "05b", "records": records}, f)

    def test_short_collect_is_not_done(self):
        """failed + rows>0 且 rows<declared → 不算完成（要重新参赛）"""
        self._ledger([{"layer": "short", "status": "failed", "rows": 9602, "declared": 17295},
                      {"layer": "done_ok", "status": "ok", "rows": 5000, "declared": 5000}])
        done = W.done_layers("05")
        self.assertNotIn("short", done)
        self.assertIn("done_ok", done)

    def test_three_legal_ways_to_be_done(self):
        """合法算完成的三种：ok / empty / 已判 capped（再试没收益）；unstable 同理"""
        self._ledger([
            {"layer": "done_ok", "status": "ok", "rows": 5000, "declared": 5000},
            {"layer": "done_empty", "status": "empty", "rows": 0, "declared": 0},
            {"layer": "done_capped", "status": "capped_by_upstream", "rows": 39, "declared": 100},
            {"layer": "done_unstable", "status": "upstream_unstable", "rows": 0, "declared": 100},
        ])
        done = W.done_layers("05")
        for x in ("done_ok", "done_empty", "done_capped", "done_unstable"):
            self.assertIn(x, done, x)

    def test_vetoed_layer_comes_back_into_plan(self):
        """否决完必须能在计划里重新看到它（否则修了等于没修）"""
        self._ledger([{"layer": "short", "status": "failed", "rows": 9602, "declared": 17295}])
        pol = {"kind": "parcel_situs", "title": "t", "geom_in": [],
               "select": {"source": "layer_plan", "file": "batch1.csv", "grade": ["strong"],
                          "eff_min": 0.2, "skip_done": True},
               "workers": 4, "unit_rows": 100000, "tag": "collect-step05-{layer}"}
        ids = [r["id"] for r in W.select_layers("05", policy=pol)]
        self.assertIn("short", ids)
        self.assertNotIn("done_ok", ids)

    def test_partial_with_enough_rows_is_done(self):
        """行数其实够了（≥99% 声明）只是收尾报错 → 采完了，别为 1% 再烧一轮"""
        self._ledger([{"layer": "short", "status": "partial", "rows": 17130, "declared": 17295}])
        self.assertIn("short", W.done_layers("05"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
