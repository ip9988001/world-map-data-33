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
        self._old = (W.ROOT, W.HERE, W._URL_IDX)
        W.ROOT, W.HERE, W._URL_IDX = self.tmp, self.tmp, None

    def tearDown(self):
        W.ROOT, W.HERE, W._URL_IDX = self._old

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
