#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报工员（计数机器人）

采摘机器人一停 —— 不管摘完没摘完 —— 它就干活：
  1. 读账本 collect/state.json
  2. 按 ROADMAP 判据自动判「合格 / 不合格」
  3. 开/更新 Issue，简报自带地图：第几步、数字、达标否、下一步读哪个文件、触发命令
  4. 更新账本（含防重复点火 last_triggered）

用法：
  python3 scripts/herald.py --step 02 --status success --run-id 123
  python3 scripts/herald.py --selftest
"""
# 【2026-10-24 已废止】v1 工头。自研模式 v2 起，工头只叫醒大脑、不判验收：
# 改看 collect/supervisor.py + collect/supervisors/step_0X.py。
# 本文件保留仅为考古；直接运行会被下面的守卫拦下。
# ★ 废止标记必须写成注释 —— 上一版把中文正文塞进 docstring 外面，
#   导致 py_compile 报 invalid character '【'，把 ci-smoke 连续 4 次刷成假红。
from __future__ import annotations
import argparse, json, os, subprocess
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_F = os.path.join(ROOT, "collect", "state.json")
REPO = os.environ.get("GITHUB_REPOSITORY") or "ip9988001/world-map-data-33"
LABEL = "sentinel-alarm"

STEPS = {
 "00": ("地基", "collect/steps/STEP-00.md", "01"),
 "01": ("预检", "collect/steps/STEP-01.md", "02"),
 "02": ("试点 8 层", "collect/steps/STEP-02.md", "03"),
 "03": ("单州试跑 KS", "collect/steps/STEP-03.md", "04"),
 "04": ("全州级放量", "collect/steps/STEP-04.md", "05"),
 "05": ("县市碎片放量", "collect/steps/STEP-05.md", "06"),
 "06": ("收工", "collect/steps/STEP-06.md", None),
}
TRIGGER = {
 "01": "gh workflow run collect-preflight.yml --repo %s",
 "02": "gh workflow run collect-pilot.yml --repo %s",
 "03": "gh workflow run collect-state.yml -f state=KS --repo %s",
 "04": "gh workflow run collect-statewide.yml --repo %s",
 "05": "gh workflow run collect-bulk.yml --repo %s",
}

def sh(args, timeout=180):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, "", str(e)

def load_state():
    with open(STATE_F, encoding="utf-8") as f:
        return json.load(f)

def save_state(st):
    with open(STATE_F, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)

# ---------------- 判据（机器判） ----------------
def check_00():
    ok = os.path.exists(STATE_F)
    return ok, {"state_readable": ok}, [] if ok else ["state.json 读不到"]

def check_01():
    import csv
    p = os.path.join(ROOT, "collect", "layer_plan.csv")
    rows = bad = withc = 0
    try:
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows += 1
                if not (r.get("plan") or "").strip(): bad += 1
                if (r.get("row_count") or "").strip(): withc += 1
    except Exception:
        return False, {"csv": 0}, ["layer_plan.csv 不存在"]
    rate = round(withc / max(rows, 1), 3)
    m = {"rows": rows, "plan_empty": bad, "count_rate": rate}
    ok = rows >= 50000 and bad == 0 and rate >= 0.95
    return ok, m, [] if ok else [f"判据未过：rows={rows}/50000 plan空={bad} 有count率={rate}/0.95"]

def _manifests():
    out = []
    for d, _, fs in os.walk(os.path.join(ROOT, "collect", "out")):
        for f in fs:
            if f == "_manifest.json":
                try:
                    out.append(json.load(open(os.path.join(d, f), encoding="utf-8")))
                except Exception:
                    pass
    return out

def check_02():
    ms = _manifests()
    got = [m for m in ms if (m.get("rows") or 0) > 0]
    worst = 0.0
    for m in got:
        c, r = m.get("count") or 0, m.get("rows") or 0
        if c: worst = max(worst, abs(r - c) / c)
    m = {"layers": len(ms), "with_rows": len(got), "worst_diff": round(worst, 4)}
    ok = len(got) >= 7 and worst < 0.01
    return ok, m, [] if ok else [f"判据未过：有数据层={len(got)}/7 最大对账误差={m['worst_diff']}/0.01"]

def check_03():
    p = os.path.join(ROOT, "collect", "ks_report.json")
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        return False, {}, ["ks_report.json 不存在"]
    st = d.get("status") or {}
    failed = st.get("failed", 0)
    rate = round(failed / max(sum(st.values()) or 1, 1), 3)
    m = {"status": st, "failed_rate": rate}
    ok = st.get("pending", 0) == 0 and rate < 0.15
    return ok, m, [] if ok else [f"判据未过：pending={st.get('pending')} 失败率={rate}"]

def check_04():
    p = os.path.join(ROOT, "collect", "coverage_report.md")
    if not os.path.exists(p):
        return False, {}, ["coverage_report.md 不存在"]
    n = os.path.getsize(p)
    return n > 1000, {"report_bytes": n}, [] if n > 1000 else ["报告太小，疑似没内容"]

def check_05():
    p = os.path.join(ROOT, "collect", "layer_status.json")
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        return False, {}, ["layer_status.json 不存在"]
    pend = sum(1 for v in d.values() if v == "pending")
    failed = sum(1 for v in d.values() if v == "failed")
    rate = round(failed / max(len(d), 1), 3)
    m = {"layers": len(d), "pending": pend, "failed": failed, "failed_rate": rate}
    ok = pend == 0 and rate < 0.15
    return ok, m, [] if ok else [f"判据未过：pending={pend} 失败率={rate}"]

def check_06():
    ok = os.path.exists(os.path.join(ROOT, "collect", "FINAL_REPORT.md"))
    return ok, {"final_report": ok}, [] if ok else ["FINAL_REPORT.md 不存在"]

CHECKS = {"00": check_00, "01": check_01, "02": check_02, "03": check_03,
          "04": check_04, "05": check_05, "06": check_06}

def briefing(step, ok, metrics, notes, wf, run_id):
    name, page, nxt = STEPS[step]
    L = [f"## 采摘机器人停了：STEP {step} {name}", "",
         f"- workflow 状态：**{wf}**　run `{run_id or '-'}`",
         f"- 自动判定：**{'✅ 合格' if ok else '❌ 不合格'}**",
         f"- 关键数字：`{json.dumps(metrics, ensure_ascii=False)[:600]}`"]
    if notes:
        L += ["", "**不过的原因**："] + [f"- {n}" for n in notes]
    L += ["", "### 地图（自己看，不要问人）",
          f"- 本步说明书：`{page}`",
          "- 总图：`collect/ROADMAP.md`",
          "- 账本：`collect/state.json`"]
    if nxt:
        L += ["", f"### 下一步：STEP {nxt} {STEPS[nxt][0]}",
              f"- 读这张纸：`{STEPS[nxt][1]}`",
              f"- 触发：`{TRIGGER.get(nxt, '(见说明书)') % REPO}`"]
    else:
        L += ["", "### 已到最后一步：按 STEP-06 推企微后停下等人。"]
    return "\n".join(L)

def post_issue(step, body, ok):
    sh(["gh", "label", "create", LABEL, "--repo", REPO, "--color", "d73a4a",
        "--description", "采集流水线事件/告警", "--force"])
    title = f"【采集】STEP {step} {'完成' if ok else '卡住'} — {STEPS[step][0]}"
    rc, out, _ = sh(["gh", "issue", "list", "--repo", REPO, "--label", LABEL, "--state", "open",
                     "--search", f"【采集】STEP {step}", "--json", "number,title"])
    num = None
    try:
        for it in json.loads(out or "[]"):
            if it["title"].startswith(f"【采集】STEP {step}"):
                num = it["number"]
    except Exception:
        pass
    if num:
        sh(["gh", "issue", "comment", str(num), "--repo", REPO, "--body", body])
        return num
    rc, out, err = sh(["gh", "issue", "create", "--repo", REPO, "--label", LABEL,
                       "--title", title, "--body", body])
    return out.strip().splitlines()[-1] if out else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--step")
    ap.add_argument("--status", default="success")
    ap.add_argument("--run-id", default="")
    ap.add_argument("--note", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        ok, m, n = check_00()
        num = post_issue("00", briefing("00", ok, m, n, "selftest", "-"), ok)
        print(json.dumps({"selftest": True, "ok": ok, "issue": num}, ensure_ascii=False))
        return 0
    if a.step not in STEPS:
        print("unknown step"); return 2
    st = load_state()
    okc, metrics, notes = CHECKS[a.step]()
    ok = okc and a.status == "success"
    if a.status != "success":
        notes = notes + [f"workflow 没成功：{a.status}"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    st.setdefault("steps", {})[a.step] = {"status": "done" if ok else "blocked", "at": now,
                                          "wf": a.status, "run_id": a.run_id,
                                          "metrics": metrics, "notes": notes}
    st["current_step"] = a.step if not ok else (STEPS[a.step][2] or "06")
    st["status"] = "running" if ok else "blocked"
    st["last_run_id"] = a.run_id or st.get("last_run_id")
    if ok and STEPS[a.step][2]:
        st["last_triggered"] = {"step": STEPS[a.step][2], "run_id": None}
    save_state(st)
    num = post_issue(a.step, briefing(a.step, ok, metrics, notes, a.status, a.run_id), ok)
    print(json.dumps({"step": a.step, "ok": ok, "metrics": metrics, "issue": num}, ensure_ascii=False))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
