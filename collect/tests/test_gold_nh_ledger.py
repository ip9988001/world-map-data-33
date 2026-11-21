#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""契约测试：`collect/ledger/gold_nh_v1_rebuilt.json`（二仓 Release 只读补登）必须能被
三仓现有台账口径直接读，不许自成一套。

背景（2026-11-22，Phase 0 排雷·任务 2）：二仓 Release `gold-US-NH-v1` 有 13 个资产
（10 个 ADDR 地址层 + 3 个元数据文件），10 个地址层实测解压后 0 字节 / 0 行，
`STATUS.json` 却 `ok:true`。把这 13 个资产按 `collect-ledger-rebuild/v1`（= `ledger_rebuild.py`
的「资产即真值」口径）补登进三仓台账，本测试锁住三件事：

1. 顶层键与 `step04b_rebuilt.json` 同构（同键集，供 `--rebuilt` 类读取器直接吃）；
2. 每条 record 同时满足 `collect-ledger/v1` 的必备字段（layer/declared/rows/status/reason），
   且 `status` 落在 `step_full_report.py` 的 rank 表里（不许出现自定义状态）；
3. 13 个资产全部有实测行数，且 0 行层必须 `status=empty`、`rows=0`、`declared=0`——
   空包不许写成 ok。
"""
import json
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
LEDGER = os.path.join(ROOT, "collect", "ledger", "gold_nh_v1_rebuilt.json")
REF = os.path.join(ROOT, "collect", "ledger", "step04b_rebuilt.json")

# step_full_report.py 的 status 排序表（同一层出现多次取「最好」的那次）
RANK = {"ok": 4, "empty": 3, "skipped_done": 2, "partial": 1, "failed": 0}
V1_REQUIRED = {"layer", "declared", "rows", "status", "reason"}


def load():
    with open(LEDGER, encoding="utf-8") as f:
        return json.load(f)


class GoldNhLedgerTest(unittest.TestCase):
    def setUp(self):
        self.d = load()

    def test_schema_and_toplevel_isomorphic(self):
        self.assertEqual(self.d["schema"], "collect-ledger-rebuild/v1")
        with open(REF, encoding="utf-8") as f:
            ref = json.load(f)
        self.assertEqual([k for k in ref if k not in self.d], [],
                         "顶层键必须覆盖 step04b_rebuilt.json 的全部键")

    def test_thirteen_assets_all_measured(self):
        self.assertEqual(self.d["assets_total"], 13)
        idx = self.d["assets_index"]
        self.assertEqual(len(idx), 13)
        for a in idx:
            self.assertIsInstance(a["lines"], int)
            self.assertEqual(len(a["sha256"]), 64)
            self.assertEqual(a["size"], a["bytes_gz"], "API size 与实测压缩字节必须一致")
        self.assertEqual(sum(1 for a in idx if a["kind"] == "addr_layer"), 10)

    def test_records_readable_as_collect_ledger_v1(self):
        for r in self.d["records"]:
            self.assertFalse(V1_REQUIRED - set(r), "缺 collect-ledger/v1 字段：%s" % r.get("layer"))
            self.assertIn(r["status"], RANK, "status 必须是既有枚举：%s" % r.get("status"))
            self.assertIsInstance(r["declared"], int)
            self.assertIsInstance(r["rows"], int)

    def test_empty_layers_never_reported_ok(self):
        data = [r for r in self.d["records"] if r["asset"].endswith(".ndjson.gz")]
        self.assertEqual(len(data), 10)
        for r in data:
            self.assertEqual(r["rows"], 0, r["layer"])
            self.assertEqual(r["bytes_dec"], 0, r["layer"])
            self.assertEqual(r["sha256_claimed"], r["sha256_actual"], "自述 sha256 必须与实物一致")
            self.assertEqual(r["status"], "empty", "0 行层不许写 ok：%s" % r["layer"])
        self.assertEqual([r["layer"] for r in data], self.d["empty_layers"])

    def test_aggregation_matches_full_report_rule(self):
        by = {}
        for r in self.d["records"]:
            prev = by.get(r["layer"])
            if prev is None or RANK.get(r["status"], 0) > RANK.get(prev["status"], 0):
                by[r["layer"]] = r
        self.assertEqual(len(by), 13, "层名不许重复")
        self.assertEqual(sum(r["declared"] for r in by.values()), 0)
        self.assertEqual(sum(r["rows"] for r in by.values()), 0)
        self.assertEqual([r["layer"] for r in by.values() if r["status"] in ("failed", "partial")], [])

    def test_verdict_says_cannot_fuse(self):
        v = self.d["verdict"]
        self.assertEqual(v["can_fuse_into_gold"], [])
        self.assertEqual(len(v["cannot_fuse"]), 10)
        self.assertEqual(len(v["pending_upstream"]), 10)


if __name__ == "__main__":
    unittest.main(verbosity=2)
