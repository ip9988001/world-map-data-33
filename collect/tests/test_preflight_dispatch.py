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


class DuplicateDeclared(unittest.TestCase):
    """D12 / W33-035：`@<分区>` 的 Σ declared > 1.5× 同 base 上游 returnCount → 点名 duplicate_declared。"""

    URLS = {"B@X-1": "http://h/1", "B@X-2": "http://h/2"}

    def recs(self, d1, d2, r1=None, r2=None):
        return [{"layer": "B@X-1", "declared": d1, "rows": r1, "status": "missing"},
                {"layer": "B@X-2", "declared": d2, "rows": r2, "status": "ok"}]

    def test_duplicate_is_named_and_suggests_rejudge(self):
        it = P.judge_duplicate_declared(self.recs(6_297_169, 6_297_169, 0, 6_648_000),
                                        url_of=self.URLS, probe=lambda u: {"count": 6_297_169})
        self.assertEqual(it["status"], "WARN")
        self.assertIn("duplicate_declared", it["detail"])
        self.assertIn("--duplicate-partitions", it["detail"])
        self.assertEqual(it["duplicate_declared"][0]["sum_declared"], 12_594_338)
        self.assertEqual(it["duplicate_declared"][0]["upstream_count"], 6_297_169)

    def test_already_rejudged_group_passes(self):
        rs = self.recs(None, 6_297_169, 0, 6_648_000)
        rs[0]["declared_duplicate_partition"] = {"declared_before": 6_297_169, "duplicate_of": "B@X-2"}
        it = P.judge_duplicate_declared(rs, url_of=self.URLS, probe=lambda u: {"count": 6_297_169})
        self.assertEqual(it["status"], "PASS")
        self.assertIn("declared_duplicate_partition", it["detail"])

    def test_reviewed_group_is_not_flagged_but_named(self):
        spec = {"reviewed": [{"base_layer": "B", "verdict": "mirror_hosts_same_data",
                              "decision": "不改判（本次）"}]}
        it = P.judge_duplicate_declared(self.recs(2_139_288, 2_078_539, 2_139_242, 2_139_742),
                                        url_of=self.URLS, probe=lambda u: {"count": 2_139_742},
                                        spec=spec)
        self.assertEqual(it["status"], "PASS")
        self.assertIn("已人复核", it["detail"])
        self.assertEqual(it["duplicate_declared"], [])
        self.assertEqual(it["duplicate_declared_reviewed"][0]["reviewed"]["verdict"],
                         "mirror_hosts_same_data")

    def test_no_partition_layers_is_info(self):
        self.assertEqual(P.judge_duplicate_declared([{"layer": "plain", "declared": 5}],
                                                     url_of={})["status"], "INFO")

    def test_offline_without_any_count_is_warn_not_pass(self):
        """无法判定 ≠ 通过：既没实测、清单里也没有同 base 的 row_count → WARN（与 D10 同约定）。"""
        it = P.judge_duplicate_declared(self.recs(6_297_169, 6_297_169), url_of=self.URLS,
                                        offline=True)
        self.assertEqual(it["status"], "WARN")
        self.assertIn("未能判定", it["detail"])
        self.assertEqual(len(it["duplicate_declared_unknown"]), 1)


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

    def test_e14_suggests_capped_only_after_two_confirmed_rounds(self):
        """硬判据（2026-10-31）：连续两轮服务级 499 → 建议 capped_by_upstream + 打印命令；
        只有一轮 → 不建建议（一次 499 可能只是临时风控）。且**不得自动改账**。"""
        base = {"http": 200, "count": None, "err": "", "meta_token": True}
        res = {"twice": dict(base, confirm_service_token=True),
               "once": dict(base, confirm_service_token=False),
               "noconfirm": dict(base)}
        items = P.judge_upstream(list(res), res, min_samples=1, stage="04b",
                                 urls={k: "https://x/%s/0" % k for k in res})
        e14 = {i["id"]: i for i in items}["E14"]
        self.assertEqual(e14["service_token"], ["twice", "once", "noconfirm"])
        self.assertEqual(e14["capped_candidates"], ["twice"])
        cmds = e14["capped_commands"]
        self.assertEqual(len(cmds), 1)
        self.assertIn("probe_service_token.py --target 'twice=https://x/twice/0'", cmds[0]["probe_cmd"])
        self.assertIn("adjudicate_04b.py --capped twice", cmds[0]["adjudicate_cmd"])
        self.assertIn("--capped-evidence analysis/04b-token-499-evidence-", cmds[0]["adjudicate_cmd"])
        # 两轮未确认的层不得进 capped 候选
        self.assertNotIn("once", e14["capped_candidates"])

    def test_human_summary_prints_capped_commands(self):
        """命令必须真的打到 stdout（否则“打印建议命令”等于没打）。"""
        rep = {"stage": "04b", "ref": "main", "ref_sha": "a" * 40, "verdict": "PASS_WITH_WARNINGS",
               "fail_n": 0, "warn_n": 1, "checks_total": 1,
               "checks": [P.item("E14", "E", "声明可复核率", "WARN", "1 层不可复核",
                                  capped_candidates=["L"],
                                  capped_commands=[{"layer": "L", "probe_cmd": "PROBE",
                                                    "adjudicate_cmd": "ADJ"}])]}
        txt = P.human_summary(rep)
        self.assertIn("PROBE", txt)
        self.assertIn("ADJ", txt)
        self.assertIn("不会自动改", txt)


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
| W33-007 | 2026-10-30 | git提交 | 裸 checkout 被未提交文件拒 | 产物没清干净 | 4 片假红 | checkout -qf + 硬复位 | 脏目录跑完提交步 rc=0 | 未修 | 3 |
"""


class FailureLedger(unittest.TestCase):
    """F16：复发≥2 且未规避 → FAIL；复发≥2 且已规避 → WARN（固定文案 + 验证方式）；
    未规避且复发=1 → WARN；台账缺失 / 表解析失败 → FAIL；豁免必须带理由。"""

    def test_parse_rows_and_recurrence(self):
        rows = P.parse_failure_ledger(LEDGER_SAMPLE)
        self.assertEqual([r["id"] for r in rows],
                         ["W33-011", "W33-014", "W33-021", "W33-001", "W33-007"])
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

    def test_chronic_mitigated_is_warn_not_fail(self):
        # ★ 2026-10-31 改版：踩过 2 次但已修 → 只 WARN（不再逼人无脑 waive）
        it, hits = P.judge_failure_ledger(LEDGER_SAMPLE, categories=["账本与口径"],
                                          waive=["W33-014=rc=2 语义属采集口径变更，本单不碰 pilot 退出码"])
        self.assertEqual(it["status"], "WARN")
        self.assertIn("这条踩过 2 次，已修于 35904fb", it["detail"])
        self.assertIn("未重新引入", it["detail"])
        self.assertEqual([h["id"] for h in hits if h["recurrence"] >= 2 and h["mitigated"]],
                         ["W33-011"])

    def test_chronic_unmitigated_is_fail(self):
        # 复发 3 次且关联提交写「未修」→ 真危险（明知踩过还没修）
        it, _ = P.judge_failure_ledger(LEDGER_SAMPLE, categories=["git提交"])
        self.assertEqual(it["status"], "FAIL")
        self.assertIn("W33-007", it["detail"])
        self.assertIn("未规避", it["detail"])

    def test_waive_with_reason_downgrades_fail(self):
        it, _ = P.judge_failure_ledger(
            LEDGER_SAMPLE, categories=["git提交"],
            waive=["W33-007=checkout 已改 -qf 且本单只改 preflight，不碰 workflow 提交步"])
        self.assertNotEqual(it["status"], "FAIL")
        hit = [h for h in it["ledger_hits"] if h["id"] == "W33-007"][0]
        self.assertTrue(hit["waived"])
        self.assertIn("不碰 workflow", hit["waiver_reason"])

    def test_waive_without_reason_is_refused(self):
        for bad in ("W33-011", "W33-011=", "W33-011=无", "W33-011=ok", "W33-011 =   "):
            with self.assertRaises(ValueError):
                P.judge_failure_ledger(LEDGER_SAMPLE, categories=["账本与口径"], waive=[bad])

    def test_waive_reason_is_recorded_in_item(self):
        it, _ = P.judge_failure_ledger(
            LEDGER_SAMPLE, categories=["git提交"],
            waive=["W33-007=本单只动 preflight_dispatch.py，workflow 提交步未改"])
        self.assertEqual(it["ledger_waivers"][0]["id"], "W33-007")
        self.assertIn("workflow 提交步未改", it["ledger_waivers"][0]["reason"])

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

    def test_missing_ledger_is_fail(self):
        # 台账缺失 = 没查就派单 → FAIL（不许静默）
        it, _ = P.judge_failure_ledger("", categories=["账本与口径"])
        self.assertEqual(it["status"], "FAIL")
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

    def test_human_summary_prints_verify_and_waiver_reason(self):
        it, hits = P.judge_failure_ledger(
            LEDGER_SAMPLE, categories=["git提交"],
            waive=["W33-007=本单只动 preflight_dispatch.py，workflow 提交步未改"])
        rep = {"stage": "04b", "ref": "main", "ref_sha": "deadbeef", "verdict": "PASS_WITH_WARNINGS",
               "fail_n": 0, "warn_n": 1, "checks_total": 1, "checks": [it]}
        txt = P.human_summary(rep)
        self.assertIn("F16 故障清单比对", txt)
        self.assertIn("验证方式：脏目录跑完提交步 rc=0", txt)
        self.assertIn("豁免理由：本单只动 preflight_dispatch.py", txt)


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


class RetryCap(unittest.TestCase):
    """D13：已到重试上限（upstream_unstable）的层默认从待采队列剔除，并点名到每层。

    事故背景（2026-10-31）：同一层连续吃 3 轮 CI——`41155023558` 两层全 failed
    （`503 Wait timeout` / `Expecting value: line 1 column 1`），上一轮三个 missing 层全是
    单层超时 55 分钟。不是采集 bug，是上游不稳；不管就会无限重试。
    """

    def _summary(self, n=3, kind="non_json", no_progress=True):
        import attempt_log as A
        atts = [A.attempt_of({"layer": "L1", "status": "failed", "err": "Expecting value",
                              "elapsed_s": 33.4, "rc": 1, "rows": 0, "prior_units": 0,
                              "at": "2026-10-31T0%d:00:00Z" % (i + 1)}) for i in range(n)]
        return A.summarize(atts, 3)

    def test_cap_reached_is_warn_and_named(self):
        it = P.judge_retry_cap(self._summary(3), {"path": "analysis/04b-attempt-log.json",
                                                  "cap": 3, "attempts_n": 3})
        self.assertEqual(it["status"], "WARN")
        self.assertIn("L1", it["detail"])
        self.assertIn("3 次", it["detail"])
        self.assertIn("--force-unstable-layer", it["detail"])
        self.assertEqual(it["retry_cap_unstable"][0]["layer"], "L1")

    def test_below_cap_passes(self):
        it = P.judge_retry_cap(self._summary(2), {"path": "x", "cap": 3, "attempts_n": 2})
        self.assertEqual(it["status"], "PASS")
        self.assertEqual(it["retry_cap_unstable"], [])

    def test_missing_log_is_info_not_pass(self):
        it = P.judge_retry_cap({}, {"path": "analysis/04b-attempt-log.json", "missing": True})
        self.assertEqual(it["status"], "INFO")
        self.assertIn("attempt_log.py", it["detail"])

    def test_broken_log_is_warn_not_pass(self):
        it = P.judge_retry_cap({}, {"path": "x", "error": "JSONDecodeError"})
        self.assertEqual(it["status"], "WARN")

    def test_force_moves_it_out_of_the_warning_list(self):
        it = P.judge_retry_cap(self._summary(3), {"path": "x", "cap": 3, "attempts_n": 3},
                               force_unstable=("L1",))
        self.assertEqual(it["status"], "PASS")
        self.assertEqual([x["layer"] for x in it["retry_cap_forced"]], ["L1"])

    def test_plan_still_contains_it_is_called_out(self):
        """计划是旧的（没跑 full_plan 的剔除）→ 必须点名，不能只看「日志里有」就完事。"""
        it = P.judge_retry_cap(self._summary(3), {"path": "x", "cap": 3, "attempts_n": 3},
                               planned=[{"layer": "L1"}])
        self.assertEqual(it["retry_cap_in_plan"], ["L1"])
        self.assertIn("本次计划里仍有", it["detail"])

    def test_layer_that_succeeded_later_is_not_listed(self):
        """尝试账本只记失败，不知道「后来成功了」——状态的唯一真值是阶段账本。

        实测（2026-10-31 run 41155023558）：`vices_AGOL_…NG911` 有 3 次超时史，
        但本轮已采成（ok，3,618,012 行 = 上游 returnCount）→ 不许再挂 unstable。
        """
        it = P.judge_retry_cap(self._summary(3), {"path": "x", "cap": 3, "attempts_n": 3},
                               records=[{"layer": "L1", "status": "ok"}])
        self.assertEqual(it["status"], "PASS")
        self.assertEqual(it["retry_cap_unstable"], [])
        self.assertIn("已采成", it["detail"])
        self.assertEqual(it["cleared_by_success"], ["L1"])

    def test_duplicate_partition_layer_is_not_a_gap(self):
        """分区重复声明层（declared 已移出分母）重试只是再采一份同源重复 → 不算缺口。"""
        it = P.judge_retry_cap(self._summary(3), {"path": "x", "cap": 3, "attempts_n": 3},
                               records=[{"layer": "L1", "status": "partial",
                                         "declared_duplicate_partition": {"duplicate_of": "P@X-2"}}])
        self.assertEqual(it["retry_cap_unstable"], [])
        self.assertEqual(it["cleared_by_success"], ["L1"])


if __name__ == "__main__":
    unittest.main()
