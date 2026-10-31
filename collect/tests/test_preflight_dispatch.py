# -*- coding: utf-8 -*-
"""派单前门禁的契约 —— 「跑之前先核验」必须是机械判定，不是口号。

锁六类行为（全部离线，不联网、不派单、不改账本）：
  A1/A1b  同 concurrency group 有 pending → FAIL；上游阶段在跑 → WARN（它全绿会自动派本阶段）
  B3      --ref 缺少已批准修复（ledger_merge / ckpt_guard 等）→ FAIL，并列出缺哪几项
  B4/B5   接续策略：04b/05b 只许接 05b/07b 且单跳；07b/10b 必须 stop；10b 未授权 → FAIL
  C6/C8   账本现值可读；merge 写入保护缺失 → FAIL
  D9/D10/D11  force 层与在跑 run 撞车 → FAIL；已采重叠要说清是补采；无 .bak → WARN + 命令
  E12/E13/E14 0 行层单列；403/超时只 WARN 不判死；Token Required 标 declared_unverifiable
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import preflight_dispatch as P  # noqa: E402


class AQueue(unittest.TestCase):
    def test_pending_same_group_is_fail(self):
        out = P.judge_concurrency("07b", [{"id": 1, "status": "queued"}])
        self.assertEqual([i["status"] for i in out], ["FAIL"])
        self.assertIn("挤掉", out[0]["detail"])

    def test_in_progress_same_group_is_warn_with_wait(self):
        out = P.judge_concurrency("07b", [{"id": 9, "status": "in_progress"}], wait_est_min=42)
        self.assertEqual(out[0]["status"], "WARN")
        self.assertIn("42", out[0]["detail"])
        self.assertIn("9", out[0]["detail"])

    def test_idle_group_passes(self):
        self.assertEqual(P.judge_concurrency("07b", [])[0]["status"], "PASS")

    def test_offline_is_warn_not_pass(self):
        self.assertEqual(P.judge_concurrency("07b", [], offline=True)[0]["status"], "WARN")

    def test_upstream_stage_running_warns_about_auto_dispatch(self):
        active = [{"id": 5, "stage": "05b", "status": "in_progress"}]
        it = P.judge_upstream_stage("07b", active)
        self.assertEqual(it["status"], "WARN")
        self.assertIn("自动派", it["detail"])          # 05b 全绿会派 07b → 手派会撞
        self.assertEqual(P.judge_upstream_stage("04b", active)["status"], "INFO")
        self.assertEqual(P.judge_upstream_stage("07b", [])["status"], "PASS")


class BCode(unittest.TestCase):
    FILES = {"collect/chain_policy.py": 'ALLOWED = ("05b", "07b")\nNEXT = {\n "07b": "",\n}',
             "collect/ledger_merge.py": "def write_run_and_stage(\n\ndef row_regressions(\n",
             "collect/step_full_report.py": "from ledger_merge import write_run_and_stage\n",
             "collect/ckpt_guard.py": "def merge_checkpoints(\n",
             "collect/pilot.py": "def _backup_legacy_ckpt():\n"}

    def _show(self, ref, path):
        return self.FILES.get(path)

    def _blob(self, ref, path):
        return "sha-" + path

    def test_all_fixes_present_and_same_as_main_passes(self):
        items, diffs = P.judge_code_gate("origin/main", "origin/main",
                                         show=self._show, blob=self._blob)
        self.assertEqual([i["status"] for i in items], ["PASS"])
        self.assertEqual(diffs, [])

    def test_missing_fix_is_fail_and_names_file(self):
        files = dict(self.FILES)
        del files["collect/ckpt_guard.py"]
        files["collect/pilot.py"] = "def other():\n"          # 缺 _backup_legacy_ckpt
        items, _ = P.judge_code_gate("feat/x", "origin/main",
                                     show=lambda r, p: files.get(p), blob=self._blob)
        self.assertEqual(items[0]["status"], "FAIL")
        self.assertIn("ckpt_guard.py", items[0]["detail"])
        miss = {m["file"] for m in items[0]["missing"]}
        self.assertEqual(miss, {"collect/ckpt_guard.py", "collect/pilot.py"})

    def test_ref_differs_from_main_is_fail_listing_files(self):
        items, diffs = P.judge_code_gate(
            "feat/x", "origin/main", show=self._show,
            blob=lambda r, p: ("other" if r == "feat/x" else "sha-") + p)
        st = {i["id"]: i["status"] for i in items}
        self.assertEqual(st["B3"], "FAIL")
        self.assertIn("collect/pilot.py", [d["file"] for d in diffs])

    def test_chain_rules(self):
        self.assertEqual(P.judge_chain("04b", "[chain] stage=04b next=05b child_chain=0 decide=dispatch")["status"], "PASS")
        self.assertEqual(P.judge_chain("05b", "[chain] stage=05b next=07b child_chain=0 decide=dispatch")["status"], "PASS")
        self.assertEqual(P.judge_chain("07b", "[chain] stage=07b next=-   child_chain=0 decide=stop")["status"], "PASS")
        bad = P.judge_chain("07b", "[chain] stage=07b next=10b child_chain=0 decide=dispatch")
        self.assertEqual(bad["status"], "FAIL")
        self.assertEqual(P.judge_chain("04b", "boom", chain_rc=1)["status"], "FAIL")

    def test_authorization(self):
        self.assertEqual(P.judge_authorization("04b")["status"], "PASS")
        self.assertEqual(P.judge_authorization("10b")["status"], "FAIL")
        self.assertEqual(P.judge_authorization("10b", authorize_heavy=True)["status"], "WARN")
        self.assertEqual(P.judge_authorization("08")["status"], "FAIL")
        self.assertEqual(P.judge_authorization("08", authorize_manual=("08",))["status"], "WARN")
        self.assertEqual(P.judge_authorization("99")["status"], "FAIL")


class CLedger(unittest.TestCase):
    def test_baseline_reads_counts(self):
        d = tempfile.mkdtemp()
        p = os.path.join(d, "04b_ledger.json")
        json.dump({"schema": "x", "layers_n": 3, "records": [
            {"layer": "a", "status": "ok", "rows": 10, "declared": 10},
            {"layer": "b", "status": "partial", "rows": 5, "declared": 10},
            {"layer": "c", "status": "failed", "rows": 0, "declared": 10}],
            "revisions": [{}, {}]}, open(p, "w"))
        it = P.judge_baseline("04b", (p, "", ""))
        self.assertEqual(it["status"], "WARN")          # 缺 rebuilt / last_run
        led = it["ledgers"]["stage_ledger"]
        self.assertEqual((led["layers_n"], led["ok"], led["partial"], led["failed"]), (3, 1, 1, 1))
        self.assertEqual(led["rows"], 15)
        self.assertEqual(led["revisions"], 2)

    def test_merge_guard_fail_then_pass(self):
        empty = lambda ref, path: ""                    # noqa: E731
        self.assertEqual(P.judge_merge_guard("main", show=empty)["status"], "FAIL")
        ok_files = {"collect/ledger_merge.py":
                    "def write_run_and_stage(\ndef stage_overwrite_allowed(",
                    "collect/step_full_report.py":
                    "from ledger_merge import write_run_and_stage\n--row-shrink-evidence",
                    "collect/ckpt_guard.py": "def merge_checkpoints(",
                    "collect/pilot.py": "_merge_legacy_ckpt"}
        it = P.judge_merge_guard("ref", show=lambda r, p: ok_files.get(p, ""))
        self.assertEqual(it["status"], "PASS")


class DOverlap(unittest.TestCase):
    def test_force_layer_being_written_is_fail(self):
        it = P.judge_overlap(["L1"], {"411": {"stage": "04b", "layers": ["L1", "L2"]}})
        self.assertEqual(it["status"], "FAIL")
        self.assertIn("411", it["detail"])

    def test_no_force_layers_is_info(self):
        self.assertEqual(P.judge_overlap([], {})["status"], "INFO")

    def test_unknown_targets_is_warn_not_pass(self):
        it = P.judge_overlap(["L9"], {"411": {"stage": "04b", "layers": []}})
        self.assertEqual(it["status"], "WARN")

    def test_done_overlap_explains_backfill(self):
        warn = P.judge_done_overlap("04b", ["L1", "L2"], {"L1"}, force_layers=["L1"])
        self.assertEqual(warn["status"], "WARN")
        self.assertEqual(warn["overlap_n"], 1)
        ok = P.judge_done_overlap("04b", ["L3"], {"L1"}, force_layers=["L1"])
        self.assertEqual(ok["status"], "PASS")
        self.assertIn("补采", ok["detail"])
        self.assertEqual(P.judge_done_overlap("04b", None, {"L1"})["status"], "WARN")

    def test_checkpoint_without_bak_warns_with_command(self):
        assets = {"L1": ["L1-checkpoint.json", "L1-u00000.tar.gz"]}
        it = P.judge_ckpt_backup("collect-step04-", ["L1"], assets)
        self.assertEqual(it["status"], "WARN")
        self.assertIn("gh release upload", it["commands"][0])
        ok = P.judge_ckpt_backup("collect-step04-", ["L1"],
                                 {"L1": ["L1-checkpoint.json", "L1-checkpoint.bak-1.json"]})
        self.assertEqual(ok["status"], "PASS")


class EUpstream(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(P.classify_probe({"http": 200, "count": 5}), "ok")
        self.assertEqual(P.classify_probe({"http": 200, "count": 0}), "empty")
        self.assertEqual(P.classify_probe({"http": 200, "count": None,
                                           "err": {"message": "Token Required"}}), "token")
        self.assertEqual(P.classify_probe({"http": 200, "count": None, "err": "",
                                           "meta_token": True}), "service_token")
        self.assertEqual(P.classify_probe({"http": 403, "err": "HTTP 403"}), "forbidden")
        self.assertEqual(P.classify_probe({"http": 0, "err": "URLError: <urlopen error timed out>"}), "timeout")

    def test_judge_upstream_lists_empty_and_keeps_403_as_warn(self):
        res = {"a": {"http": 200, "count": 0}, "b": {"http": 200, "count": 7},
               "c": {"http": 403, "err": "HTTP 403"}, "d": {"http": 200, "count": None,
                                                            "err": "Token Required", "meta_token": True}}
        items = P.judge_upstream(list(res), res, min_samples=1)
        by = {i["id"]: i for i in items}
        self.assertEqual(by["E12"]["status"], "WARN")
        self.assertEqual(by["E12"]["layers"], ["a"])                 # 0 行层单列
        self.assertEqual(by["E13"]["status"], "WARN")                # 403 不判死
        self.assertEqual(by["E13"]["layers"][0]["class"], "forbidden")
        self.assertEqual(by["E14"]["service_token"], ["d"])          # 服务级 token 单列
        self.assertEqual(by["E14"]["status"], "WARN")

    def test_offline_and_no_samples_are_warn(self):
        items = P.judge_upstream([], {}, offline=True)
        self.assertTrue(all(i["status"] == "WARN" for i in items))


class ApprovedVersion(unittest.TestCase):
    """B3b：已批准版本白名单 —— main 前进了不能静默通过，也不能被当成「版本不一致」误判。"""

    def test_new_main_after_a478570_is_whitelisted(self):
        # 2026-10-31 合并的两笔：a478570 合入（f68c002）、rows 回退护栏（3f3c9b9）
        for sha, why in (("f68c002", "chore/ledger-merge-fix"), ("3f3c9b9", "regressions")):
            self.assertIn(sha, P.APPROVED_MAIN)
            self.assertTrue(P.APPROVED_MAIN[sha].strip())
        self.assertIn("d5b5db2", P.APPROVED_MAIN)          # 基线版本仍在

    def test_whitelisted_main_passes_and_says_what_was_approved(self):
        it = P.judge_approved_version("3f3c9b9deadbeef", "3f3c9b9deadbeef")
        self.assertEqual(it["status"], "PASS")
        self.assertIn("3f3c9b9", it["detail"])
        self.assertIn("regressions", it["detail"])

    def test_unknown_main_warns_instead_of_failing(self):
        it = P.judge_approved_version("aaaaaaa", "bbbbbbb1234")
        self.assertEqual(it["status"], "WARN")              # 不挡派单，但必须点名
        self.assertIn("bbbbbbb", it["detail"])
        self.assertIn("APPROVED_MAIN", it["detail"])

    def test_unresolvable_main_is_fail(self):
        self.assertEqual(P.judge_approved_version("aaaaaaa", "")["status"], "FAIL")


LEDGER_SAMPLE = """# 台账
| 编号 | 发现日期 | 类别 | 症状 | 根因 | 影响 | 修法 | 验证方式 | 关联提交 | 复发次数 |
|---|---|---|---|---|---|---|---|---|---|
| W33-011 | 2026-10-30 | 账本与口径 | 阶段账本被单 run 冲成 31 层 | 共用一个文件 | 账本错 | 单 run 单独落文件 | test_ledger_merge | 35904fb | 2 |
| W33-014 | 2026-10-30 | 账本与口径 | rc!=0 一律 failed | 只判 0/非 0 | 假红 | rc=2 → unverified 不报红 | 构造 rc=2 | 未修 | 0 |
| W33-021 | 2026-10-30 | 切分与体积 | 按行数切必撞 2GB | 不看字节 | 上传失败 | unit_rows + unit_bytes 双上限 | unit_bytes < 1.5e9 | 566b20b | 1 |
| W33-001 | 2026-10-30 | 并发队列 | 同组只留一个 pending | GitHub 行为 | 白排一轮 | 派前查 pending | gh run list | 无（靠流程规避） | 1 |
"""


class FailureLedger(unittest.TestCase):
    """F16：故障清单 —— 未规避 → WARN；复发 ≥2 → FAIL；豁免写进证据。"""

    def test_parse_rows_and_recurrence(self):
        rows = P.parse_failure_ledger(LEDGER_SAMPLE)
        self.assertEqual([r["id"] for r in rows], ["W33-011", "W33-014", "W33-021", "W33-001"])
        self.assertEqual(rows[0]["recurrence"], 2)
        self.assertTrue(rows[0]["mitigated"])          # 有关联提交
        self.assertFalse(rows[1]["mitigated"])         # 未修
        self.assertEqual(rows[2]["category"], "切分与体积")

    def test_no_commit_means_unmitigated_even_with_prose(self):
        rows = P.parse_failure_ledger(LEDGER_SAMPLE)
        self.assertFalse(rows[3]["mitigated"])        # 关联提交写「无（靠流程规避）」
        it, _ = P.judge_failure_ledger(LEDGER_SAMPLE, categories=["并发队列"])
        self.assertEqual(it["status"], "WARN")
        self.assertIn("W33-001", it["detail"])

    def test_header_and_separator_are_ignored(self):
        rows = P.parse_failure_ledger("| 编号 | 日期 |\n|---|---|\n| xx | y |\n")
        self.assertEqual(rows, [])

    def test_recurrence_ge_2_is_fail(self):
        it, hits = P.judge_failure_ledger(LEDGER_SAMPLE, categories=["账本与口径"])
        self.assertEqual(it["status"], "FAIL")
        self.assertIn("W33-011", it["detail"])
        self.assertTrue(any(h["id"] == "W33-011" for h in hits))

    def test_unmitigated_is_warn_and_prints_mitigation(self):
        it, _ = P.judge_failure_ledger(LEDGER_SAMPLE, categories=["账本与口径"],
                                       waive=["W33-011"])
        self.assertEqual(it["status"], "WARN")
        self.assertIn("W33-014", it["detail"])
        self.assertIn("unverified", it["detail"])      # 规避动作要打出来

    def test_waive_downgrades_the_fatal_one(self):
        it, _ = P.judge_failure_ledger(LEDGER_SAMPLE, categories=["账本与口径"],
                                       waive=["w33-011", "W33-014"])
        self.assertNotEqual(it["status"], "FAIL")
        self.assertTrue(any(h["waived"] for h in it["ledger_hits"]))

    def test_fixed_single_recurrence_is_pass_with_hits_listed(self):
        it, hits = P.judge_failure_ledger(LEDGER_SAMPLE, categories=["切分与体积"])
        self.assertEqual(it["status"], "PASS")
        self.assertEqual([h["id"] for h in hits], ["W33-021"])

    def test_no_category_match_passes(self):
        it, hits = P.judge_failure_ledger(LEDGER_SAMPLE, categories=["缓存与签名"])
        self.assertEqual(it["status"], "PASS")
        self.assertEqual(hits, [])

    def test_unknown_category_warns_instead_of_silently_passing(self):
        it, _ = P.judge_failure_ledger(LEDGER_SAMPLE, categories=["账本口径"])
        self.assertEqual(it["status"], "WARN")
        self.assertIn("类别写错", it["detail"])

    def test_no_category_declared_warns(self):
        it, hits = P.judge_failure_ledger(LEDGER_SAMPLE)
        self.assertEqual(it["status"], "WARN")
        self.assertIn("故障清单已查", it["detail"])
        self.assertEqual(hits, [])

    def test_missing_ledger_warns(self):
        it, _ = P.judge_failure_ledger("", categories=["账本与口径"])
        self.assertEqual(it["status"], "WARN")
        self.assertIn("WORKFLOW-FAILURE-LEDGER", it["detail"])

    def test_broken_table_is_fail(self):
        it, _ = P.judge_failure_ledger("no table here", categories=["账本与口径"])
        self.assertEqual(it["status"], "FAIL")

    def test_categories_derived_from_changed_paths(self):
        cats = P.categories_of_paths(["collect/pilot.py", "docs/x.md"])
        self.assertIn("checkpoint与断点", cats)
        self.assertIn("切分与体积", cats)
        self.assertNotIn("账本与口径", cats)
        cats2 = P.categories_of_paths(["collect/ledger_merge.py"])
        self.assertEqual(cats2, {"账本与口径"})


class Verdict(unittest.TestCase):
    def test_verdict_aggregation(self):
        ok = [{"status": "PASS"}, {"status": "INFO"}]
        self.assertEqual(P.verdict_of(ok), "PASS")
        self.assertEqual(P.verdict_of(ok + [{"status": "WARN"}]), "PASS_WITH_WARNINGS")
        self.assertEqual(P.verdict_of(ok + [{"status": "WARN"}, {"status": "FAIL"}]), "FAIL")

    def test_stage_of_run_from_artifacts(self):
        self.assertEqual(P.stage_of_run(1, {"04b": {"run_id": "1"}}), "04b")
        self.assertEqual(P.stage_of_run(2, {}, ["led-05b-7"]), "05b")
        self.assertEqual(P.stage_of_run(3, {}, ["plan-07b"]), "07b")
        self.assertEqual(P.stage_of_run(4, {}, ["plan-xx"]), "")


if __name__ == "__main__":
    unittest.main()
