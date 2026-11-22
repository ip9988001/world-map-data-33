# -*- coding: utf-8 -*-
"""full_shard.write_ledger 契约：增量落账（被掐也留痕）+ 四态计数。

2026-10-30 事故：shard 1/3/6 卡在挂死的上游，被 350 分钟上限掐成 cancelled，
而账本只在循环末尾写一次 → 已跑完的层跟着蒸发，整片「cancelled 零痕迹」。
"""
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import full_shard as FS  # noqa: E402


class WriteLedger(unittest.TestCase):
    def setUp(self):
        self.d=tempfile.mkdtemp()
        self.out=os.path.join(self.d,'04b_shard03.json')
        self.layers=['a','b','c']
        self.plan={'size':4}
    def test_incremental_partial_run_is_marked(self):
        recs=[{'layer':'a','status':'ok','rows':10,'declared':10}]
        led=FS.write_ledger(self.out,'step04b','04b',3,[{}],self.plan,1000,[],self.layers,recs,True)
        self.assertTrue(led['partial_run'])
        self.assertEqual(led['ok'],1)
        self.assertEqual(led['layers_planned'],3)
        self.assertEqual(led['layers_n'],1)
        self.assertEqual(led['rows'],10)
        on_disk=json.load(open(self.out,encoding='utf-8'))
        self.assertTrue(on_disk['partial_run'])
    def test_final_write_not_partial(self):
        recs=[{'layer':x,'status':'failed','rows':0,'declared':5} for x in self.layers]
        led=FS.write_ledger(self.out,'step04b','04b',3,[{}],self.plan,1000,[],self.layers,recs,False)
        self.assertFalse(led['partial_run'])
        self.assertEqual(led['failed'],3)
        self.assertEqual(led['declared'],15)
    def test_counts_all_states(self):
        recs=[{'layer':'a','status':'ok','rows':1,'declared':1},
              {'layer':'b','status':'empty','rows':0,'declared':0},
              {'layer':'c','status':'partial','rows':5,'declared':10},
              {'layer':'d','status':'skipped_done','rows':None,'declared':None}]
        led=FS.write_ledger(self.out,'step04b','04b',3,[{}],self.plan,1000,[],recs,recs,False)
        self.assertEqual((led['ok'],led['empty'],led['partial'],led['skipped_done']),(1,1,1,1))
        self.assertEqual(led['rows'],6)

class CoverageDisplay(unittest.TestCase):
    """★ 2026-11-22：`rows > declared` 不许再渲染成负缺口。

    事故（run 44992201755）：100 层因跨代际双算 rows≈2×declared，而 `partial` 的 reason 用
    `(declared - rows)/declared` 算 → 账本上写着「缺口 -99.93%」。读者只会得出「差 99.93%
    没采到」的结论，实际是多算了一倍 —— 账本在说谎。现在覆盖率封顶 100%，
    「实采超出声明」单独留 `rows_exceeds_declared` 标记（异常信号不许静默吞掉）。
    """

    def test_rows_exceed_declared_is_capped_not_negative(self):
        txt, flags = FS.coverage_note(555729, 277958)
        self.assertEqual(FS.coverage_pct(555729, 277958), 100.0)
        self.assertIn("100.00%", txt)
        self.assertNotIn("-", txt)                       # 不许出现负缺口
        self.assertNotIn("缺口 -", txt)
        self.assertTrue(flags["rows_exceeds_declared"])
        self.assertEqual(flags["rows_excess"], 277771)

    def test_exact_match_has_no_flag(self):
        txt, flags = FS.coverage_note(25834, 25834)
        self.assertEqual(flags, {})
        self.assertIn("100.00%", txt)

    def test_short_layer_still_reports_coverage(self):
        txt, flags = FS.coverage_note(25776, 25834)
        self.assertEqual(flags, {})
        self.assertAlmostEqual(FS.coverage_pct(25776, 25834), 99.7755, places=3)

    def test_zero_declared_has_no_denominator(self):
        txt, flags = FS.coverage_note(0, 0)
        self.assertIn("无分母", txt)
        self.assertEqual(flags, {})
        self.assertIsNone(FS.coverage_pct(0, 0))
        self.assertIsNone(FS.coverage_pct(5, None))


if __name__ == "__main__":
    unittest.main()
