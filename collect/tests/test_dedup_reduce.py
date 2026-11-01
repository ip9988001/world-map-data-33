# -*- coding: utf-8 -*-
"""`collect/dedup_reduce.py` 的边界单测：键解析、方向补全、重发层折叠、守恒。

不碰网络、不读 Release：用临时目录造 3 行 spill 跑一遍 reduce。
"""
import gzip
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)

import dedup_reduce as DR      # noqa: E402


def _row(county, key, layer, group="LOCAL_GIS", fp="", street_src="top", num="1"):
    return {"s": "IA", "c": county, "k": num, "sk": key, "u": "", "ur": "",
            "st": "MAIN", "ty": "ST", "pd": "", "po": "", "z": "50000", "ci": "X",
            "la": 41.0, "lo": -91.0, "L": layer, "k_": "%s|%s|%s|%s|" % ("IA", county, num, key),
            "ss": street_src, "t": "2026-10-31T00:00:00Z"}


class KeyParsing(unittest.TestCase):
    def test_split_key_seven_parts(self):
        st, co, num, skey, ukey = DR.split_key("IA|19113|412|STREET|3|S|D")
        self.assertEqual((st, co, num, skey, ukey), ("IA", "19113", "412", "STREET|3|S", "D"))

    def test_nodir_drops_dir(self):
        self.assertEqual(DR.nodir_key("IA|19113|412|STREET|3|S|D"),
                         "IA|19113|412|STREET|3||D")

    def test_different_dir_are_different_keys(self):
        a = DR.split_key("IA|19113|1|STREET|MAIN|E|")
        b = DR.split_key("IA|19113|1|STREET|MAIN|W|")
        self.assertNotEqual(a[3], b[3])


class Tier(unittest.TestCase):
    def test_two_groups_is_a(self):
        self.assertEqual(DR.tier_of({"NAD", "NG911"}, False, "top", "ok"), "A")

    def test_dir_inferred_drops_to_b(self):
        self.assertEqual(DR.tier_of({"NAD", "NG911"}, True, "top", "ok"), "B")

    def test_fulltext_is_u(self):
        self.assertEqual(DR.tier_of({"NAD"}, False, "full", "ok"), "U")

    def test_no_s_without_tiger(self):
        self.assertNotEqual(DR.tier_of({"NAD", "NG911", "LOCAL_GIS"}, False, "top", "ok"), "S")


class Pipeline(unittest.TestCase):
    def _mk(self, tmp, rows, layers):
        spill = os.path.join(tmp, "spill")
        os.makedirs(spill, exist_ok=True)
        with gzip.open(os.path.join(spill, "spill-shard00-b00.ndjson.gz"), "wt",
                       encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r) + "\n")
        with open(os.path.join(spill, "layers.jsonl"), "w", encoding="utf-8") as fh:
            for i, L in enumerate(layers):
                fh.write(json.dumps({"layer": L[0], "src_group": L[1],
                                     "dataset_fingerprint": L[2], "status": "ok"}) + "\n")
        json.dump({}, open(os.path.join(spill, "county_names.json"), "w"))
        return spill

    def test_duplicate_dataset_counts_one_vote(self):
        """同一 dataset_fingerprint 的两层只算 1 票；不同源组才是 2 票。"""
        tmp = tempfile.mkdtemp()
        rows = [_row("19113", "STREET|MAIN|", 0), _row("19113", "STREET|MAIN|", 1)]
        layers = [("L0", "LOCAL_GIS", "FP1"), ("L1", "LOCAL_GIS", "FP1")]
        spill = self._mk(tmp, rows, layers)
        out = os.path.join(tmp, "out")
        os.makedirs(os.path.join(out, "reports"), exist_ok=True)
        sys_argv = sys.argv
        sys.argv = ["x", "--spill", spill, "--out", out]
        try:
            DR.main()
        finally:
            sys.argv = sys_argv
        rep = json.load(open(os.path.join(out, "reports", "reduce.json")))
        self.assertEqual(rep["keys_out"], 1)
        self.assertEqual(rep["dup_members_total"], 1)
        self.assertEqual(rep["duplicate_dataset_votes_dropped"], 1)
        self.assertTrue(rep["conservation"]["rows_in == keys_out + dup_members"])
        led = os.path.join(out, "ledger", "state=IA", "county=19113.ndjson.gz")
        row = json.loads(gzip.open(led, "rt", encoding="utf-8").readline())
        self.assertEqual(row["independent_sources_n"], 1)

    def test_two_groups_two_votes(self):
        tmp = tempfile.mkdtemp()
        rows = [_row("19113", "STREET|MAIN|", 0), _row("19113", "STREET|MAIN|", 1)]
        layers = [("L0", "NAD", "FP1"), ("L1", "NG911", "FP2")]
        spill = self._mk(tmp, rows, layers)
        out = os.path.join(tmp, "out")
        os.makedirs(os.path.join(out, "reports"), exist_ok=True)
        sys_argv = sys.argv
        sys.argv = ["x", "--spill", spill, "--out", out]
        try:
            DR.main()
        finally:
            sys.argv = sys_argv
        led = os.path.join(out, "ledger", "state=IA", "county=19113.ndjson.gz")
        row = json.loads(gzip.open(led, "rt", encoding="utf-8").readline())
        self.assertEqual(row["independent_sources_n"], 2)
        self.assertEqual(row["tier"], "A")


if __name__ == "__main__":
    unittest.main()
