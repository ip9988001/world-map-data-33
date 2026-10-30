#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ledger_rebuild.judge() 契约测试：四态判定 + 不猜原则。

跑法：python3 -m pytest collect/tests/test_ledger_rebuild.py -q
      （无 pytest 时：python3 collect/tests/test_ledger_rebuild.py）
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ledger_rebuild import (judge, scope_layers, extras_not_in_plan,   # noqa: E402
                            plan_shard_index, annotate_shards)


def rel(tag="collect-step04-L", units=(0,), ckpt=True, size=1000):
    assets = [{"id": 1, "name": tag[len("collect-step04-"):] + "-u%05d.tar.gz" % u,
               "size": size, "created_at": "2026-10-30T01:00:00Z"} for u in units]
    if ckpt:
        assets.append({"id": 9, "name": tag[len("collect-step04-"):] + "-checkpoint.json",
                       "size": 500, "created_at": "2026-10-30T01:00:00Z"})
    return {"tag": tag, "created_at": "2026-10-30T01:00:00Z", "assets": assets}


def ck(tag="collect-step04-L", unit_rows=None, seen=None, uploaded=None, done=None,
       errors=None, ver=2):
    unit_rows = unit_rows if unit_rows is not None else {0: 1000}
    seen = seen if seen is not None else dict(unit_rows)
    uploaded = uploaded if uploaded is not None else {k: True for k in unit_rows}
    done = done if done is not None else list(unit_rows)
    d = {"ver": ver, "tag": tag, "unit_rows": unit_rows, "unit_uploaded": uploaded,
         "done_units": done, "unit_files": {k: ["part-%d.ndjson.gz" % i] for i, k in enumerate(unit_rows)},
         "unit_errors": errors or {}}
    if ver >= 2:
        d["unit_rows_seen"] = seen
    return d


def t_ok():
    r = judge("L", 1000, rel(), ck(), "")
    assert r["status"] == "ok", r
    assert r["rows"] == 1000 and r["rows_src"] == "unit_rows_seen"
    assert r["parts_assets"] == 1 and r["bytes"] == 1000 + 500


def t_missing_release():
    r = judge("L", 5000, None, None, "")
    assert r["status"] == "failed" and "无 Release 资产" in r["reason"], r


def t_empty_layer():
    """声明 0 行 + 无资产 = 上游空层，不是失败（不猜成 failed）。"""
    r = judge("L", 0, None, None, "")
    assert r["status"] == "empty", r


def t_no_checkpoint():
    """有 unit 包但没 checkpoint → 完成度不可证，判 failed（绝不按包数推行数）。"""
    r = judge("L", 1000, rel(ckpt=False), None, "")
    assert r["status"] == "failed" and "无 checkpoint" in r["reason"], r


def t_missing_asset():
    """checkpoint 说单元传了，但 Release 里没这个包 → failed。"""
    c = ck(unit_rows={0: 1000, 1: 1000})
    r = judge("L", 2000, rel(units=(0,)), c, "")
    assert r["status"] == "failed" and "无 -u00001.tar.gz" in r["reason"], r


def t_extra_asset():
    """Release 有单元包但 checkpoint 没记录 → 旧切分遗留：**warn 不算 failed**（完成度由 checkpoint 举证）。

    历史口径这里是 failed；2026-10-30 改为 warn：重切片（plan_hash 变）后旧包编号
    与新单元对不上是预期行为，若继续判 failed，一次正常重切片就把好层钉成永久 failed。
    该异常仍会在逐层表 `stale_parts` + 备注里看得见，不是静默。
    """
    r = judge("L", 1000, rel(units=(0, 1)), ck(), "")
    assert r["status"] == "ok", r
    assert r.get("stale_parts") == [1], r
    assert any("旧切分遗留" in w for w in r["warn"]), r


def t_unit_errors():
    r = judge("L", 1000, rel(), ck(errors={0: "short:900/1000"}), "")
    assert r["status"] == "failed" and "残留错误" in r["reason"], r


def t_not_uploaded():
    r = judge("L", 1000, rel(), ck(uploaded={0: False}, done=[]), "")
    assert r["status"] == "failed" and "未上传" in r["reason"], r


def t_gap_1pct():
    """缺口 > 1% → partial，且必须能被单列出来。"""
    r = judge("L", 100000, rel(), ck(unit_rows={0: 100000}, seen={0: 98000}), "")
    assert r["status"] == "partial" and r["gap_pct"] > 1.0, r


def t_gap_under_1pct():
    r = judge("L", 100000, rel(), ck(unit_rows={0: 100000}, seen={0: 99500}), "")
    assert r["status"] == "ok" and r["gap_pct"] < 1.0, r


def t_plan_below_declared():
    """实采 == 本层计划行，但计划行远小于清单声明 → partial 并点明「口径差，需重采」。"""
    r = judge("L", 97928946, rel(), ck(unit_rows={0: 27979700}, seen={0: 27979700}), "")
    assert r["status"] == "partial" and "口径差" in r["reason"], r


def t_legacy_checkpoint():
    """老 checkpoint 无 unit_rows_seen → 退回 unit_rows 并标注，不静默。"""
    r = judge("L", 1000, rel(), ck(ver=1), "")
    assert r["rows_src"] == "unit_rows" and any("unit_rows_seen" in w for w in r["warn"]), r


