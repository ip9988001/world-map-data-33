# -*- coding: utf-8 -*-
"""steps.json ↔ 判据卡 ↔ 工头 三方契约的防护网（零网络、只读）

为什么要有它：2026-10-30 b1bc572 把 04b/05b/07b/10b 四个补采阶段只加进了 steps.json，
没补 4 份判据卡、没补 4 份工头；`supervisor.py --entry-check` 从那次起连续 5 次 ci-smoke 静默红
（每次只跑 10~12 秒就挂在第 3 步「结构自检」上，看着像依赖装不上，实际是结构漂移）。

这条单测把同一批契约压进 unittest：
  · 步号文法（基础步 0..NN 连续，补采变体只能是 <基础步>b）
  · 每个步号都有工头 + 判据卡（点名的那份，不是「目录里随便有一份」）
  · 判据卡镜像块与 steps.json 逐字段一致（check_docs.py 的判据）
再加一条兜底：直接跑 `--entry-check`，红就红在这儿，不再等 CI 12 秒后才发现。
"""
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
COLLECT = os.path.dirname(HERE)
ROOT = os.path.dirname(COLLECT)
STEPS_F = os.path.join(COLLECT, "steps.json")


def _steps():
    with open(STEPS_F, encoding="utf-8") as f:
        return json.load(f)["steps"]


class TestStepsContract(unittest.TestCase):
    def setUp(self):
        self.steps = _steps()

    def test_step_grammar(self):
        ids = set(self.steps)
        odd = [k for k in ids if not re.fullmatch(r"\d+b?", k)]
        self.assertEqual(odd, [], "步号只允许 00..NN 与 NNb（补采变体），越界：%s" % odd)
        base = {k for k in ids if k.isdigit()}
        self.assertEqual(sorted(int(k) for k in base), list(range(len(base))),
                         "基础步号必须从 0 连续：%s" % sorted(base))
        orphan = [k for k in ids if k.endswith("b") and k[:-1] not in base]
        self.assertEqual(orphan, [], "补采变体的基础步必须存在：%s" % orphan)

    def test_every_step_has_supervisor(self):
        missing = [k for k in self.steps
                   if not os.path.exists(os.path.join(COLLECT, "supervisors", "step_%s.py" % k))]
        self.assertEqual(missing, [], "缺工头 supervisors/step_<step>.py：%s" % missing)

    def test_every_step_has_its_own_card(self):
        """按各步 supervise.doc 点名的那份判据卡校验，不接受「共用一份凑数」。"""
        missing = []
        for k, s in self.steps.items():
            rel = (s.get("supervise") or {}).get("doc") or "collect/steps/STEP-%s.md" % k
            if not os.path.exists(os.path.join(ROOT, rel)):
                missing.append((k, rel))
        self.assertEqual(missing, [], "判据卡不存在（steps.json → supervise.doc）：%s" % missing)

    def test_worker_workflow_exists(self):
        missing = []
        for k, s in self.steps.items():
            wf = (s.get("supervise") or {}).get("wf") or ""
            if not os.path.exists(os.path.join(ROOT, ".github", "workflows", wf)):
                missing.append((k, wf))
        self.assertEqual(missing, [], "工人 workflow 不存在：%s" % missing)

    def test_doc_mirror_matches_steps_json(self):
        """判据卡镜像块漂移 = ci-smoke 第 4 步红。这里提前红，并给出逐条问题。"""
        r = subprocess.run([sys.executable, os.path.join(COLLECT, "check_docs.py"), "--json"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         "check_docs.py 判红（判据卡与 steps.json 不一致）：\n%s%s"
                         % (r.stdout[-3000:], r.stderr[-800:]))

    def test_polygon_steps_require_centroid(self):
        """面层步骤必须声明 poly_centroid，且 pilot 采集侧默认开 + 落 `_lat`/`_lon`。

        2026-10-30 的 1,038 层「有行无坐标」就是这一步没锁 —— 一旦有人把
        PILOT_POLY_CENTROID 改回默认关，或者新增的面层步骤忘了声明，这里当场红。
        """
        poly = [k for k, s in self.steps.items() if (s or {}).get("kind") == "parcel_situs"]
        self.assertTrue(poly, "steps.json 里没有任何面层（parcel_situs）步骤？")
        lack = [k for k in poly if (self.steps[k] or {}).get("poly_centroid") is not True]
        self.assertEqual(lack, [], "面层步骤没声明 poly_centroid=true：%s" % lack)
        src = open(os.path.join(COLLECT, "pilot.py"), encoding="utf-8").read()
        self.assertIn('os.environ.get("PILOT_POLY_CENTROID", "1")', src,
                      "pilot.py 的 PILOT_POLY_CENTROID 默认值被改成关了")
        self.assertIn('"_lat": lat', src, "pilot.py 不再落 `_lat`/`_lon` —— 面层会再次无坐标")
        self.assertIn("def poly_point(", src, "pilot.py 丢了面层取点实现（representative_point）")

    def test_structure_gate_is_green(self):
        """ci-smoke 第 3 步的同一道闸：结构自检必须全绿（现在是 29 条）。"""
        r = subprocess.run([sys.executable, os.path.join(COLLECT, "supervisor.py"), "--entry-check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         "结构自检没全绿（这就是 ci-smoke 10 秒爆红的那一步）：\n%s%s"
                         % (r.stdout[-3000:], r.stderr[-800:]))


if __name__ == "__main__":
    unittest.main()
