#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工头（supervisor）—— 自研模式 v2

铁律（v2 · 2026-10-24 落地）：**工头只叫醒大脑，验收判定权 100% 归大脑。**

它能做的三件事：
  1. 看有没有活着的 run（有 → 只记录事实；跑太久也只报告，**不判死**）
  2. 没活 run → 收集证据 → 写 collect/wake/WAKE.json → 开 Issue **叫醒**大脑
  3. 记事实账（last_run / awaiting_brain / 预算），**不写任何合格/不合格**

它不能做的（写死在代码里）：
  ✗ 比数字判验收 —— 判据在执行者脑子里；脚本只会比大小，不会判原因
  ✗ 自己推进 current_step、自己点火下一步 —— 点火只能由大脑下令
  ✗ 写失败计数 / 收摊标记 —— 「收摊」是决定，不是事实
  ✗ 推企微 —— 老板只该收到大脑的话
  ✗ 用 `|| true` 吞错

用法:
  python3 collect/supervisor.py --once                # 巡逻一轮（叫醒用，CI cron 调这个）
  python3 collect/supervisor.py --dry-run             # 只看证据，不改任何东西
  python3 collect/supervisor.py --entry-check         # v2 结构自检
  python3 collect/supervisor.py --kick 02 --layers a,b --workers 8   # 【大脑下令】点火工人
  python3 collect/supervisor.py --review pass --note "..." --next 03  # 【大脑写】验收结论
  python3 collect/supervisor.py --pause "原因" / --resume             # 【大脑】暂停/放开
