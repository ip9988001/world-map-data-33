# -*- coding: utf-8 -*-
"""行数护栏契约 —— force 重跑不许把「完成度证据」变小。

守的事故（2026-10-30 22:23Z，run 41126178216）：
  NAD view 层的检查点被 force 补采整份覆盖成「1 unit / 0 行」，68 个 `u000NN.tar.gz`
  一个没少，但账本从 partial(39,875,268) 掉成 failed(0) —— 数据在、判据没了。

本文件锁四件事：
  ① 覆盖前先备份（本地 bak，只留 3 代）；
  ② 合并按**包名**去重：旧包还在→行数保留并标 legacy_split；同名被覆盖→取大者不双算；
  ③ 切分不兼容时 units_new[] / units_legacy[] 两边都记，rows 求和；
  ④ 行数变小必须有 `regression_reason` + 证据路径，否则 RowsRegression（拒绝写入）。
"""
import json
import os
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import ckpt_guard as G          # noqa: E402
import ledger_merge as LM      # noqa: E402

LAYER = "s_Points_from_National_Address_Database_view_FeatureServer_0"


def ck(units, layer=LAYER, plan_hash="ph1", uploaded=True, seeded=True, unit_ns=""):
    """造一个检查点：units = {idx: rows}。`unit_ns` 模拟切分不兼容时的代际前缀。"""
    return {"ver": 2, "url": "http://x/0", "plan_hash": plan_hash, "unit_ns": unit_ns,
            "unit_rows": {str(i): n for i, n in units.items()},
            "unit_rows_seen": {str(i): n for i, n in units.items()},
            "unit_files": {str(i): ["part-u%05d-000.ndjson.gz" % i] for i in units},
            "unit_package": {str(i): "%s-%su%05d.tar.gz" % (layer, unit_ns, i) for i in units},
            "unit_uploaded": {str(i): uploaded for i in units},
            "done_units": sorted(units) if seeded else []}


def assets_of(names, size=1000):
    return {n: {"size": size, "state": "uploaded"} for n in names}


class Basics(unittest.TestCase):
    def test_rows_of_prefers_seen(self):
        c = {"unit_rows": {"0": 5}, "unit_rows_seen": {"0": 9, "1": 1}}
        self.assertEqual(G.unit_rows_map(c), {"0": 9, "1": 1})
        self.assertEqual(G.rows_of(c), 10)

    def test_pkg_name_from_files_then_index(self):
        c = {"unit_files": {"12": ["part-u00012-003.ndjson.gz"]}}
        self.assertEqual(G.pkg_name(LAYER, "12", c), "%s-u00012.tar.gz" % LAYER)
        self.assertEqual(G.pkg_name(LAYER, 7, {}), "%s-u00007.tar.gz" % LAYER)

    def test_pkg_name_records_real_asset_and_namespace(self):
        c = {"unit_package": {"3": "%s-rdeadbeef-u00003.tar.gz" % LAYER},
             "unit_files": {"3": ["part-u00003-000.ndjson.gz"]}}
        self.assertEqual(G.pkg_name(LAYER, 3, c), "%s-rdeadbeef-u00003.tar.gz" % LAYER)
        ns = {"unit_ns": "rdeadbeef-", "unit_files": {"3": ["part-u00003-000.ndjson.gz"]}}
        self.assertEqual(G.pkg_name(LAYER, 3, ns), "%s-rdeadbeef-u00003.tar.gz" % LAYER)
        self.assertEqual(G.pkg_name(LAYER, 3, {"unit_ns": "rabcd1234-"}), "%s-rabcd1234-u00003.tar.gz" % LAYER)

    def test_package_downloadable_three_states(self):
        idx = assets_of(["a.tar.gz"]) | {"b.tar.gz": {"size": 0, "state": "uploaded"},
                                         "c.tar.gz": {"size": 5, "state": "new"}}
        self.assertTrue(G.package_downloadable(idx, "a.tar.gz"))
        self.assertFalse(G.package_downloadable(idx, "b.tar.gz"))
        self.assertFalse(G.package_downloadable(idx, "c.tar.gz"))
        self.assertFalse(G.package_downloadable(idx, "zzz.tar.gz"))
        self.assertIsNone(G.package_downloadable(None, "a.tar.gz"))   # 查不到 ≠ 不在


