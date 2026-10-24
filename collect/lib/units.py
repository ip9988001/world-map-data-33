# -*- coding: utf-8 -*-
"""单元级断点续传的底座：检查点 / 进度心跳 / 已完成记录 / 清理。

从 pilot.py 抽出，改成「显式参数」而不是读模块全局 —— 7 个工人入口各自
有自己的 outbase/进度目录时，不会互相污染。
"""
import json
import os
import time


def TS():
    """统一时间戳格式（UTC ISO8601，秒级）"""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ckpt_path(outbase, cid):
    return os.path.join(outbase, cid, "_checkpoint.json")


def save_ckpt(ck, outbase, cid):
    p = ckpt_path(outbase, cid)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(ck, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)


def load_ckpt(plan_hash, outbase, cid, url, ver):
    p = ckpt_path(outbase, cid)
    if not os.path.exists(p):
        return None
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception:
        return None
    if d.get("ver") != ver or d.get("plan_hash") != plan_hash or d.get("url") != url:
        return None          # 切分方案变了 → 旧检查点作废，绝不硬续
    return d


def write_progress(prog, outbase, prog_dir):
    os.makedirs(prog_dir, exist_ok=True)
    prog["ts"] = TS()
    d = os.path.join(outbase, prog["id"])
    prog["parts"] = len([f for f in os.listdir(d) if f.endswith(".gz")]) if os.path.isdir(d) else 0
    p = os.path.join(prog_dir, prog["id"] + ".json")
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        json.dump(prog, f, ensure_ascii=False, indent=1)
    os.replace(p + ".tmp", p)
    return p


def purge(files):
    for f in files:
        try:
            os.remove(f)
        except Exception:
            pass


def record_unit(ck, idx, rows, files):
    ck.setdefault("unit_rows", {})[str(idx)] = rows
    ck.setdefault("unit_files", {})[str(idx)] = [os.path.basename(f) for f in files]
    ck.setdefault("done_units", [])
    if idx not in ck["done_units"]:
        ck["done_units"].append(idx)
    ck["done_units"].sort()
