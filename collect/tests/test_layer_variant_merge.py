#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W33-048 缺陷 A 单测：`@<状态>-<n>` 变体只算**一层**，且 force 能把它提到队首。

事故：层 `_services_Address_Points_AddressPoint_Native_FeatureServer_0` 在清单里有两行
（baltegis / egis 两个入口，都 state=未定位），唯一化后成 `@未定位-1` / `@未定位-2`：
  · plan 里被当成两层，各占一个名额；
  · Release 只有 `@未定位-1` 的 tag → `@未定位-2` 永远判不到 done（天天重采）；
  · `--force-layers @未定位-2` 因 add 只加 `not in have` 而提不到队首。

本文件锁五件事：
  ① `base_layer_id` 只剥我们自己造的后缀，真实层名原样返回；
  ② 两个变体合并成一层，优先留 **Release 已有 tag** 的那条，其次序号最小；
  ③ 被合并的另一条不消失：`merged_variants` + `alt_urls` 留痕；
  ④ 已采判定按 base id：变体挂在 Releases 的旧名字下也能判掉；
  ⑤ `full_plan.resolve_forced`：`@变体` 名单按 base 解析，命中队列的**提到队首**，找不到的不静默。
"""
from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import worker_core as W  # noqa: E402
import full_plan as FP   # noqa: E402

BASE = "_services_Address_Points_AddressPoint_Native_FeatureServer_0"


def _row(lid, url="u1"):
    return {"id": lid, "state": "未定位", "title": "t", "url": url, "expect": 100}


class BaseId(unittest.TestCase):
    def test_strips_only_our_suffix(self):
        self.assertEqual(W.base_layer_id(BASE + "@未定位-1"), BASE)
        self.assertEqual(W.base_layer_id(BASE + "@NC-12"), BASE)
        self.assertEqual(W.base_layer_id(BASE), BASE)
        self.assertEqual(W.base_layer_id(""), "")
        self.assertEqual(W.base_layer_id("a@b"), "a@b")          # 没有 -<数字> → 不是我们的后缀

    def test_variant_regex(self):
        self.assertTrue(W.VAR_SUFFIX_RE.match("x@未定位-2"))
        self.assertFalse(W.VAR_SUFFIX_RE.match("x@未定位"))
        self.assertFalse(W.VAR_SUFFIX_RE.match("x"))


class MergeVariants(unittest.TestCase):
    def test_two_variants_become_one(self):
        rows = [_row(BASE + "@未定位-1", "https://baltegis/0"), _row(BASE + "@未定位-2", "https://egis/0")]
        out = W.merge_layer_variants(rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["id"], BASE + "@未定位-1")       # 无 tag 证据 → 序号最小
        self.assertEqual(out[0]["merged_variants"], [BASE + "@未定位-2"])
        self.assertIn("https://egis/0", out[0]["alt_urls"])      # 另一条 URL 不丢

    def test_prefers_variant_with_release_tag(self):
        rows = [_row(BASE + "@未定位-1", "https://baltegis/0"), _row(BASE + "@未定位-2", "https://egis/0")]
        out = W.merge_layer_variants(rows, prefer_ids={BASE + "@未定位-2"})
        self.assertEqual([r["id"] for r in out], [BASE + "@未定位-2"])
        self.assertEqual(out[0]["url"], "https://egis/0")
        self.assertEqual(out[0]["merged_variants"], [BASE + "@未定位-1"])

    def test_unrelated_layers_untouched(self):
        rows = [_row("a"), _row("b@ND-1"), _row("b@ND-2"), _row("c")]
        out = W.merge_layer_variants(rows)
        self.assertEqual([r["id"] for r in out], ["a", "b@ND-1", "c"])

    def test_same_layer_only_counts_once(self):
        rows = [_row(BASE + "@未定位-1"), _row(BASE + "@未定位-2")]
        self.assertEqual(len(W.merge_layer_variants(rows)), 1)


class DoneByBaseId(unittest.TestCase):
    def test_variant_tag_marks_layer_done(self):
        rows = [_row(BASE + "@未定位-1"), _row("other")]
        keep, skipped = W.split_done(rows, {BASE + "@未定位-2"})   # tag 记在被合并掉的变体名下
        self.assertEqual(skipped, 1)
        self.assertEqual([r["id"] for r in keep], ["other"])

    def test_unrelated_untouched(self):
        rows = [_row("a"), _row("b")]
        keep, skipped = W.split_done(rows, {"a"})
        self.assertEqual(len(keep), 1)
        self.assertEqual(skipped, 1)

    def test_empty_done_is_noop(self):
        rows = [_row("a")]
        self.assertEqual(W.split_done(rows, set()), (rows, 0))


class ForceToFront(unittest.TestCase):
    def test_variant_force_is_resolved_and_lifted(self):
        q = [_row("first"), _row(BASE + "@未定位-1")]
        univ = q + [_row(BASE + "@未定位-2", "https://egis/0")]
        front, rest, unknown, merged = FP.resolve_forced([BASE + "@未定位-2"], univ, q)
        self.assertEqual([r["id"] for r in front], [BASE + "@未定位-2"])   # 命中 univ → 用 univ 那条
        self.assertEqual([r["id"] for r in rest], ["first"])               # 队列里的同 base 变体被摘掉
        self.assertEqual(unknown, [])
        self.assertEqual(merged, [(BASE + "@未定位-2", BASE + "@未定位-2")] and [])

    def test_force_by_base_name_when_only_variant_exists(self):
        q = [_row("first")]
        univ = [_row(BASE + "@未定位-1")]
        front, rest, unknown, merged = FP.resolve_forced([BASE], univ, q)
        self.assertEqual([r["id"] for r in front], [BASE + "@未定位-1"])
        self.assertEqual(merged, [(BASE, BASE + "@未定位-1")])
        self.assertEqual(unknown, [])

    def test_forced_layer_already_in_queue_goes_to_front(self):
        q = [_row("first"), _row("second")]
        front, rest, unknown, _ = FP.resolve_forced(["second"], q, q)
        self.assertEqual([r["id"] for r in front], ["second"])
        self.assertEqual([r["id"] for r in rest], ["first"])

    def test_unknown_is_reported_not_swallowed(self):
        q = [_row("a")]
        front, rest, unknown, _ = FP.resolve_forced(["nope"], q, q)
        self.assertEqual(front, [])
        self.assertEqual(unknown, ["nope"])

    def test_queue_is_not_double_counted(self):
        q = [_row("a"), _row("b")]
        front, rest, _, _ = FP.resolve_forced(["a"], q, q)
        self.assertEqual(len(front) + len(rest), 2)     # 旧版会变成 3（add + 全队列）


if __name__ == "__main__":
    unittest.main(verbosity=2)
