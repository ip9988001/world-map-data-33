"""E7 扩参照源（沙盒）：把本地全表里「门牌 + 街名 + 坐标」齐全的行拉进同址投票参照池。

判据一字不改：同址跨源 >max_addr_conflict_m(300m) 记冲突、可比行 n_cmp<min_cmp_rows(3) 记 unknown、
冲突占比 >max_conflict_share(0.10) 记 hit；只换「跟谁比」——除 738,174 行坐标样本外，
再加本地全表（dist/intake-full/layers/*/addr.*.ndjson.gz）每层前 per_layer_cap 行。
取样是**采样不是全量**：每层取到的行数、是否被截断、跳过的层与原因全部落进 e7-refpool-stats.csv。

用法：python3 sandbox/e7_refpool.py --outdir analysis/auto-spatial-relax-20261125 [--per-layer-cap 2000]
"""
import argparse, collections, csv, glob, gzip, json, math, os, re, sys, time, yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sandbox.coord_evidence import (FIELDS, SUFFIX, THRESHOLDS, addr_key, roles_of,  # noqa: E402
                                    street_norm)

SAMPLES = os.environ.get("COORD_SAMPLES") or os.path.join(ROOT, "analysis", "coord-samples-20261124", "samples")
LOCAL = os.environ.get("INTAKE_FULL") or "/data/workspace/world-map-data-33/dist/intake-full"
POOL_COLS = ("layer,url,state,pool_rows,pool_keyed,capped,skip_reason,own_rows_keyed,n_cmp,"
             "n_cmp_sample,n_conflict,e7").split(",")
NUM_RE = re.compile(r"[^0-9A-Za-z-]")


def thresholds():
    doc = yaml.safe_load(open(THRESHOLDS, encoding="utf-8"))
    return ({k: v["value"] for k, v in doc["e7"].items()},
            {k: v["value"] for k, v in doc["e7_refpool"].items()})


def strip_type(s):
    """street_full 去掉尾部街名类型词，与 street_norm 的 SUFFIX 全称化配套（WINDY HILL Pl → WINDY HILL）。"""
    w = re.findall(r"[a-z0-9]+", (s or "").lower())
    while len(w) > 1 and w[-1] in SUFFIX:
        w.pop()
    return " ".join(w)


def pool_key(d):
    """本地全表行 → 同址键；门牌/街名/州缺任一项返回空串（不猜、不补）。"""
    n = NUM_RE.sub("", str(d.get("house_number") or ""))
    s = d.get("street_name") or strip_type(d.get("street_full"))
    st = (d.get("state_abbr") or "").strip()
    return f"{st}|{n}|{street_norm(s)}|{d.get('zip5') or ''}" if (n and s and st) else ""


def load_local_pool(cap):
    """逐层取前 cap 行；返回 rows / layer_stats / layer→url。只读，不改本地全表一个字节。"""
    rows, stats, urls, state_of = [], {}, {}, {}
    for p in sorted(glob.glob(os.path.join(LOCAL, "layers", "*", "addr.*.ndjson.gz"))):
        layer = os.path.basename(os.path.dirname(p))
        n = bad = keyed = 0
        try:
            with gzip.open(p, "rt") as fh:
                for line in fh:
                    if n >= cap:
                        break
                    try:
                        d = json.loads(line)
                    except ValueError:
                        bad += 1
                        continue
                    n += 1
                    urls.setdefault(layer, d.get("src_layer_url") or "")
                    state_of.setdefault(layer, d.get("state_abbr") or "")
                    k = pool_key(d)
                    lon, lat = d.get("longitude"), d.get("latitude")
                    if k and isinstance(lon, (int, float)) and isinstance(lat, (int, float)):
                        rows.append((layer, k, float(lon), float(lat)))
                        keyed += 1
        except (OSError, EOFError):
            stats[layer] = {"layer": layer, "pool_rows": 0, "pool_keyed": 0, "capped": "", "skip_reason": "gz 读取失败"}
            continue
        stats[layer] = {"layer": layer, "state": state_of.get(layer, ""), "pool_rows": n, "pool_keyed": keyed,
                        "capped": "1" if n >= cap else "", "skip_reason": f"{bad} 行 JSON 解析失败" if bad else "",
                        "own_rows_keyed": keyed, "n_cmp": "", "n_cmp_sample": "", "n_conflict": "", "e7": "pending"}
    return rows, stats, urls


