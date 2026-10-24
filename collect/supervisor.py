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
import argparse, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_F = os.path.join(ROOT, "collect", "state.json")
WAKE_F = os.path.join(ROOT, "collect", "wake", "WAKE.json")
REPORT_F = os.path.join(ROOT, "collect", "pilot_report.json")
BLOCKED_F = os.path.join(ROOT, "collect", "blocked.json")
REPO = os.environ.get("GITHUB_REPOSITORY") or "ip9988001/world-map-data-33"
LABEL = "sentinel-alarm"
STALL_MIN = 240
JOB_RUNS_MAX = 15        # 预算严格算法只看最近 15 个 run（每 run 1~3 次 API）          # 超过这么久没结束 = 异常，但只报告不判死

# ★ 唯一参数源：collect/steps.json。工头不再自带一份参数副本。
STEPS_JSON = os.path.join(ROOT, "collect", "steps.json")


def cfg():  # ponytail: 每次现读，7 步 × 每轮一次，代价可忽略；要缓存时加 mtime 判定
    with open(STEPS_JSON, encoding="utf-8") as f:
        return json.load(f)


def steps_map():
    """step -> (名字, 说明书, worker workflow)，全部来自 steps.json。"""
    out = {}
    for k, s in (cfg().get("steps") or {}).items():
        sup = s.get("supervise") or {}
        out[k] = (s.get("title") or k,
                  sup.get("doc") or f"collect/steps/STEP-{k}.md",
                  sup.get("wf") or f"worker-{k}.yml")
    return out


def profile_of(step):
    """单步工头的全部差异：卡死阈值 / 叫醒话术 / 命令模板 / 证据清单 / 判据卡。"""
    s = (cfg().get("steps") or {}).get(step) or {}
    sup = s.get("supervise") or {}
    title, doc, wf = STEPS.get(step, (s.get("title") or step, None, None))
    return {"step": step, "title": title, "doc": doc, "wf": wf,
            "stall_min": int(sup.get("stall_min") or STALL_MIN),
            "evidence": list(s.get("evidence") or []),
            "wake_reason": sup.get("wake_reason") or f"{title}：工人已停手，等大脑判验收",
            "cmds": list(sup.get("cmds") or []),
            "accept": dict(s.get("accept") or {}),
            "tag": s.get("tag"), "kind": s.get("kind")}


