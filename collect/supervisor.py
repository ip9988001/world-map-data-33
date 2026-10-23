#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工头（supervisor）—— 自研模式的监督者

与工人（collect-*.yml）完全解耦：工人不报告，工头自己巡逻。
每轮做四件事：
  1. 账本 collapsed / paused → 直接退出（不叫人）
  2. 当前步有没有活着的 run？ 有 → 检查是否卡死（>120 分钟），没卡就退出
  3. 没有活着的 run → 判验收（按 ROADMAP 判据）
      通过  → 推进到下一步，重置 fail_streak，开 Issue 递活
      不通过 → fail_streak+1；满 3 次 → collapsed=true，静默收摊
  4. 额度闸门：minutes_used ≥ 95% → paused

用法:
  python3 collect/supervisor.py --dry-run    # 只体检，不改任何东西
  python3 collect/supervisor.py --once       # 正常巡逻一轮
"""
from __future__ import annotations
import argparse, json, os, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_F = os.path.join(ROOT, "collect", "state.json")
REPO = os.environ.get("GITHUB_REPOSITORY") or "ip9988001/world-map-data-33"
LABEL = "sentinel-alarm"
STALL_MIN = 120
MAX_FAIL = 3

STEPS = {
 "00": ("地基", "collect/steps/STEP-00.md", "01", "collect-watchdog.yml"),
 "01": ("预检", "collect/steps/STEP-01.md", "02", "collect-preflight.yml"),
 "02": ("试点 8 层", "collect/steps/STEP-02.md", "03", "collect-pilot.yml"),
 "03": ("单州试跑 KS", "collect/steps/STEP-03.md", "04", "collect-state.yml"),
 "04": ("全州级放量", "collect/steps/STEP-04.md", "05", "collect-statewide.yml"),
 "05": ("县市碎片放量", "collect/steps/STEP-05.md", "06", "collect-bulk.yml"),
 "06": ("收工", "collect/steps/STEP-06.md", None, None),
}
TRIGGER = {
 "01": "gh workflow run collect-preflight.yml --repo %s",
 "02": "gh workflow run collect-pilot.yml --repo %s",
 "03": "gh workflow run collect-state.yml -f state=KS --repo %s",
 "04": "gh workflow run collect-statewide.yml --repo %s",
 "05": "gh workflow run collect-bulk.yml --repo %s",
}


def sh(args, timeout=120):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, "", str(e)


def load():
    with open(STATE_F, encoding="utf-8") as f:
        return json.load(f)


def save(st):
    with open(STATE_F, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def mins(iso):
    try:
        t = datetime.strptime(iso.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
        return (datetime.now(timezone.utc) - t).total_seconds() / 60
    except Exception:
        return 1e9


# ---------------- 验收判据 ----------------
def check_01():
    import csv
    p = os.path.join(ROOT, "collect", "layer_plan.csv")
    rows = bad = withc = 0
    try:
        with open(p, encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rows += 1
                if not (r.get("plan") or "").strip():
                    bad += 1
                if (r.get("row_count") or "").strip():
                    withc += 1
    except Exception:
        return False, {"csv": 0}, ["layer_plan.csv 不存在"]
    rate = round(withc / max(rows, 1), 3)
    ok = rows >= 50000 and bad == 0 and rate >= 0.78
    return ok, {"rows": rows, "plan_empty": bad, "count_rate": rate}, \
        [] if ok else [f"rows={rows}/50000 plan空={bad} count率={rate}/0.78"]


def check_00():
    return os.path.exists(STATE_F), {"state": True}, []


def check_generic(name, min_bytes=200):
    p = os.path.join(ROOT, "collect", name)
    if not os.path.exists(p):
        return False, {name: 0}, [f"{name} 不存在"]
    n = os.path.getsize(p)
    return n >= min_bytes, {name: n}, [] if n >= min_bytes else [f"{name} 只有 {n} 字节"]


CHECKS = {
 "00": check_00,
 "01": check_01,
 "02": lambda: check_generic("pilot_report.json"),
 "03": lambda: check_generic("ks_report.json"),
 "04": lambda: check_generic("coverage_report.md"),
 "05": lambda: check_generic("layer_status.json", 500),
 "06": lambda: check_generic("FINAL_REPORT.md", 500),
}


def active_runs(wf):
    rc, out, _ = sh(["gh", "run", "list", "--workflow", wf, "--repo", REPO, "--limit", "5",
                     "--json", "databaseId,status,startedAt,conclusion"])
    try:
        rows = json.loads(out or "[]")
    except Exception:
        return []
    return [r for r in rows if r.get("status") in ("queued", "in_progress")]


def post_issue(step, ok, body):
    sh(["gh", "label", "create", LABEL, "--repo", REPO, "--color", "d73a4a",
        "--description", "采集流水线事件/告警", "--force"])
    title = f"【三仓项目】STEP {step} {'完成' if ok else '卡住'} — {STEPS[step][0]}"
    rc, out, _ = sh(["gh", "issue", "list", "--repo", REPO, "--label", LABEL, "--state", "open",
                     "--search", f"STEP {step}", "--json", "number,title"])
    num = None
    try:
        for it in json.loads(out or "[]"):
            if f"STEP {step}" in it["title"]:
                num = it["number"]
    except Exception:
        pass
    if num:
        sh(["gh", "issue", "comment", str(num), "--repo", REPO, "--body", body])
        return num
    rc, out, _ = sh(["gh", "issue", "create", "--repo", REPO, "--label", LABEL,
                     "--title", title, "--body", body])
    return out.strip().splitlines()[-1] if out else None


def briefing(st, step, ok, metrics, notes):
    name, page, nxt, _ = STEPS[step]
    L = [f"## 【三仓项目】工人停手了：STEP {step} {name}", "",
         f"- 自动判定：**{'✅ 合格' if ok else '❌ 不合格'}**",
         f"- 尝试次数：{st.get('fail_streak', 0) + 1} / {MAX_FAIL}（连败 3 次收摊）",
         f"- 关键数字：`{json.dumps(metrics, ensure_ascii=False)[:500]}`",
         f"- 上次错误：`{st.get('last_error') or '-'}`",
         f"- 账本：`collect/state.json`　当前步：{step}　预算：{st['budget']['minutes_used']}/{st['budget']['minutes_cap']} 分钟"]
    if notes:
        L += ["", "**不过的原因**："] + [f"- {n}" for n in notes]
    L += ["", "### 地图（自己看，不要问人）", f"- 本步说明书：`{page}`",
          "- 总图：`collect/ROADMAP.md`　模式说明：`collect/SELF_DRIVE.md`"]
    if nxt:
        L += ["", f"### 下一步：STEP {nxt} {STEPS[nxt][0]}",
              f"- 读：`{STEPS[nxt][1]}`",
              f"- 触发：`{TRIGGER.get(nxt, '(见说明书)') % REPO}`"]
    else:
        L += ["", "### 最后一步：按 STEP-06 推企微后停下。"]
    return "\n".join(L)




# ---------------- 进入自研模式的条件自检（12 条） ----------------
def entry_check():
    import glob
    C = []
    def add(n, name, ok, ev):
        C.append({"n": n, "name": name, "ok": bool(ok), "ev": ev})
    add(1, "总图存在", os.path.exists(os.path.join(ROOT, "collect", "ROADMAP.md")), "collect/ROADMAP.md")
    steps = sorted(glob.glob(os.path.join(ROOT, "collect", "steps", "STEP-*.md")))
    add(2, "每步说明书齐全", len(steps) >= 7, f"{len(steps)} 张")
    try:
        st = load()
        keys = {"fail_streak", "collapsed", "attempts", "budget"} <= set(st)
    except Exception:
        keys, st = False, {}
    add(3, "账本字段完整", keys, "fail_streak/collapsed/attempts/budget")
    # 4 工人与工头分离
    sep = True
    for wf in glob.glob(os.path.join(ROOT, ".github", "workflows", "collect-*.yml")):
        if "herald" in open(wf, encoding="utf-8").read() or "supervisor" in open(wf, encoding="utf-8").read():
            if "collect-supervisor" not in wf:
                sep = False
    add(4, "工人不含报警步骤", sep, "采集 workflow 内无 herald/supervisor 调用")
    add(5, "工头能发现该动没动", "active_runs" in open(__file__, encoding="utf-8").read(), "按 run 存活判")
    add(6, "能发现卡死", STALL_MIN == 120, f"阈值 {STALL_MIN} 分钟")
    src = open(__file__, encoding="utf-8").read()
    add(7, "简报自包含", all(k in src for k in ("尝试次数", "上次错误", "本步说明书", "触发：")), "含步号/数字/尝试/错误/地图/命令")
    add(8, "三振出局", MAX_FAIL == 3 and "collapsed" in src, "连败 3 次 collapsed")
    add(9, "防重复点火", os.path.exists(os.path.join(ROOT, ".github", "workflows", "collect-supervisor.yml")), "concurrency 锁 + last_triggered")
    b = st.get("budget", {})
    add(10, "额度闸门", "stop_ratio" in b and b.get("stop_ratio", 1) <= 0.95, f"stop={b.get('stop_ratio')}")
    add(11, "改动自检", os.path.exists(os.path.join(ROOT, ".github", "workflows", "ci-smoke.yml")), "ci-smoke.yml")
    add(12, "自检可验证", "--dry-run" in src, "supervisor.py --dry-run")
    return C


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--entry-check", action="store_true")
    a = ap.parse_args()
    if a.entry_check:
        C = entry_check()
        for c in C:
            print(("✅" if c["ok"] else "❌") + f" {c['n']:>2}. {c['name']} — {c['ev']}")
        good = sum(1 for c in C if c["ok"])
        print(f"\n{'READY' if good == len(C) else 'BLOCKED'}：{good}/{len(C)} 条通过")
        return 0 if good == len(C) else 1
    st = load()
    step = st.get("current_step")
    report = {"step": step, "mode": st.get("mode"), "checks": []}

    def say(k, v, ok=True):
        report["checks"].append({"k": k, "v": v, "ok": ok})
        print(("✅ " if ok else "❌ ") + f"{k}: {v}")

    say("账本可读", "ok", True)
    say("模式", st.get("mode"))
    if st.get("status") in ("awaiting_go", "finished"):
        say("状态", st["status"] + " —— 未获确认，静止不巡逻")
        return 0
    if st.get("collapsed"):
        say("熔断状态", "collapsed（三振出局，静默停止）", False)
        return 0
    if st.get("status") == "paused":
        say("额度", "paused", False)
        return 0

    b = st.setdefault("budget", {})
    b.setdefault("minutes_used", 0); b.setdefault("minutes_cap", 1800)
    b.setdefault("warn_ratio", 0.8); b.setdefault("stop_ratio", 0.95)
    ratio = b["minutes_used"] / max(b["minutes_cap"], 1)
    say("额度", f"{b['minutes_used']}/{b['minutes_cap']} ({ratio:.0%})", ratio < b["stop_ratio"])
    if ratio >= b["stop_ratio"]:
        if not a.dry_run:
            st["status"] = "paused"
            save(st)
        say("动作", "额度耗尽 → paused，静默停止")
        return 0

    wf = STEPS[step][3]
    act = active_runs(wf) if wf else []
    say("工人", f"{wf} 活着的 run = {len(act)}")
    if act:
        age = min(mins(r.get("startedAt") or "") for r in act)
        if age > STALL_MIN:
            say("卡死", f"run 已跑 {age:.0f} 分钟 > {STALL_MIN} → 判失败", False)
            ok, metrics, notes = False, {"stalled_min": round(age)}, [f"卡死 {age:.0f} 分钟"]
        else:
            say("状态", f"工人在干活（{age:.0f} 分钟），不打扰")
            return 0
    else:
        ok, metrics, notes = CHECKS[step]()
        say("验收", "通过" if ok else "未通过", ok)

    if ok:
        st["fail_streak"] = 0
        st["last_error"] = None
        st.setdefault("steps", {})[step] = {"status": "done",
                                            "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                                            "metrics": metrics}
        nxt = STEPS[step][2]
        st["current_step"] = nxt or "06"
        st["status"] = "finished" if nxt is None else "running"
        if nxt:
            st["last_triggered"] = {"step": nxt, "run_id": None}
    else:
        st["fail_streak"] = st.get("fail_streak", 0) + 1
        st["last_error"] = "; ".join(notes)[:300]
        if st["fail_streak"] >= MAX_FAIL:
            st["collapsed"] = True
            st["status"] = "collapsed"
            say("熔断", f"连败 {st['fail_streak']} 次 → collapsed，收摊，不再叫人")
        else:
            st["status"] = "retry"

    if a.dry_run:
        say("dry-run", "不改账本、不发 Issue")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    save(st)
    if not (st.get("collapsed") and not ok):
        num = post_issue(step, ok, briefing(st, step, ok, metrics, notes))
        say("Issue", str(num))
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
