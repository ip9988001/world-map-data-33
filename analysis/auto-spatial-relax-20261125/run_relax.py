"""第 7 步复算脚本：E3/E7 放宽 → 三档 + 四档留底 + 挪动表，一条命令重跑全部交付物。

python3 analysis/auto-spatial-relax-20261125/run_relax.py            # 全量（约 90 秒）
python3 analysis/auto-spatial-relax-20261125/run_relax.py --e3-relax off   # 只放 E7（严格档仍 30 层）
python3 analysis/auto-spatial-relax-20261125/run_relax.py --strict-only    # 不重算参照池，只重分档

产物（本目录）：auto-recognized.csv / coord-evidence-relax.csv / e7-refpool-stats.csv /
e7-refpool-summary.json / summary.json / tier1-buckets.csv / tier1-{strict,e3_only,e7_only,both}.ids /
tier1-evidence.csv / template-unresolved-moves.csv / template-unresolved-unavailable.csv
"""
import argparse, json, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "analysis", "auto-spatial-relax-20261125")
STRICT = os.path.join(ROOT, "analysis", "auto-spatial-rerun-20261125")


def run(*cmd):
    print("+", " ".join(os.path.relpath(c, ROOT) if c.startswith("/") else c for c in cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit(f"FAILED rc={r.returncode}: {cmd}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--e3-relax", choices=("on", "off"), default="on")
    ap.add_argument("--per-layer-cap", type=int, default=None)
    ap.add_argument("--strict-only", action="store_true")
    args = ap.parse_args()
    if not args.strict_only:
        run(sys.executable, "sandbox/e7_refpool.py", "--outdir", OUT, *(
            ["--per-layer-cap", str(args.per_layer_cap)] if args.per_layer_cap else []))
    run(sys.executable, "sandbox/tier_relax.py", "--strict", STRICT, "--outdir", OUT, "--e3-relax", args.e3_relax)
    rp = os.path.join(OUT, "e7-refpool-summary.json")
    if os.path.isfile(rp):                       # 把参照池统计并进 summary.json（报告里所有数都能从这里复算）
        s = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
        s["e7_refpool"] = json.load(open(rp, encoding="utf-8"))
        json.dump(s, open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    s = json.load(open(os.path.join(OUT, "summary.json"), encoding="utf-8"))
    print(json.dumps({"e3_relax": s["e3_relax_default"], "tiers": {k: v["layers"] for k, v in s["tiers"].items()},
                      "buckets": {k: v["layers"] for k, v in s["buckets"].items()},
                      "moves": {k: v["layers"] for k, v in s["moves"].items()},
                      "closed": s["checks"]["tiers_closed"] and s["checks"]["moves_closed"]
                      and s["checks"]["buckets_equal_tier1"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
