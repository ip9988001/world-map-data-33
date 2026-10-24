# -*- coding: utf-8 -*-
"""lib/schema.normalize 回归测试

2026-10-24 事故：schema.py 从 pilot.py 抽模块时漏了 `import re` / `import hashlib`。
带「完整地址」字段的层（STEP-03 灰度 20 层里有 5 层）全部 NameError 秒挂，
而缺这两行的代码在纯语法检查、导入检查下都看不出来 —— 只有真喂一条带 full 的地址才炸。
所以这里直接喂数据，不做静态分析。
"""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from lib.schema import normalize  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_full_address_branch(self):
        """走 re.match 分支（原来的 NameError 触发点）。"""
        r = normalize({"FULLADDR": "123 Main St", "ST_NAME": "Main", "ZIP": "66044"}, 38.9, -95.2)
        self.assertEqual(r["add_num"], "123")
        self.assertEqual(r["zip"], "66044")
        self.assertEqual(r["lat"], 38.9)

    def test_addr_key_branch(self):
        """走 hashlib.md5 分支（第二个漏 import 的点）。"""
        r = normalize({"ADD_NUM": "12", "ST_NAME": "Oak", "ZIP": "66044"}, None, None)
        self.assertTrue(r["addr_key"], "add_num + st_name 都在时必须算得出 addr_key")
        self.assertEqual(len(r["addr_key"]), 16)

    def test_no_address(self):
        r = normalize({}, None, None)
        self.assertEqual(r["addr_key"], "")


class TestModulesImport(unittest.TestCase):
    def test_all_collect_modules_import(self):
        """collect/ 下所有模块都要能导入（漏写的模块级依赖会在这里暴露）。"""
        import importlib
        root = os.path.dirname(HERE)
        mods = []
        for dirpath, _, files in os.walk(root):
            if os.sep + "tests" in dirpath or os.sep + "legacy" in dirpath:
                continue
            for f in files:
                if f.endswith(".py") and f != "__init__.py":
                    rel = os.path.relpath(os.path.join(dirpath, f), root)[:-3].replace(os.sep, ".")
                    mods.append(rel)
        self.assertGreater(len(mods), 10, "collect/ 下的模块数不对：%s" % mods[:5])
        for m in mods:
            with self.subTest(module=m):
                importlib.import_module(m)


if __name__ == "__main__":
    unittest.main()
