#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""单县对象级断点续跑回归（muse-000146 第 11 项 / W2-018 的县内细化）。

跑法：python3 -m unittest discover -s collect/tests -q
或：  python3 collect/tests/test_county_ckpt_resume.py

它验的是「县内被打断」这件事，比 test_county_ckpt.py 的「县与县之间」更细一层：
  · 上游翻页翻到一半被杀 → checkpoint 里留下 last_objectid / raw_fetched / sha256；
  · 续跑从 last_objectid **之后**接着拉，不从头下载该县；
  · 已完成的县一次都不再调用（不重抓）；
  · raw_fetched == declared_upstream 才算该县 done，不达标记 failed，不许静默当完成；
  · 县完成后 `.part` 分片自动删掉，断点县留着续写。

全部用 mock 上游 + 临时目录，不联网、不碰真账本。
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "collect"))

import county_ckpt as CK  # noqa: E402

UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

# mock 上游：每县有 N 个对象，id 从 1 开始；页大小 2
UPSTREAM = {
    "33001": list(range(1, 5)),     # 4 个对象
    "33003": list(range(1, 7)),     # 6 个对象 —— 这个县会在第 1 页后被打断
    "33005": list(range(1, 5)),     # 4 个对象
}
PAGE = 2


class ObjectLevelResume(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="ckpt-resume-")
        self.src = os.path.join(self.tmp, "US-NH-overture.json.gz")
        Path(self.src).write_bytes(b"upstream-v1")
        self.fp = CK.source_fingerprint([self.src])
        self.counties = ["33001", "33003", "33005"]
        self.fetched: list[tuple[str, int]] = []      # (fips, objectid) —— 记「实际从上游拉了什么」
        self.interrupt_on: dict[str, int] = {"33003": 2}   # 33003 拉到 oid=2 后模拟被杀

    # ------------------------------------------------------------ 假采集县函数
    def _work(self, fips: str, resume: dict):
        """按 resume['last_objectid'] 续拉；每页落一次 checkpoint（模拟真实翻页）。"""
        start = (resume.get("last_objectid") or 0)
        ids = [i for i in UPSTREAM[fips] if i > start]
        part = CK.part_path("NH", fips, self.tmp)
        os.makedirs(os.path.dirname(part), exist_ok=True)
        n = int(resume.get("raw_fetched") or 0)
        for k in range(0, len(ids), PAGE):
            page = ids[k:k + PAGE]
            for oid in page:
                self.fetched.append((fips, oid))
                with open(part, "a", encoding="utf-8") as fh:
                    fh.write("%s\t%d\n" % (fips, oid))
                n += 1
            # 每页把断点刷进账本（真实代码用 CK.load/CK.progress/CK.save 三件套）
            d = CK.load("NH", self.tmp)
            CK.progress(d, fips, last_objectid=page[-1], raw_fetched=n,
                        declared_upstream=len(UPSTREAM[fips]), sha256=CK.part_sha256(part))
            CK.save(d, self.tmp)
            if self.interrupt_on.get(fips) == page[-1]:
                raise RuntimeError("模拟上游中断（进程被杀 / 504）")
        return {"raw_fetched": n, "declared_upstream": len(UPSTREAM[fips]),
                "sha256": CK.part_sha256(part),
                "last_objectid": ids[-1] if ids else start}

    def _run(self, **kw) -> dict:
        return CK.run_counties("NH", self.counties, work_with_resume=self._work,
                               ledger_dir=self.tmp, fingerprint=self.fp,
                               log=lambda m: print("   " + m), **kw)

    # ------------------------------------------------------------ 主用例
    def test_interrupt_mid_county_then_resume_from_last_objectid(self) -> None:
        print("\n===== 第一次：33003 在 oid=2 后被打断 =====")
        s1 = self._run()
        self.assertEqual(s1["done"], 2, "另两县应先完成：%r" % s1)
        self.assertEqual(s1["failed"], 1, "被打断的县必须记 failed：%r" % s1)

        doc = CK.load("NH", self.tmp)
        rec = doc["counties"]["33003"]
        self.assertEqual(rec["status"], "failed", "中断县不许当 done：%r" % rec)
        self.assertEqual(rec["last_objectid"], 2, "断点应停在最后一个已落盘对象：%r" % rec)
        self.assertEqual(rec["raw_fetched"], 2, "已落盘行数应=2：%r" % rec)
        self.assertEqual(rec["declared_upstream"], 6, "上游声明行数应=6：%r" % rec)
        self.assertTrue(rec.get("sha256"), "必须记分片 sha256：%r" % rec)
        self.assertRegex(rec.get("updated_at") or "", UTC_RE, "updated_at 必须是 UTC ISO：%r" % rec)

        part = CK.part_path("NH", "33003", self.tmp)
        self.assertTrue(os.path.exists(part), "断点县必须留着 .part 分片：%s" % part)
        self.assertFalse(os.path.exists(CK.part_path("NH", "33001", self.tmp)),
                         "已完成县的分片应已删掉")

        # 已完成县：一次都没重抓
        self.assertEqual([o for f, o in self.fetched if f == "33001"], [1, 2, 3, 4])
        self.assertEqual([o for f, o in self.fetched if f == "33005"], [1, 2, 3, 4])
        self.assertEqual([o for f, o in self.fetched if f == "33003"], [1, 2], "第一次只该拉到 2")

        print("\n===== 第二次：只续跑 33003，从 oid=3 开始 =====")
        self.fetched.clear()
        self.interrupt_on = {}                      # 这次不再打断
        s2 = self._run()

        self.assertEqual(s2["ran"], ["33003"], "只有断点县该跑：%r" % s2)
        self.assertEqual(sorted(s2["skipped"]), ["33001", "33005"], "已完成县必须跳过：%r" % s2)
        self.assertEqual(s2["resumed"], ["33003"], "应报告「续跑」的县：%r" % s2)

        fetched_3 = [o for f, o in self.fetched]
        self.assertEqual(fetched_3, [3, 4, 5, 6], "续跑必须从 oid=3 起，不重下 1、2：%r" % fetched_3)
        self.assertEqual([f for f, _ in self.fetched], ["33003"] * 4,
                         "另两县不许再被调用一次：%r" % self.fetched)

        doc = CK.load("NH", self.tmp)
        rec = doc["counties"]["33003"]
        self.assertEqual(rec["status"], "done", "续跑补齐后应 done：%r" % rec)
        self.assertEqual(rec["raw_fetched"], rec["declared_upstream"],
                         "raw_fetched 必须等于 declared_upstream：%r" % rec)
        self.assertEqual(rec["raw_fetched"], 6, "%r" % rec)
        self.assertFalse(os.path.exists(part), "done 后 .part 应被删掉：%s" % part)
        self.assertEqual(s2["done"], 3, "三县全 done：%r" % s2)

    # ------------------------------------------------------------ 对账红线
    def test_raw_fetched_must_equal_declared_upstream(self) -> None:
        print("\n===== 短采：raw_fetched < declared_upstream 不许当 done =====")
        CK.run_counties("NH", ["33001"], work=lambda f: {"raw_fetched": 3, "declared_upstream": 4},
                        ledger_dir=self.tmp, fingerprint=self.fp)
        rec = CK.load("NH", self.tmp)["counties"]["33001"]
        self.assertEqual(rec["status"], "failed", "短采必须 failed：%r" % rec)
        self.assertIn("rows_mismatch", rec["fail_reason"], "%r" % rec)
        self.assertEqual(rec["raw_fetched"], 3, "%r" % rec)
        self.assertEqual(rec["declared_upstream"], 4, "%r" % rec)

    # ------------------------------------------------------------ 续跑点读取
    def test_resume_point_and_part_path_contract(self) -> None:
        print("\n===== 续跑点契约（resume_of / part_path）=====")
        self.assertEqual(CK.resume_of("NH", "33009", self.tmp)["last_objectid"], None,
                         "无记录时 last_objectid 必须是 None（=从头开始）")
        self.assertEqual(CK.resume_of("NH", "33009", self.tmp)["raw_fetched"], 0)
        self.assertTrue(CK.part_path("NH", "33009", self.tmp).endswith("/county_part_NH/33009.part"),
                        "分片路径格式：%s" % CK.part_path("NH", "33009", self.tmp))
        self.assertEqual(CK.part_sha256(CK.part_path("NH", "33009", self.tmp)), "",
                         "分片不存在时 sha256 必须是空串")


if __name__ == "__main__":
    unittest.main(verbosity=2)