"""
from __future__ import annotations
import argparse, hashlib, json, os, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_F = os.path.join(ROOT, "collect", "state.json")
WAKE_F = os.path.join(ROOT, "collect", "wake", "WAKE.json")
REPORT_F = os.path.join(ROOT, "collect", "pilot_report.json")
BLOCKED_F = os.path.join(ROOT, "collect", "blocked.json")
REPO = os.environ.get("GITHUB_REPOSITORY") or "ip9988001/world-map-data-33"
LABEL = "sentinel-alarm"
STALL_MIN = 240          # 超过这么久没结束 = 异常，但只报告不判死

# step -> (名字, 说明书, worker workflow)
STEPS = {
    "00": ("地基", "collect/steps/STEP-00.md", "collect-watchdog.yml"),
    "01": ("预检", "collect/steps/STEP-01.md", "collect-preflight.yml"),
    "02": ("试点 8 层", "collect/steps/STEP-02.md", "collect-pilot.yml"),
    "03": ("单州试跑 KS", "collect/steps/STEP-03.md", "collect-batch.yml"),
    "04": ("全州级放量", "collect/steps/STEP-04.md", "collect-batch.yml"),
    "05": ("县市碎片放量", "collect/steps/STEP-05.md", "collect-batch.yml"),
    "06": ("收工", "collect/steps/STEP-06.md", None),
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sh(args, timeout=120):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except Exception as e:
        return 1, "", str(e)


def api_json(path):
    rc, out, _ = sh(["gh", "api", path])
    if rc != 0:
        return {}
    try:
        return json.loads(out or "{}")
    except Exception:
        return {}


def load():
    with open(STATE_F, encoding="utf-8") as f:
        return json.load(f)


def save(st):
    os.makedirs(os.path.dirname(STATE_F), exist_ok=True)
    with open(STATE_F, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def mins(iso):
    try:
        t = datetime.strptime(iso.replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
        return (datetime.now(timezone.utc) - t).total_seconds() / 60
    except Exception:
        return 1e9


def used_minutes():
    """按 Actions 实际 run 时长累计（近 100 个 run），让额度闸门真生效。"""
    runs = api_json("repos/%s/actions/runs?per_page=100" % REPO).get("workflow_runs") or []
    tot = 0.0
    for r in runs:
        if r.get("status") != "completed":
            continue
        try:
            a = datetime.strptime(r["created_at"].replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
            b = datetime.strptime(r["updated_at"].replace("Z", "+0000"), "%Y-%m-%dT%H:%M:%S%z")
            tot += max((b - a).total_seconds() / 60.0, 0)
        except Exception:
            pass
    return int(tot)


def active_runs(wf=None):
    runs = api_json("repos/%s/actions/runs?per_page=30" % REPO).get("workflow_runs") or []
    out = []
    for r in runs:
        if r.get("status") not in ("queued", "in_progress", "pending"):
            continue
        if wf and (r.get("name") or "") not in (wf.replace(".yml", ""), wf) \
                and (r.get("path") or "").split("/")[-1] != wf:
            continue
        out.append(r)
    return out


# ---------------- 证据（只收事实，不下结论） ----------------
def evidence(st, step):
    ev = {"step": step, "at": now(), "facts": {}, "ask": []}
    wf = STEPS[step][2]

    runs = (api_json("repos/%s/actions/runs?per_page=30" % REPO).get("workflow_runs") or [])
    mine = [r for r in runs if (r.get("path") or "").split("/")[-1] == wf][:6]
    ev["facts"]["recent_runs"] = [
        {"n": r.get("run_number"), "id": r.get("id"), "status": r.get("status"),
         "conclusion": r.get("conclusion"), "at": r.get("created_at"),
         "duration_min": round((r.get("updated_at") and r.get("created_at") and
                                (mins(r.get("created_at")) - mins(r.get("updated_at")))) or 0, 1)}
        for r in mine]

    rels = api_json("repos/%s/releases?per_page=20" % REPO) or []
    ev["facts"]["releases"] = [
        {"tag": r.get("tag_name"), "at": r.get("created_at"),
         "assets": [{"name": a.get("name"), "bytes": a.get("size")} for a in (r.get("assets") or [])]}
        for r in rels[:12]]

    # 报告新鲜度（本地 checkout 里的那份）
    if os.path.exists(REPORT_F):
        raw = open(REPORT_F, "rb").read()
        try:
            d = json.loads(raw.decode("utf-8"))
        except Exception:
            d = {}
        ev["facts"]["report"] = {
            "sha": hashlib.sha1(raw).hexdigest()[:12],
            "mtime": datetime.fromtimestamp(os.path.getmtime(REPORT_F), timezone.utc)
                            .strftime("%Y-%m-%dT%H:%M:%SZ"),
            "layers": d.get("layers"), "with_rows": d.get("with_rows"),
            "worst_diff": d.get("worst_diff"), "total_rows": d.get("total_rows"),
            "failed": d.get("failed"),
            "per_layer": [{k: m.get(k) for k in ("id", "count", "rows", "parts", "diff", "elapsed_s", "err")}
                          for m in (d.get("detail") or [])],
        }
    else:
        ev["facts"]["report"] = None

    if os.path.exists(BLOCKED_F):
        try:
            ev["facts"]["blocked"] = json.load(open(BLOCKED_F, encoding="utf-8"))
        except Exception:
            ev["facts"]["blocked"] = None

    ev["facts"]["state"] = {"step": step, "last_run": st.get("last_run"),
                            "last_error": st.get("last_error"),
                            "budget": st.get("budget"),
                            "steps": st.get("steps")}

    # 要问大脑什么（是问题，不是结论）
    ev["ask"] = [
        f"STEP {step}（{STEPS[step][0]}）这一轮的结果，判通过还是不通过？依据在 evidence.report.per_layer 里",
        "不通过的话：是补跑哪一层，还是记 blocked 跳过继续往下走？",
        f"判完请写回账本：python3 collect/supervisor.py --review pass|fail --note \"...\"",
    ]
    return ev


def signature(ev):
    d = {"step": ev["step"],
         "runs": [(r["id"], r["status"], r["conclusion"]) for r in ev["facts"]["recent_runs"]],
         "rel": [(r["tag"], [(a["bytes"]) for a in r["assets"]]) for r in ev["facts"]["releases"]],
         "rep": (ev["facts"]["report"] or {}).get("sha"),
         "blocked": len((ev["facts"].get("blocked") or {}).get("items") or [])}
    return hashlib.sha1(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def post_issue(step, body, sig):
    title = f"【三仓 · 等大脑】STEP {step} {STEPS[step][0]} — 工人已停手，请判验收"
    rc, out, _ = sh(["gh", "issue", "list", "--repo", REPO, "--label", LABEL, "--state", "open",
                     "--json", "number,title,body"])
    try:
        for it in json.loads(out or "[]"):
            if title in (it.get("title") or ""):
                if sig in (it.get("body") or ""):
                    return it["number"], False          # 同一批证据，不重复刷
                sh(["gh", "issue", "comment", str(it["number"]), "--repo", REPO, "--body", body])
                return it["number"], True
    except Exception:
        pass
    sh(["gh", "label", "create", LABEL, "--repo", REPO, "--color", "d73a4a",
        "--description", "流水线叫醒/告警", "--force"])
    rc, out, _ = sh(["gh", "issue", "create", "--repo", REPO, "--label", LABEL,
                     "--title", title, "--body", body])
    num = out.strip().splitlines()[-1] if out.strip() else None
    return num, True


def wake(st, step, reason, dry=False):
    """叫醒大脑：落 WAKE.json + 开 Issue。同签名只叫一次。"""
    ev = evidence(st, step)
    ev["reason"] = reason
    sig = signature(ev)
    ev["signature"] = sig
    prev = (st.get("wake") or {}).get("signature")
    fresh = sig != prev

    body = "\n".join([
        f"## 工头叫醒（v2 · 只叫人，不判验收）",
        "",
        f"- 原因：**{reason}**",
        f"- 步号：STEP {step} {STEPS[step][0]}　说明书：`{STEPS[step][1]}`",
        f"- 证据：`collect/wake/WAKE.json`（签名 `{sig}`）",
        f"- 判定权：**在你**。工头不判、不推进、不点火。",
        "",
        "### 事实",
        "```json",
        json.dumps({k: ev["facts"][k] for k in ("recent_runs", "report") if k in ev["facts"]},
                   ensure_ascii=False)[:2500],
        "```",
        "",
        "### 要你回答",
    ] + [f"- {q}" for q in ev["ask"]])
    num = None
    if not dry:
        os.makedirs(os.path.dirname(WAKE_F), exist_ok=True)
        with open(WAKE_F, "w", encoding="utf-8") as f:
            json.dump(ev, f, ensure_ascii=False, indent=1)
        if fresh:
            num, _ = post_issue(step, body, sig)
        st["awaiting_brain"] = True
        st.setdefault("wake", {}).update({"signature": sig, "at": ev["at"],
                                          "reason": reason, "issue": num,
                                          "count": (st.get("wake") or {}).get("count", 0) + (1 if fresh else 0)})
        st["steps"].setdefault(step, {})["status"] = "in_review"
    print(json.dumps({"wake": reason, "signature": sig, "fresh": fresh, "issue": num,
                      "report": (ev["facts"].get("report") or {}).get("with_rows")}, ensure_ascii=False))
    return ev


# ---------------- 大脑的两个动作（只有大脑用） ----------------
def kick(step, layers=None, workers=None, dry=False):
    wf = STEPS[step][2]
    if not wf:
        print("该步没有工人 workflow"); return 1
    cmd = ["gh", "workflow", "run", wf, "--repo", REPO]
    if layers:
        cmd += ["-f", f"layers={layers}"]
    if workers:
        cmd += ["-f", f"workers={workers}"]
    if dry:
        print("DRY:", " ".join(cmd)); return 0
    rc, out, err = sh(cmd)
    st = load()
    st["status"] = "running"
    st["awaiting_brain"] = False
    st.setdefault("steps", {})[step] = {"status": "started", "at": now()}
    st["last_run"] = {"step": step, "run_id": None, "at": now(),
                      "trigger": "brain", "layers": layers or "all", "workers": workers}
    save(st)
    print(("✅ 已点火 " if rc == 0 else "❌ 点火失败 ") + f"{wf} rc={rc} {(err or '')[:120]}")
    return rc


def review(verdict, note, nxt=None, dry=False):
    st = load()
    step = st.get("current_step")
    if verdict not in ("pass", "fail"):
        print("verdict 只能是 pass / fail"); return 1
    st["awaiting_brain"] = False
    st.setdefault("brain_review", {}).update(
        {"at": now(), "step": step, "verdict": verdict, "note": note or ""})
    st.setdefault("steps", {}).setdefault(step, {})["status"] = "done" if verdict == "pass" else "failed"
    if verdict == "pass" and nxt:
        st["current_step"] = nxt
        st["status"] = "running"
        st.setdefault("steps", {}).setdefault(nxt, {})["status"] = "ready"
    elif verdict == "pass" and nxt is None:
        st["status"] = "finished"
    if not dry:
        save(st)
    print(json.dumps({"step": step, "verdict": verdict, "next": nxt, "saved": not dry}, ensure_ascii=False))
    return 0


def pause(reason, dry=False):
    st = load()
    st["status"] = "paused"
    st["paused_reason"] = reason
    st["paused_at"] = now()
    if not dry:
        save(st)
    print("paused:", reason)
    return 0


def resume(dry=False):
    st = load()
    st["status"] = "running"
    st["paused_reason"] = None
    st["paused_at"] = None
    if not dry:
        save(st)
    print("resumed")
    return 0


# ---------------- 巡逻（唯一的自动动作 = 叫醒） ----------------
def patrol(dry=False):
    st = load()
    rep = {"at": now(), "dry": dry, "acts": []}

    def say(k, v):
        rep["acts"].append({"k": k, "v": v})
        print(f"· {k}: {v}", file=sys.stderr)

    if st.get("status") in ("awaiting_go", "finished"):
        say("静止", f"status={st['status']}，不巡逻"); print(json.dumps(rep, ensure_ascii=False)); return 0
    if st.get("status") == "paused":
        say("暂停", st.get("paused_reason") or "paused"); print(json.dumps(rep, ensure_ascii=False)); return 0

    b = st.setdefault("budget", {})
    um = used_minutes()
    if um is not None:
        b["minutes_used"] = um
    b.setdefault("minutes_cap", 1800); b.setdefault("stop_ratio", 0.95)
    ratio = b["minutes_used"] / max(b["minutes_cap"], 1)
    say("额度", f"{b['minutes_used']}/{b['minutes_cap']} ({ratio:.0%})")
    if ratio >= b["stop_ratio"]:
        if not dry:
            st["status"] = "paused"; st["paused_reason"] = f"额度 {ratio:.0%} ≥ {b['stop_ratio']:.0%}"; save(st)
        say("动作", "额度耗尽 → paused")
        print(json.dumps(rep, ensure_ascii=False)); return 0

    step = st.get("current_step")
    wf = STEPS[step][2]
    act = active_runs(wf) if wf else []
    say("工人", f"{wf} 活着的 run = {len(act)}")

    if act:
        r = act[0]
        age = mins(r.get("created_at") or "")
        st.setdefault("last_run", {}).update(
            {"step": step, "run_id": r.get("id"), "at": r.get("created_at"), "script": wf})
        if not dry:
            save(st)
        if age > STALL_MIN:
            wake(st, step, f"run #{r.get('run_number')} 已跑 {age:.0f} 分钟 > {STALL_MIN}，可能卡死（不判死，交你定）", dry)
        else:
            say("状态", f"工人在干活（{age:.0f} 分钟），不打扰")
            print(json.dumps(rep, ensure_ascii=False)); return 0
    else:
        wake(st, step, "工人已停手：没有任何活着的 run，等大脑判验收", dry)

    if not dry:
        save(st)
    print(json.dumps(rep, ensure_ascii=False))
    return 0


# ---------------- v2 结构自检 ----------------
def entry_check():
    C = []
    # 只取「自检区之前」的源码：否则检查项自己的字面量会把检查项判死
    src = open(__file__, encoding="utf-8").read().split("# ---------------- v2 结构自检")[0]
    st = load()

    def add(n, name, ok, ev):
        C.append({"n": n, "name": name, "ok": bool(ok), "ev": ev})
    add(1, "工头不判验收", not any(k in src for k in ("def check_02_pilot", "worst_diff <", "with_rows >= ")),
        "源码里没有验收判据函数")
    add(2, "工头不自动推进", "TRIGGER[" not in src and "自动触发" not in src, "没有下一步自动点火表")
    add(3, "工头不写熔断", not any(k in src for k in ('"collapsed"', "fail_streak", "MAX_FAIL")), "无三振逻辑")
    add(4, "有叫醒落盘", "WAKE.json" in src and "awaiting_brain" in src, "collect/wake/WAKE.json")
    add(5, "有证据打包", all(k in src for k in ("recent_runs", "releases", "per_layer")),
        "runs/releases/report 三件证据")
    add(6, "同签名不重复叫", "signature(" in src and "fresh" in src, "按证据签名去重")
    add(7, "点火只能大脑下令", "def kick(" in src and "--kick" in src, "supervisor.py --kick")
    add(8, "验收只能大脑写", "def review(" in src and "--review" in src, "supervisor.py --review")
    add(9, "能暂停/放开", "def pause(" in src and "--resume" in src, "paused 语义可逆")
    add(10, "额度闸门", "stop_ratio" in src and "used_minutes" in src, "按 Actions 时长记账")
    add(11, "卡死不判死", "STALL_MIN" in src and "不判死" in src, f"{STALL_MIN} 分钟只报告")
    add(12, "工头不碰企微", "qyapi" not in src and "webhook" not in src.lower(), "无企微调用")
    add(13, "账本不含判断字段", not any(k in st for k in ("collapsed", "fail_streak", "attempts")),
        f"state.json keys={sorted(st)[:8]}…")
    add(14, "账本有 v2 字段", {"awaiting_brain", "brain_review", "last_run", "budget"} <= set(st),
        "awaiting_brain/brain_review/last_run/budget")
    add(15, "blocked.json 存在", os.path.exists(BLOCKED_F), "collect/blocked.json")
    add(16, "说明书齐全", len([f for f in os.listdir(os.path.join(ROOT, "collect", "steps"))
                               if f.startswith("STEP-")]) >= 7, "collect/steps/STEP-0x.md")
    add(17, "自检可验证", "--dry-run" in src and "--entry-check" in src, "dry-run / entry-check")
    add(18, "双闹钟都在", os.path.exists(os.path.join(ROOT, "ops", "patrol_kick.sh")) and
        os.path.exists(os.path.join(ROOT, ".github", "workflows", "collect-supervisor.yml")),
        "GitHub cron + 本机 cron")

    good = sum(1 for c in C if c["ok"])
    for c in C:
        print(("✅" if c["ok"] else "❌") + f" {c['n']:>2}. {c['name']} — {c['ev']}")
    print(f"\n{'READY' if good == len(C) else 'BLOCKED'}：{good}/{len(C)} 条通过")
    return 0 if good == len(C) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--entry-check", action="store_true")
    ap.add_argument("--kick", metavar="STEP")
    ap.add_argument("--layers")
    ap.add_argument("--workers", type=int)
    ap.add_argument("--review", choices=["pass", "fail"])
    ap.add_argument("--note")
    ap.add_argument("--next", dest="nxt")
    ap.add_argument("--pause", metavar="REASON")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if a.entry_check:
        return entry_check()
    if a.kick:
        return kick(a.kick, a.layers, a.workers, a.dry_run)
    if a.review:
        return review(a.review, a.note, a.nxt, a.dry_run)
    if a.pause:
        return pause(a.pause, a.dry_run)
    if a.resume:
        return resume(a.dry_run)
    return patrol(a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