STEPS = steps_map()


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
    """累加 job 分钟（不是 run 墙钟），并且**结算过的 run 只算一次**。

    2026-10-24 两次修：
      ① 老实现用 run 的 created→updated，111 个并行 job 的 run 墙钟只有 ~20 分钟，
         job 分钟和却是 52 分钟 —— 并行度越高，闸门越乐观。
      ② 只扫最近 15 个 run 会「漏账」：跑得越多，账越小（实测从 475 掉到 363）。
         现在用 settled_runs 水位线，只结算没算过的 run，累计值写回账本。
    """
    st = load()
    b = st.setdefault("budget", {})
    seen = set(b.get("settled_runs") or [])
    total = float(b.get("settled_min") or 0)
    runs = api_json("repos/%s/actions/runs?per_page=50" % REPO).get("workflow_runs") or []
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    fresh = 0
    for r in runs:
        if r.get("status") != "completed" or r.get("id") in seen:
            continue
        for page in (1, 2, 3):
            js = api_json("repos/%s/actions/runs/%s/jobs?per_page=100&page=%d"
                          % (REPO, r.get("id"), page)).get("jobs") or []
            for j in js:
                a, c2 = j.get("started_at"), j.get("completed_at")
                if not (a and c2):
                    continue
                try:
                    total += max((datetime.strptime(c2, fmt) - datetime.strptime(a, fmt)).total_seconds() / 60.0, 0)
                except Exception:
                    pass
            if len(js) < 100:
                break
        seen.add(r.get("id"))
        fresh += 1
    if fresh:
        b["settled_runs"] = sorted(seen)[-500:]
        b["settled_min"] = round(total, 1)
        b["minutes_used"] = int(total)
        save(st)
    return int(total)


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
# ★ steps.json 的 evidence 清单是需求，这里是供给：缺哪个就记进 missing，绝不假装收到。
def _sources(st, step):
    """一次性取原始料（runs/releases/report/blocked/state），后面的收集器都从它派生。"""
    wf = STEPS.get(step, (None, None, None))[2]
    runs = (api_json("repos/%s/actions/runs?per_page=30" % REPO).get("workflow_runs") or [])
    mine = [r for r in runs if wf and (r.get("path") or "").split("/")[-1] == wf][:6]
    # ★ 只看 20 个 release 时，49 层的放量步骤只能看到 20 层证据 → 分页拉全，再按本步 tag 过滤
    reps = []
    for page in (1, 2, 3):
        batch = api_json("repos/%s/releases?per_page=100&page=%d" % (REPO, page)) or []
        reps += batch
        if len(batch) < 100:
            break
    prefix = "collect-step%s-" % step
    only = [r for r in reps if (r.get("tag_name") or "").startswith(prefix)]
    # 本步还没产出 release 时保持空（不能拿上一步的资产冒充本步证据）
    reps = only if only else []

    rep = None
    if os.path.exists(REPORT_F):
        raw = open(REPORT_F, "rb").read()
        try:
            d = json.loads(raw.decode("utf-8"))
        except Exception:
            d = {}
        rep = {
            "sha": hashlib.sha1(raw).hexdigest()[:12],
            # ★ 不能用文件 mtime：那是 runner checkout 的时间，永远「刚刚」，会骗人。
            #   用 worker 自己写进 manifest 的 at 字段，才是真实采集时间。
            "freshest": max([(m.get("at") or "") for m in (d.get("detail") or [])], default=""),
            "layers": d.get("layers"), "with_rows": d.get("with_rows"),
            "worst_diff": d.get("worst_diff"), "total_rows": d.get("total_rows"),
            "failed": d.get("failed"),
            "per_layer": [{k: m.get(k) for k in ("id", "count", "rows", "parts", "diff", "elapsed_s", "err")}
                          for m in (d.get("detail") or [])],
        }

    blk = None
    if os.path.exists(BLOCKED_F):
        try:
            blk = json.load(open(BLOCKED_F, encoding="utf-8"))
        except Exception:
            blk = None

    return {
        "runs": [{"n": r.get("run_number"), "id": r.get("id"), "status": r.get("status"),
                  "conclusion": r.get("conclusion"), "at": r.get("created_at"),
                  "duration_min": round((mins(r.get("created_at") or "") - mins(r.get("updated_at") or "")) or 0, 1)}
                 for r in mine],
        "releases": [{"tag": r.get("tag_name"), "at": r.get("created_at"),
                      "assets": [{"name": a.get("name"), "bytes": a.get("size")} for a in (r.get("assets") or [])]}
                     for r in (reps or [])[:40]],   # 聚合够用即可，正文 2500 字会截断
        "report": rep,
        "blocked": blk,
        "state": {"step": step, "last_run": st.get("last_run"), "last_error": st.get("last_error"),
                  "budget": st.get("budget"), "steps": st.get("steps")},
    }


def _ck_assets(S):
    """checkpoint 只给聚合 + 抽样清单：49 层全列会把叫醒简报撑爆，聚合数字才是判据要的。"""
    items = [{"tag": r["tag"], "name": a["name"], "bytes": a["bytes"]}
             for r in S["releases"] for a in (r.get("assets") or [])
             if (a.get("name") or "").endswith("-checkpoint.json")]
    units = sum(1 for r in S["releases"] for a in (r.get("assets") or [])
                if re.search(r"-u\d{5}\.tar\.gz$", a.get("name") or ""))
    return {"layers_with_checkpoint": len(items),
            "releases_seen": len(S["releases"]),
            "units_uploaded": units,
            "bytes": sum(i["bytes"] or 0 for i in items),
            "sample": items[:5]}