class Backup(unittest.TestCase):
    def test_local_backup_keeps_three_generations(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "_checkpoint.json")
        json.dump({"ver": 2}, open(p, "w"))
        made = []
        for rid in ("r1", "r2", "r3", "r4"):
            made.append(G.backup_local(p, rid, keep=3))
            time.sleep(0.01)
        self.assertTrue(all(made))
        baks = sorted(f for f in os.listdir(d) if ".bak-" in f)
        self.assertEqual(len(baks), 3, baks)                 # 只留 3 代
        self.assertNotIn(os.path.basename(made[0]), baks)    # 最老的被清掉
        self.assertEqual(json.load(open(made[-1])), {"ver": 2})

    def _baks(self, d):
        return sorted((f for f in os.listdir(d) if ".bak-" in f), key=G.bak_sort_key)

    def test_local_backup_keeps_three_generations_across_gap(self):
        """r3 缺失的 r1/r2/r4 序列：删的必须是数值最小的 r1，不是“随便一个”。

        旧实现按 mtime 排（copy2 继承源 mtime → 全部相等）+ 字符串兜底，
        在 r10 出现时更错：字符串序 r1 < r10 < r2 < r4，会把 r10 当最老删掉。
        """
        d = tempfile.mkdtemp()
        p = os.path.join(d, "_checkpoint.json")
        json.dump({"ver": 2}, open(p, "w"))
        for rid in ("r1", "r2", "r4"):
            self.assertTrue(G.backup_local(p, rid, keep=3))
        self.assertEqual(self._baks(d), ["_checkpoint.bak-r1.json",
                                         "_checkpoint.bak-r2.json",
                                         "_checkpoint.bak-r4.json"])
        self.assertTrue(G.backup_local(p, "r10", keep=3))
        self.assertEqual(self._baks(d), ["_checkpoint.bak-r2.json",
                                         "_checkpoint.bak-r4.json",
                                         "_checkpoint.bak-r10.json"])

    def test_local_backup_survives_identical_mtimes(self):
        """ci-smoke 41167000866 原状：bak 全同 mtime 且创建顺序乱，仍按代删最老的。"""
        d = tempfile.mkdtemp()
        p = os.path.join(d, "_checkpoint.json")
        json.dump({"ver": 2}, open(p, "w"))
        for rid in ("r4", "r1", "r2"):        # 故意乱序建，且 keep 放宽不让它先删
            self.assertTrue(G.backup_local(p, rid, keep=9))
        stamp = time.time() - 3600
        for f in os.listdir(d):                 # 强制所有代 mtime 相同（copy2 就会这样）
            if ".bak-" in f:
                os.utime(os.path.join(d, f), (stamp, stamp))
        self.assertTrue(G.backup_local(p, "r3", keep=3))
        self.assertEqual(self._baks(d), ["_checkpoint.bak-r2.json",
                                         "_checkpoint.bak-r3.json",
                                         "_checkpoint.bak-r4.json"])

    def test_backup_order_is_generation_not_mtime(self):
        """mtime 可以骗人（copy2 继承源文件；跨机器也是乱序），代序只认后缀数字。

        故意把 r1 的 mtime 设成最年轻、r4 设成最老：按 mtime 会删 r4（错），按代必删 r1。
        """
        d = tempfile.mkdtemp()
        p = os.path.join(d, "_checkpoint.json")
        json.dump({"ver": 2}, open(p, "w"))
        for rid in ("r1", "r2", "r3", "r4"):
            self.assertTrue(G.backup_local(p, rid, keep=9))
        base = time.time() - 7200
        for i, rid in enumerate(("r4", "r3", "r2", "r1")):   # r1 最新、r4 最老
            os.utime(os.path.join(d, "_checkpoint.bak-%s.json" % rid), (base + i, base + i))
        self.assertTrue(G.backup_local(p, "r5", keep=3))
        self.assertEqual(self._baks(d), ["_checkpoint.bak-r3.json",
                                         "_checkpoint.bak-r4.json",
                                         "_checkpoint.bak-r5.json"])

    def test_bak_sort_key_is_numeric_not_string(self):
        self.assertGreater(G.bak_sort_key("x.bak-r10.json"), G.bak_sort_key("x.bak-r2.json"))
        self.assertGreater(G.bak_sort_key("L-checkpoint.bak-41167000866.json"),
                           G.bak_sort_key("L-checkpoint.bak-41123309047.json"))
        self.assertLess(G.bak_sort_key("x.bak-r1.json"), G.bak_sort_key("x.bak-r2.json"))

    def test_backup_assets_to_delete_numeric_not_string(self):
        idx = assets_of(["%s-checkpoint.bak-%s.json" % (LAYER, r) for r in ("r2", "r4", "r10")])
        self.assertEqual(G.backup_assets_to_delete(idx, LAYER, "r11", keep=3),
                         ["%s-checkpoint.bak-r2.json" % LAYER])

    def test_backup_missing_file_is_noop(self):
        self.assertEqual(G.backup_local("/nonexistent/_checkpoint.json", "r1"), "")

    def test_backup_assets_to_delete(self):
        idx = assets_of(["%s-checkpoint.bak-%s.json" % (LAYER, r) for r in ("r1", "r2", "r3")])
        self.assertEqual(G.backup_assets_to_delete(idx, LAYER, "r4", keep=3),
                         ["%s-checkpoint.bak-r1.json" % LAYER])
        self.assertEqual(G.backup_assets_to_delete({}, LAYER, "r1", keep=3), [])