def t_tag_mismatch():
    r = judge("L", 1000, rel(), ck(tag="collect-step04-OTHER"), "")
    assert r["status"] == "failed" and "不符" in r["reason"], r


def t_zero_rows():
    r = judge("L", 1000, rel(), ck(unit_rows={0: 1000}, seen={0: 0}), "")
    assert r["status"] == "failed" and "实采 0 行" in r["reason"], r


def main() -> int:
    names = [(k, v) for k, v in sorted(globals().items())
             if k.startswith("t_") and callable(v)]
    bad = 0
    for n, f in names:
        try:
            f()
            print("✅ %s" % n)
        except AssertionError as e:
            bad += 1
            print("❌ %s → %s" % (n, e))
    print("\n%d/%d 通过" % (len(names) - bad, len(names)))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())


# ---------------------------------------------------------------- 无计划文件的兜底路径
def test_scope_without_plan_strips_tag_prefix():
    """无计划文件时必须用「去前缀的层 id」——否则 releases.get(prefix+layer) 恒 None，
    真资产层会被整片误标成 empty（2026-10-30 实测 238 层踩过）。"""
    rels = {"collect-step04-a": {"tag": "collect-step04-a", "assets": []},
            "collect-step04-b": {"tag": "collect-step04-b", "assets": []}}
    got = scope_layers([], rels, "collect-step04-")
    assert got == ["a", "b"], got
    assert all(("collect-step04-" + lid) in rels for lid in got)


def test_scope_with_plan_keeps_plan_order():
    rels = {"collect-step04-a": {}, "collect-step04-z": {}}
    assert scope_layers(["z", "a"], rels, "collect-step04-") == ["z", "a"]


def test_extras_empty_when_no_plan():
    rels = {"collect-step04-a": {}, "collect-step04-b": {}}
    assert extras_not_in_plan([], rels, "collect-step04-") == []


def test_extras_lists_out_of_plan_tags():
    rels = {"collect-step04-a": {}, "collect-step04-old": {}}
    assert extras_not_in_plan(["a"], rels, "collect-step04-") == ["collect-step04-old"]


# ---------------------------------------------------------------- cancelled 片留痕
import json as _json          # noqa: E402
import tempfile as _tmp       # noqa: E402


def test_plan_shard_index_maps_layer_to_shard():
    plan = {"shards": [{"shard": 0, "layers": ["a", "b"]}, {"shard": 7, "layers": ["c"]}]}
    f = _tmp.NamedTemporaryFile("w", suffix=".json", delete=False)
    _json.dump(plan, f); f.close()
    assert plan_shard_index(f.name) == {"a": 0, "b": 0, "c": 7}
    assert plan_shard_index("") == {} and plan_shard_index("/nonexist.json") == {}


def test_annotate_shards_marks_every_cancelled_layer():
    """cancelled 片里的层必须全部有痕迹：ok（已落盘）/ 半截 / 一个字节都没有，三档分明。"""
    recs = [{"layer": "done_ok", "status": "ok", "tag": "t", "declared": 100, "rows": 100},
            {"layer": "half", "status": "failed", "tag": "t", "declared": 100, "rows": 40,
             "parts_assets": 2, "units_done": 2, "units": 4},
            {"layer": "never", "status": "failed", "tag": None, "declared": 100, "rows": None},
            {"layer": "other", "status": "ok", "tag": "t", "declared": 10, "rows": 10}]
    shard_of = {"done_ok": 1, "half": 1, "never": 1, "other": 0}
    sjobs = {0: {"job_id": 90, "conclusion": "success"},
             1: {"job_id": 91, "conclusion": "cancelled"}}
    cancelled, block = annotate_shards(recs, shard_of, sjobs)
    assert cancelled == [1], cancelled
    assert len(block) == 1 and block[0]["layers_n"] == 3, block
    assert block[0]["ok"] == 1 and block[0]["failed"] == 2
    assert block[0]["rows"] == 140 and block[0]["declared"] == 300
    notes = {l["layer"]: l["note"] for l in block[0]["layers"]}
    assert "已落盘" in notes["done_ok"], notes
    assert "需续跑" in notes["half"], notes
    assert "从未跑成" in notes["never"], notes
    # 不在 cancelled 片的层不许被贴 cancelled 标
    assert not recs[3].get("shard_cancelled") and recs[3]["shard"] == 0
    assert recs[0]["shard_cancelled"] is True


# ---------------------------------------------------------------- unittest 收口
# 这个文件是「函数 + 自己的 runner」写法，`python3 -m unittest discover` 收不到函数，
# 于是 ci-smoke 的单测那一步其实从没跑过这些契约（2026-10-30 发现）。
# 这里把模块级 test_* 挂到一个 TestCase 上，让 discover 也能跑 —— 不改测试写法。
import unittest as _unittest  # noqa: E402


class LedgerRebuildContract(_unittest.TestCase):
    pass


for _name, _fn in list(globals().items()):
    if callable(_fn) and (_name.startswith("test_") or _name.startswith("t_")):
        _alias = _name if _name.startswith("test_") else "test_" + _name
        setattr(LedgerRebuildContract, _alias, staticmethod(_fn))
