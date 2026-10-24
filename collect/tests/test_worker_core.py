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



if __name__ == "__main__":
    unittest.main(verbosity=2)
