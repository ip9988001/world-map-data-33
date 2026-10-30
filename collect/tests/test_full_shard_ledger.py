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

if __name__ == "__main__":
    unittest.main()