def _short_units(S):
    return [{"id": m.get("id"), "err": m.get("err"), "rows": m.get("rows")}
            for m in ((S["report"] or {}).get("per_layer") or [])
            if str(m.get("err") or "").startswith("short:")]


def _unit_errors(S):
    return [{"id": m.get("id"), "err": m.get("err")}
            for m in ((S["report"] or {}).get("per_layer") or [])
            if m.get("err") and not str(m.get("err")).startswith("short:")]


def _layer_plan(S):
    f = os.path.join(ROOT, "collect", "layer_plan.csv")
    m = (((S["state"] or {}).get("steps") or {}).get("01") or {}).get("metrics") or {}
    return {"file": "collect/layer_plan.csv", "exists": os.path.exists(f),
            "rows": m.get("rows"), "plan_empty": m.get("plan_empty")}


def _count_rate(S):
    m = (((S["state"] or {}).get("steps") or {}).get("01") or {}).get("metrics") or {}
    return {"count_rate": m.get("count_rate")}


def _file_ev(rel):
    def f(S):
        p = os.path.join(ROOT, rel)
        return {"file": rel, "exists": os.path.exists(p),
                "bytes": (os.path.getsize(p) if os.path.exists(p) else 0)}
    return f


# steps.json 里能写哪些 evidence 名字，全在这张表里
COLLECTORS = {
    "recent_runs": lambda S: S["runs"],
    "releases": lambda S: S["releases"],
    "report": lambda S: S["report"],
    "blocked": lambda S: S["blocked"],
    "state": lambda S: S["state"],
    "checkpoint": _ck_assets,
    "short_units": _short_units,
    "unit_errors": _unit_errors,
    "layer_plan.csv": _layer_plan,
    "count_rate": _count_rate,
    "selftest": lambda S: {"entry_check": "python3 collect/supervisor.py --entry-check"},
    "unit_tests": _file_ev("collect/tests/test_worker_core.py"),
    "FINAL_REPORT.md": _file_ev("collect/reports/FINAL_REPORT.md"),
    "paused": lambda S: {"status": (load().get("status")), "paused_reason": load().get("paused_reason")},
}


def evidence(st, step):
    prof = profile_of(step)
    want = prof.get("evidence") or ["recent_runs", "releases", "report", "state"]
    S = _sources(st, step)
    ev = {"step": step, "at": now(), "want": want, "facts": {}, "missing": [], "profile": prof}
    for k in want:
        f = COLLECTORS.get(k)
        if f is None:
            ev["missing"].append(k)          # 名字拼错或还没有收集器 → 明确报缺口
            continue
        try:
            ev["facts"][k] = f(S)
        except Exception as e:
            ev["missing"].append(f"{k}({str(e)[:60]})")

    rep = S["report"] or {}
    ev["ask"] = [
        f"STEP {step}（{prof['title']}）这一轮，判通过还是不通过？判据卡（steps.json accept）：{json.dumps(prof.get('accept') or {}, ensure_ascii=False)}",
        f"依据：evidence.report.per_layer / evidence.checkpoint / evidence.short_units（缺的键见 missing={ev['missing']}）",
        "不通过的话：补跑哪一层，还是记 blocked 跳过继续往下走？",
        f"判完写回账本：python3 collect/supervisor.py --review pass|fail --note \"...\"",
    ]
    return ev