class Merge(unittest.TestCase):
    def test_legacy_packages_present_are_kept_and_flagged(self):
        legacy = ck({0: 586401, 1: 500000, 2: 490000}, plan_hash="old")
        # 切分不兼容 → pilot 给新单元包加代际前缀，旧包名不受影响
        new = ck({0: 7, 1: 3, 2: 1, 3: 11, 4: 12, 5: 13}, plan_hash="new", unit_ns="rabcd1234-")
        names = [G.pkg_name(LAYER, i) for i in range(3)]
        merged, rep = G.merge_checkpoints(legacy, new, layer=LAYER, run_id="41126178216",
                                          assets=assets_of(names))
        self.assertEqual(rep["rows_before"], 1576401)
        self.assertEqual(rep["rows_legacy_kept"], 1576401)   # 旧包在 → 行数一行不少
        self.assertGreater(rep["rows_after"], rep["rows_before"])   # 只许涨
        self.assertFalse(rep["split_compatible"])
        self.assertEqual((rep["units_legacy"], rep["units_new"]), (3, 6))
        for u in merged["units_legacy"]:
            self.assertTrue(u["legacy_split"])
            self.assertTrue(u["present"])
            self.assertEqual(u["kept_rows"], u["rows"])
        self.assertEqual(merged["rows_total"], rep["rows_after"])
        self.assertEqual(G.assert_rows_not_shrunk(rep["rows_before"], rep["rows_after"],
                                                  layer=LAYER, run_id="r"), None)

    def test_missing_legacy_packages_trigger_regression_without_evidence(self):
        legacy = ck({0: 586401, 1: 500000}, plan_hash="old")
        new = ck({0: 1}, plan_hash="new", unit_ns="rabcd1234-")   # 新切开出 1 个空单元
        merged, rep = G.merge_checkpoints(legacy, new, layer=LAYER, run_id="r",
                                          assets=assets_of([]))   # Release 里两个旧包都没了
        self.assertEqual(rep["packages_dropped"],
                         ["%s-u00000.tar.gz" % LAYER, "%s-u00001.tar.gz" % LAYER])
        self.assertEqual(rep["rows_after"], 1)
        with self.assertRaises(G.RowsRegression) as cm:
            G.assert_rows_not_shrunk(rep["rows_before"], rep["rows_after"], layer=LAYER, run_id="r")
        self.assertEqual(cm.exception.detail["rows_before"], 1086401)
        self.assertIn("拒绝写入", str(cm.exception))

    def test_regression_allowed_only_with_existing_evidence(self):
        d = tempfile.mkdtemp()
        ev = os.path.join(d, "nad-view-rebuild.json")
        json.dump({"summary": {"rows": 1}}, open(ev, "w"))
        with self.assertRaises(G.RowsRegression):
            G.assert_rows_not_shrunk(1000, 10, layer=LAYER, run_id="r", evidence=ev + ".typo")
        guard = G.assert_rows_not_shrunk(1000, 10, layer=LAYER, run_id="r",
                                        reason="旧包被上游删了", evidence=ev)
        self.assertEqual(guard["rows_before"], 1000)
        self.assertEqual(guard["regression_reason"], "旧包被上游删了")
        self.assertEqual(guard["evidence"], ev)

    def test_same_name_overwrite_dedupes_by_package_name(self):
        """旧 u00000（586k 行）被本轮同名包（7 行）覆盖 → 不双算，取大者。"""
        legacy = ck({0: 586401, 1: 500000}, plan_hash="old")
        new = ck({0: 7, 1: 3}, plan_hash="new")
        # 极端情形：没有代际前缀，本轮用同名包覆盖了旧包
        names = [G.pkg_name(LAYER, 0, legacy), G.pkg_name(LAYER, 1, legacy)]
        new["unit_package"] = {str(i): n for i, n in enumerate(names)}
        merged, rep = G.merge_checkpoints(legacy, new, layer=LAYER, run_id="r",
                                          assets=assets_of(names))
        self.assertEqual(merged["rows_by_package"][names[0]], 586401)
        self.assertEqual(merged["rows_by_package"][names[1]], 500000)
        self.assertEqual(rep["rows_after"], 1086401)          # 不是 1,086,411（不双算）
        self.assertEqual(rep["units_new"], 2)
        collided = [u for u in merged["units_legacy"] if u.get("dedupe") == "same_package_name"]
        self.assertEqual(len(collided), 2)
        self.assertTrue(all(u["counted_as"] == "units_new" for u in collided))

    def test_unknown_assets_never_drops_rows(self):
        legacy = ck({0: 100}, plan_hash="old")
        new = ck({}, plan_hash="new", unit_ns="rabcd1234-")
        merged, rep = G.merge_checkpoints(legacy, new, layer=LAYER, run_id="r", assets=None)
        self.assertEqual(rep["rows_after"], 100)
        self.assertIsNone(rep["legacy_verified_against_release"])
        self.assertFalse(merged["units_legacy"][0]["verified"])

    def test_merge_history_is_appended(self):
        legacy = ck({0: 100}, plan_hash="old")
        new = ck({0: 100}, plan_hash="new")
        new["merge_history"] = [{"rows_before": 0}]
        merged, _ = G.merge_checkpoints(legacy, new, layer=LAYER, run_id="r", assets=None)
        self.assertEqual(len(merged["merge_history"]), 2)
        self.assertEqual(merged["legacy"]["snapshot"]["plan_hash"], "old")