def load_samples(ROLES):
    """坐标样本 → 每 url 的自身行（只保留有同址键的）；键归一与第 5 步完全同一函数。"""
    own, urls, n = collections.defaultdict(list), collections.defaultdict(set), 0
    for p in sorted(glob.glob(os.path.join(SAMPLES, "*.csv"))):
        for r in csv.DictReader(open(p, encoding="utf-8")):
            n += 1
            u = r["layer_url"] or f"local:{r['layer_id']}"
            urls[u].add(r["state"])
            k = addr_key(json.loads(r["addr_fields_json"] or "{}"), ROLES, r["state"])
            if k:
                own[u].append((k, float(r["lon"]), float(r["lat"])))
    return own, urls, n


def dist_m(lon, lat, cosf, o):
    return ((lon - o[1]) * 111320.0 * cosf) ** 2 + ((lat - o[2]) * 110540.0) ** 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.join(ROOT, "analysis", "auto-spatial-relax-20261125"))
    ap.add_argument("--per-layer-cap", type=int, default=None)
    ap.add_argument("--max-cmp", type=int, default=None)
    args = ap.parse_args()
    e7t, rpt = thresholds()
    cap = args.per_layer_cap if args.per_layer_cap is not None else int(rpt["per_layer_cap"])
    max_cmp = args.max_cmp if args.max_cmp is not None else int(rpt["max_cmp_per_row"])
    t0 = time.time()
    pool, pstats, purls = load_local_pool(cap)
    own, sample_states, n_sample_rows = load_samples(roles_of())
    print(f"pool rows={len(pool)} layers={len(pstats)} sample_rows={n_sample_rows} "
          f"sample_urls={len(own)} secs={round(time.time() - t0, 1)}")

    index = collections.defaultdict(list)   # 同址键 → [(src, lon, lat)]
    for layer, k, lon, lat in pool:
        index[k].append((purls.get(layer) or f"local:{layer}", lon, lat))
    for u, rows in own.items():
        for k, lon, lat in rows:
            index[k].append((u, lon, lat))
    for k in index:
        index[k].sort()

    pool_by_url = collections.Counter(purls.get(layer) or f"local:{layer}" for layer, _k, _x, _y in pool)
    own_all = collections.defaultdict(list)   # url → 自身行（样本 + 本层本地全表）
    for u, rows in own.items():
        own_all[u].extend((k, lon, lat, "sample") for k, lon, lat in rows)
    for layer, k, lon, lat in pool:
        own_all[purls.get(layer) or f"local:{layer}"].append((k, lon, lat, "local"))

    out, unverifiable, checked = [], [], 0
    for u in sorted(set(own_all) | set(sample_states)):
        states = sample_states.get(u) or set()
        rows = own_all.get(u, [])
        cmp_n = conf = cmp_s = 0
        for k, lon, lat, src in rows:
            others = [o for o in index[k] if o[0] != u]
            if not others:
                continue
            cosf = math.cos(math.radians(lat))
            d = min(dist_m(lon, lat, cosf, o) for o in others[:max_cmp]) ** 0.5
            cmp_n += 1
            if src == "sample":
                cmp_s += 1
            if d > e7t["max_addr_conflict_m"]:
                conf += 1
        n_samp = sum(1 for r in rows if r[3] == "sample")
        m = {"url": u, "state_scope": (sorted(states)[0] if states else ""), "n_addr_rows": len(rows) or n_samp,
             "n_cmp": cmp_n, "n_cmp_sample": cmp_s, "n_conflict": conf,
             "conflict_share": round(conf / cmp_n, 4) if cmp_n else "", "n_coords": n_samp}
        if not len(rows):
            m.update(e7="unknown", e7_detail="本层无『门牌+街名+坐标』齐全的行（样本 0 行、本地全表无 addr 表）→ 无同址可比")
            unverifiable.append(u)
        elif cmp_n < e7t["min_cmp_rows"]:
            m.update(e7="unknown", e7_detail=f"跨源同址可比值 n_cmp={cmp_n} < min_cmp_rows={e7t['min_cmp_rows']}"
                                             f"（参照池已含本地全表 {len(rows) - n_samp} 行仍投不出票）")
        else:
            m.update(e7="hit" if m["conflict_share"] > e7t["max_conflict_share"] else "clear",
                     e7_detail=(f"参照池=坐标样本+本地全表；自身行 {len(rows)}（样本 {n_samp} + 本地 {len(rows) - n_samp}），"
                                f"同址可比 {cmp_n} 行、冲突 {conf} 行（>{int(e7t['max_addr_conflict_m'])}m 记冲突），"
                                f"冲突占比 {m['conflict_share']}"))
        m["pool_rows"] = pool_by_url.get(u, 0)
        out.append(m)
        checked += 1

    # 每层参照池统计（含未进投票的层，原样写清跳过原因）
    by_url = {m["url"]: m for m in out}
    for layer, s in pstats.items():
        s["url"] = purls.get(layer) or ""
        if not s["pool_rows"]:
            s["skip_reason"] = s["skip_reason"] or "addr 表为空（本地全表无地址行）"
        elif not s["pool_keyed"]:
            s["skip_reason"] = s["skip_reason"] or "本地全表行缺门牌/街名/州（无同址键）"
        elif s["url"] in by_url:
            hit = by_url[s["url"]]
            s.update(n_cmp=hit["n_cmp"], n_cmp_sample=hit["n_cmp_sample"], n_conflict=hit["n_conflict"], e7=hit["e7"])
        elif not s["url"]:
            s["skip_reason"] = s["skip_reason"] or "本地全表行无 src_layer_url（无法映射到分母 url，只作他源参照）"
    os.makedirs(args.outdir, exist_ok=True)
    with open(os.path.join(args.outdir, "e7-refpool-stats.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=POOL_COLS, restval="")
        w.writeheader()
        w.writerows([{k: s.get(k, "") for k in POOL_COLS} for s in
                     sorted(pstats.values(), key=lambda x: x["layer"])])
    cols = FIELDS + ["n_cmp_sample", "pool_rows"]
    with open(os.path.join(args.outdir, "coord-evidence-relax.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols, restval="")
        w.writeheader()
        w.writerows(out)
    skipped = [s for s in pstats.values() if s["skip_reason"]]
    summ = {"per_layer_cap": cap, "max_cmp_per_row": max_cmp, "sample_rows": n_sample_rows,
            "pool_rows": len(pool), "pool_rows_by_state": dict(collections.Counter((pstats.get(r[0]) or {}).get("state", "") for r in pool)),
            "pool_layers_total": len(pstats), "pool_layers_with_rows": sum(1 for s in pstats.values() if s["pool_rows"]),
            "pool_layers_keyed": sum(1 for s in pstats.values() if s["pool_keyed"]),
            "pool_layers_capped": sum(1 for s in pstats.values() if s["capped"]),
            "pool_layers_mapped_to_denominator": sum(1 for s in pstats.values() if s["url"]),
            "skipped_layers": len(skipped), "skip_reasons": dict(collections.Counter(s["skip_reason"] for s in skipped)),
            "e7_status_after_relax": dict(collections.Counter(m["e7"] for m in out)), "urls_evaluated": len(out),
            "note": "每层取前 N 行是采样、不是全量：capped 层与 skip 原因逐层见 e7-refpool-stats.csv"}
    with open(os.path.join(args.outdir, "e7-refpool-summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summ, fh, ensure_ascii=False, indent=1)
    c = collections.Counter(m["e7"] for m in out)
    print(f"urls_evaluated={checked} e7={dict(c)} pool_rows={len(pool)} pool_layers={len(pstats)} "
          f"capped={sum(1 for s in pstats.values() if s['capped'])} skipped={sum(1 for s in pstats.values() if s['skip_reason'])} "
          f"secs={round(time.time() - t0, 1)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