def signature(ev):
    """同一批证据只叫醒一次。state 含 budget（每轮都变）→ 排除，否则去重永远失效。"""
    keep = ("recent_runs", "releases", "report", "blocked", "checkpoint", "short_units", "unit_errors")
    d = {"step": ev["step"], "facts": {k: v for k, v in ev["facts"].items() if k in keep},
         "missing": sorted(ev.get("missing") or [])}
    return hashlib.sha1(json.dumps(d, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()[:16]


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


def wake(st, step, reason, dry=False, profile=None):
    """叫醒大脑：落 WAKE.json + 开 Issue。同签名只叫一次。"""
    ev = evidence(st, step)
    ev["reason"] = reason
    prof = dict(profile or profile_of(step))
    ev["profile"] = {k: prof.get(k) for k in ("step", "title", "stall_min", "cmds", "evidence", "accept", "doc", "tag")}
    sig = signature(ev)
    ev["signature"] = sig
    prev = (st.get("wake") or {}).get("signature")
    fresh = sig != prev

    title_, doc_, wf_ = STEPS.get(step, (step, None, None))
    acc = prof.get("accept") or {}
    cmds = prof.get("cmds") or []
    body = "\n".join([
        "## 工头叫醒（v2 · 只叫人，不判验收）",
        "",
        f"- 原因：**{reason}**",
        f"- 步号：**STEP {step} {title_}**　类型：`{prof.get('kind')}`",
        "",
        "### 你要读的东西（路径已写死，别去找）",
        f"- 说明书：`{doc_}`",
        f"- 参数与判据卡：`collect/steps.json` → `steps.{step}`（accept = `{json.dumps(acc, ensure_ascii=False)}`）",
        f"- 证据原件：`{WAKE_F}`（绝对路径）",
        f"- 工人 workflow：`.github/workflows/{wf_}`",
        "",
        "### 事实（工头只收事实，不写合格/不合格）",
        "```json",
        json.dumps({k: ev["facts"][k] for k in ev["facts"] if k != "state"}, ensure_ascii=False)[:2500],
        "```",
        "",
        f"### 证据缺口（steps.json 要了但没收到的键）：{('`' + '`, `'.join(ev['missing']) + '`') if ev.get('missing') else '无'}",
        "",
        "### 命令模板（照抄，改参数就行）",
    ] + [f"```bash\npython3 collect/supervisor.py {c}\n```" for c in cmds] + [
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
def kick(step, layers=None, workers=None, dry=False, max_layers=None, offset=None, size=None):
    wf = STEPS[step][2]
    if not wf:
        print("该步没有工人 workflow"); return 1
    cmd = ["gh", "workflow", "run", wf, "--repo", REPO]
    if layers:
        cmd += ["-f", f"layers={layers}"]
    if workers:
        cmd += ["-f", f"workers={workers}"]
    if max_layers:
        cmd += ["-f", f"max_layers={max_layers}"]
    if offset is not None:
        cmd += ["-f", f"offset={offset}"]
    if size is not None:
        cmd += ["-f", f"size={size}"]
    if dry:
        print("DRY:", " ".join(cmd)); return 0
    rc, out, err = sh(cmd)
    st = load()
    st["status"] = "running"
    st["awaiting_brain"] = False
    st.setdefault("steps", {})[step] = {"status": "started", "at": now()}
    st["last_run"] = {"step": step, "run_id": None, "at": now(),
                      "trigger": "brain", "layers": layers or "all", "workers": workers}
    st["paused_reason"] = None
    (st.get("wake") or {}).pop("closed", None)   # 重新开跑 = 上一轮 fail 的关单作废
    save(st)
    print(("✅ 已点火 " if rc == 0 else "❌ 点火失败 ") + f"{wf} rc={rc} {(err or '')[:120]}")
    return rc


def review(verdict, note, nxt=None, dry=False):
    """大脑写验收结论。pass 才可能推进；fail 必须把流程停住，不许同一批证据反复叫醒。"""
    st = load()
    step = st.get("current_step")
    if verdict not in ("pass", "fail"):
        print("verdict 只能是 pass / fail"); return 1
    st["awaiting_brain"] = False
    st.setdefault("brain_review", {}).update(
        {"at": now(), "step": step, "verdict": verdict, "note": note or ""})
    st.setdefault("steps", {}).setdefault(step, {})["status"] = "done" if verdict == "pass" else "failed"
    wk = st.setdefault("wake", {})

    if verdict == "pass" and nxt:
        st["current_step"] = nxt
        st["status"] = "running"
        st["paused_reason"] = None
        st.setdefault("steps", {}).setdefault(nxt, {})["status"] = "ready"
        wk.pop("closed", None)
    elif verdict == "pass" and nxt is None:
        st["status"] = "finished"
        st["paused_reason"] = None
        wk.pop("closed", None)
    else:
        # ★ fail 闭环：停在 awaiting_go，巡逻一律静止；同签名证据不再开 Issue。
        #   要重跑就 --kick（点火会把 status 改回 running 并清掉 closed）。
        st["status"] = "awaiting_go"
        st["paused_reason"] = note or f"STEP {step} 验收不通过，等大脑给指令"
        wk["closed"] = {"at": now(), "verdict": "fail", "step": step, "note": note or "",
                        "signature": wk.get("signature")}
        st.setdefault("steps", {})[step].update({"status": "failed", "fail_reason": (note or "")[:300]})

    if not dry:
        save(st)
    print(json.dumps({"step": step, "verdict": verdict, "next": nxt, "status": st["status"],
                      "saved": not dry}, ensure_ascii=False))
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
def patrol(dry=False, step=None, profile=None):
    profile = profile or {}
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
    b.setdefault("minutes_used", 0)          # ★ 缺字段时 gh api 失败会直接 KeyError，工头整轮崩掉
    b.setdefault("minutes_cap", 1800); b.setdefault("stop_ratio", 0.95)
    ratio = b["minutes_used"] / max(b["minutes_cap"], 1)
    say("额度", f"{b['minutes_used']}/{b['minutes_cap']} ({ratio:.0%})")
    if ratio >= b["stop_ratio"]:
        if not dry:
            st["status"] = "paused"; st["paused_reason"] = f"额度 {ratio:.0%} ≥ {b['stop_ratio']:.0%}"; save(st)
        say("动作", "额度耗尽 → paused")
        print(json.dumps(rep, ensure_ascii=False)); return 0

    step = step or st.get("current_step")
    stall = int(profile.get("stall_min") or STALL_MIN)
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
        if age > stall:
            wake(st, step, f"run #{r.get('run_number')} 已跑 {age:.0f} 分钟 > {stall}，可能卡死（不判死，交你定）", dry, profile)
        else:
            say("状态", f"工人在干活（{age:.0f} 分钟），不打扰")
            print(json.dumps(rep, ensure_ascii=False)); return 0
    else:
        wake(st, step, profile.get("wake_reason") or "工人已停手：没有任何活着的 run，等大脑判验收", dry, profile)

    if not dry:
        save(st)
    print(json.dumps(rep, ensure_ascii=False))
    return 0


def patrol_step(profile, dry=False):
    """单步工头入口：7 个 supervisors/step_0X.py 各自调它，差异全在 profile 里。"""
    return patrol(dry=dry, step=profile.get("step"), profile=profile)


def tick(dry=False):
    """cron 的唯一入口：读账本当前步 → 交给对应的单步工头。"""
    st = load()
    step = st.get("current_step") or "02"
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        mod = __import__("supervisors.step_%s" % step, fromlist=["run"])
    except Exception as e:
        print(json.dumps({"tick": "error", "step": step, "err": str(e)[:200]}, ensure_ascii=False))
        return 1
    return mod.run(dry)


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
    d = cfg()
    S = d.get("steps") or {}
    want_docs = {"STEP-%s.md" % k for k in S}
    have_docs = set(os.listdir(os.path.join(ROOT, "collect", "steps")))
    add(16, "说明书齐全", want_docs <= have_docs,
        f"{len(want_docs)} 步说明书齐（steps.json 有几步就要几份）")
    add(17, "自检可验证", "--dry-run" in src and "--entry-check" in src, "dry-run / entry-check")
    add(18, "双闹钟都在", os.path.exists(os.path.join(ROOT, "ops", "patrol_kick.sh")) and
        os.path.exists(os.path.join(ROOT, ".github", "workflows", "collect-supervisor.yml")),
        "GitHub cron + 本机 cron")

    # ---- 19~24：v2.1 本轮新增（steps.json 单源 / 清单驱动取证 / 简报四件套 / fail 闭环）----
    d = cfg()
    S = d.get("steps") or {}
    nums = sorted(int(k) for k in S if str(k).isdigit())
    contiguous = nums == list(range(0, len(nums))) and len(nums) == len(S)
    add(19, "steps.json 是唯一参数源", d.get("schema") == "v2.1" and contiguous and len(S) >= 7,
        f"schema={d.get('schema')} steps={len(S)} 连续={contiguous}")

    profs = []
    for k in S:
        fp = os.path.join(ROOT, "collect", "supervisors", "step_%s.py" % k)
        profs.append(open(fp, encoding="utf-8").read() if os.path.exists(fp) else "")
    add(20, "每步一份工头且只报步号", len(profs) == len(S) and len(S) >= 7
        and all("core.profile_of(" in t for t in profs) and not any("PROFILE = {" in t for t in profs),
        f"{len(profs)}/{len(S)} 份工头 ← steps.json")

    miss = {k: [e for e in (s.get("evidence") or []) if e not in COLLECTORS] for k, s in S.items()}
    miss = {k: v for k, v in miss.items() if v}
    add(21, "证据需求都有收集器", not miss, f"steps.json evidence × COLLECTORS：缺口={miss or '无'}")

    fat = {k: [f for f in ("stall_min", "wake_reason", "cmds", "doc", "wf")
               if not (s.get("supervise") or {}).get(f)] for k, s in S.items()}
    fat = {k: v for k, v in fat.items() if v}
    add(22, "每步 supervise 五项齐", not fat, f"缺项={fat or '无'}")

    add(23, "叫醒简报四件套", all(t in src for t in ("说明书：", "判据卡", "命令模板")),
        "说明书路径 / 判据卡(accept) / 命令模板 / WAKE 绝对路径")

    add(24, "fail 有闭环", '"closed"' in src and "awaiting_go" in src and 'pop("closed"' in src,
        "fail→awaiting_go + 关单；--kick 解封")

    rc, out, _ = sh([sys.executable, os.path.join(ROOT, "collect", "check_docs.py"), "--json"])
    try:
        docs = json.loads(out or "{}")
    except Exception:
        docs = {}
    add(25, "判据卡与 steps.json 一致", rc == 0 and docs.get("ready") is True,
        f"check_docs.py → {docs.get('docs')} 份判据卡 / {len(docs.get('problems') or [])} 条问题")

    good = sum(1 for c in C if c["ok"])
    for c in C:
        print(("✅" if c["ok"] else "❌") + f" {c['n']:>2}. {c['name']} — {c['ev']}")
    print(f"\n{'READY' if good == len(C) else 'BLOCKED'}：{good}/{len(C)} 条通过")
    return 0 if good == len(C) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--tick", action="store_true", help="cron 入口：按当前步分派到 supervisors/step_0X.py")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--entry-check", action="store_true")
    ap.add_argument("--kick", metavar="STEP")
    ap.add_argument("--layers")
    ap.add_argument("--workers", type=int)
    ap.add_argument("--max-layers", type=int, help="灰度：只跑前 N 层（steps.json gate.gray_layers）")
    ap.add_argument("--offset", type=int, help="批量游标起点（STEP-05 分批）")
    ap.add_argument("--size", type=int, help="本批层数（STEP-05 分批）")
    ap.add_argument("--review", choices=["pass", "fail"])
    ap.add_argument("--note")
    ap.add_argument("--next", dest="nxt")
    ap.add_argument("--pause", metavar="REASON")
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    if a.entry_check:
        return entry_check()
    if a.tick:
        return tick(a.dry_run)
    if a.kick:
        return kick(a.kick, a.layers, a.workers, a.dry_run, a.max_layers, a.offset, a.size)
    if a.review:
        return review(a.review, a.note, a.nxt, a.dry_run)
    if a.pause:
        return pause(a.pause, a.dry_run)
    if a.resume:
        return resume(a.dry_run)
    return patrol(a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