class LedgerGate(unittest.TestCase):
    def test_row_regressions_lists_shrinks(self):
        old = [{"layer": "a", "rows": 100, "status": "partial"},
               {"layer": "b", "rows": 5, "status": "ok"}]
        new = [{"layer": "a", "rows": 1, "status": "failed"},
               {"layer": "b", "rows": 6, "status": "ok"}]
        regs = G.row_regressions(old, new)
        self.assertEqual([r["layer"] for r in regs], ["a"])
        with self.assertRaises(G.RowsRegression):
            G.guard_ledger_rows(old, new, stage="04b", run_id="r")

    def test_guard_passes_with_evidence(self):
        d = tempfile.mkdtemp()
        ev = os.path.join(d, "ev.json")
        json.dump({}, open(ev, "w"))
        old = [{"layer": "a", "rows": 100}]
        new = [{"layer": "a", "rows": 1, "regression_reason": "旧检查点被证伪"}]
        regs = G.guard_ledger_rows(old, new, stage="04b", run_id="r", allow_shrink={"a": ev})
        self.assertEqual(len(regs), 1)
        self.assertEqual(regs[0]["evidence"], ev)

    def test_stage_ledger_write_refused_on_shrink(self):
        """write_run_and_stage：合并后 rows 变小且无实证 → 阶段账本一个字不动，返回 error。

        场景取真实形态：阶段账本 partial(39.8M) → 本轮报 ok 但只测到 5M
        （「更优状态 + 更少行数」= 唯一会把阶段账本 rows 冲小的路径）。"""
        d = tempfile.mkdtemp()
        stage_path = os.path.join(d, "04b_ledger.json")
        json.dump({"stage": "04b", "layers_n": 2, "records": [
            {"layer": "a", "rows": 100, "status": "partial"},
            {"layer": "b", "rows": 50, "status": "ok"}]}, open(stage_path, "w"))
        run = {"layers_n": 2, "records": [{"layer": "a", "rows": 40, "status": "ok"},
                                          {"layer": "b", "rows": 50, "status": "ok"}]}
        res = LM.write_run_and_stage("04b", run, "r1", base_dir=d)
        self.assertFalse(res["stage_written"])
        self.assertEqual(res["reason"], "row_regression_without_evidence")
        self.assertIn("拒绝写入", res["error"])
        self.assertEqual(res["regressions"][0]["rows_before"], 100)
        after = json.load(open(stage_path))
        self.assertEqual(after["records"][0]["rows"], 100)    # 阶段账本未被冲掉
        self.assertTrue(os.path.exists(res["run_path"]))      # 单 run 账本照写（留痕）

    def test_failed_zero_rows_is_not_a_regression(self):
        """本轮「failed + 0 行」= 没测到，不是测出 0 → 不算回退，阶段账本照常合并。

        这正是 NAD view 那次的形态：阶段 partial(39,875,268) + 本轮 failed(0)。
        正确行为是**保留**旧行数并照常写账（而不是拒绝），否则一次 cancel 就让整阶段停更。"""
        d = tempfile.mkdtemp()
        stage_path = os.path.join(d, "04b_ledger.json")
        json.dump({"stage": "04b", "layers_n": 2, "records": [
            {"layer": "a", "rows": 39875268, "status": "partial"},
            {"layer": "b", "rows": 50, "status": "ok"}]}, open(stage_path, "w"))
        run = {"layers_n": 2, "records": [{"layer": "a", "rows": 0, "status": "failed"},
                                          {"layer": "b", "rows": 50, "status": "ok"}]}
        res = LM.write_run_and_stage("04b", run, "r1b", base_dir=d)
        self.assertTrue(res["stage_written"])
        after = json.load(open(stage_path))
        self.assertEqual(after["records"][0]["rows"], 39875268)
        self.assertEqual(after["records"][0]["status"], "partial")   # 不许降级

    def test_stage_ledger_write_allowed_with_evidence(self):
        d = tempfile.mkdtemp()
        stage_path = os.path.join(d, "04b_ledger.json")
        json.dump({"stage": "04b", "layers_n": 2, "records": [
            {"layer": "a", "rows": 100, "status": "partial"},
            {"layer": "b", "rows": 50, "status": "ok"}]}, open(stage_path, "w"))
        ev = os.path.join(d, "ev.json")
        json.dump({}, open(ev, "w"))
        run = {"layers_n": 2, "records": [{"layer": "a", "rows": 40, "status": "ok",
                                           "regression_reason": "旧 100 行里有 60 行是重复 OID"},
                                          {"layer": "b", "rows": 50, "status": "ok"}]}
        res = LM.write_run_and_stage("04b", run, "r2", base_dir=d, allow_shrink={"a": ev})
        self.assertTrue(res["stage_written"])
        self.assertEqual(res["row_regressions_allowed"], 1)
        after = json.load(open(stage_path))
        self.assertEqual(after["records"][0]["rows"], 40)     # 有实证 → 允许变小并留痕
        self.assertEqual([r["kind"] for r in after["revisions"]][-1], "row_regression_allowed")


if __name__ == "__main__":
    unittest.main()
