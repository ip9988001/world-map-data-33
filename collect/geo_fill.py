#!/usr/bin/env python3
"""geo_fill.py v2 — 给 layer_plan_clean.csv 未定位层补 state。
策略：①标题宽松匹配 ②feature+outSR=4326 反查（服务端转投影，最可靠）③extent 兜底(仅4326/3857)
"""
import csv, json, os, sys, time, math, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from geo_state import which_state  # noqa: E402

# ★ 2026-10-28：proj-XXXX 分支需要知道「这个 EPSG 是不是美国的坐标系」。
#   pyproj 可选：没有就跳过分支（标 proj-unhandled），绝不静默假装成功。
try:
    from pyproj import CRS, Transformer
    from pyproj.aoi import AreaOfInterest
    from pyproj.database import query_crs_info
    _US_AOI = AreaOfInterest(-125.0, 24.0, -66.0, 50.0)
    US_EPSG = {int(c.code) for c in query_crs_info(auth_name="EPSG", area_of_interest=_US_AOI)}
except Exception:  # noqa: BLE001
    US_EPSG = set()


SRC = os.path.join(HERE, 'layer_plan_clean.csv')
UA = {'User-Agent': 'world-map-data-33/1.0 (+geofill)'}

STATES = ['alabama','alaska','arizona','arkansas','california','colorado','connecticut','delaware',
 'florida','georgia','hawaii','idaho','illinois','indiana','iowa','kansas','kentucky','louisiana',
 'maine','maryland','massachusetts','michigan','minnesota','mississippi','missouri','montana',
 'nebraska','nevada','newhampshire','newjersey','newmexico','newyork','northcarolina','northdakota',
 'ohio','oklahoma','oregon','pennsylvania','rhodeisland','southcarolina','southdakota','tennessee',
 'texas','utah','vermont','virginia','washington','westvirginia','wisconsin','wyoming','districtofcolumbia']
AB = {'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO',
 'connecticut':'CT','delaware':'DE','florida':'FL','georgia':'GA','hawaii':'HI','idaho':'ID','illinois':'IL',
 'indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY','louisiana':'LA','maine':'ME','maryland':'MD',
 'massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS','missouri':'MO','montana':'MT',
 'nebraska':'NE','nevada':'NV','newhampshire':'NH','newjersey':'NJ','newmexico':'NM','newyork':'NY',
 'northcarolina':'NC','northdakota':'ND','ohio':'OH','oklahoma':'OK','oregon':'OR','pennsylvania':'PA',
 'rhodeisland':'RI','southcarolina':'SC','southdakota':'SD','tennessee':'TN','texas':'TX','utah':'UT',
 'vermont':'VT','virginia':'VA','washington':'WA','westvirginia':'WV','wisconsin':'WI','wyoming':'WY',
 'districtofcolumbia':'DC'}

def title_state(t):
    """宽松：maine_elevation / Maine-Turnpike 都算命中，长名优先避免 virginia/westvirginia 误判"""
    if not t: return None
    low = t.lower()
    flat = low.replace('_', ' ').replace('-', ' ')
    flat2 = flat.replace(' ', '')
    for nm in sorted(STATES, key=len, reverse=True):
        if nm in flat2: return AB[nm]
    return None

def http_json(u, timeout=25):
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode('utf-8', 'replace'))

def qurl(u):
    """ArcGIS 图层端点必须走 /query 才能查询；直接 ?where= 返回的是元数据。"""
    u = url_clean(u)
    return u if u.endswith('/query') else u + '/query'

def url_clean(u):
    u = (u or '').strip().rstrip('/')
    return u

def geo_probe(url):
    u = url_clean(url)
    base = u if u.endswith('/query') else u
    # ① feature + outSR=4326（服务端负责投影转换）
    #    ★ ArcGIS JSON 不是 GeoJSON：Point 是 {x,y}，Polyline 是 {paths}，Polygon 是 {rings}
    try:
        d = http_json(qurl(u) + '?where=1%3D1&outFields=*&resultRecordCount=5&returnGeometry=true&outSR=4326&f=json')
        for f in (d.get('features') or [])[:5]:
            g = f.get('geometry') or {}
            if 'x' in g and 'y' in g:
                lon, lat = float(g['x']), float(g['y'])
                if -180 <= lon <= -60 and 15 <= lat <= 72:
                    return (lon, lat), 'feature-point'
                continue
            pts = []
            def collect(o):
                if isinstance(o, (list, tuple)):
                    if len(o) >= 2 and isinstance(o[0], (int, float)) and isinstance(o[1], (int, float)):
                        pts.append((float(o[0]), float(o[1])))
                    else:
                        for z in o: collect(z)
            for key in ('rings', 'paths', 'coordinates'):
                if key in g: collect(g[key]); break
            if pts:
                lon = sum(q[0] for q in pts) / len(pts)
                lat = sum(q[1] for q in pts) / len(pts)
                if -180 <= lon <= -60 and 15 <= lat <= 72:
                    return (lon, lat), 'feature-centroid'
    except Exception:
        pass
    # ② extent 兜底（只接受 4326/3857）—— 元数据用原端点
    try:
        m = http_json(base + '?f=json')
        ext = m.get('extent') or m.get('fullExtent') or {}
        sr = ext.get('spatialReference') or {}
        w = sr.get('latestWkid') or sr.get('wkid')
        if ext.get('xmin') is not None and w in (4326, None, 3857, 102100, 900913):
            x = (float(ext['xmin']) + float(ext['xmax'])) / 2
            y = (float(ext['ymin']) + float(ext['ymax'])) / 2
            if w in (3857, 102100, 900913):
                lon = x / 20037508.34 * 180.0
                lat = (2 * math.atan(math.exp(y / 6378137.0)) - math.pi / 2) * 180 / math.pi
            else:
                lon, lat = x, y
            span = abs(float(ext['xmax']) - float(ext['xmin'])) / max(1, (20037508.34 / 180.0)) if w in (3857, 102100, 900913) else abs(float(ext['xmax']) - float(ext['xmin']))
            if span > 12: return None, 'multi-state'
            return (lon, lat), 'extent'
        if ext.get('xmin') is not None: return None, 'proj-%s' % w
    except Exception as e:
        return None, 'meta:%s' % type(e).__name__
    return None, 'nogeom'

def feature_vote(url, n=10, need=2):
    """multi-state 专用：extent 跨州时改取多个 feature 的坐标，逐个过州界，多数票。
    extent 说跨州 ≠ 数据跨州（很多是 extent 被设成全美，数据其实是某州子集）。"""
    try:
        d = http_json(qurl(url) + '?where=1%%3D1&outFields=*&resultRecordCount=%d'
                                  '&returnGeometry=true&outSR=4326&f=json' % n)
    except Exception:  # noqa: BLE001
        return None, 0
    votes = Counter()
    for f in (d.get('features') or [])[:n]:
        g = f.get('geometry') or {}
        pt = None
        if 'x' in g and 'y' in g:
            pt = (float(g['x']), float(g['y']))
        else:
            pts = []
            def collect(o):
                if isinstance(o, (list, tuple)):
                    if len(o) >= 2 and isinstance(o[0], (int, float)) and isinstance(o[1], (int, float)):
                        pts.append((float(o[0]), float(o[1])))
                    else:
                        for z in o: collect(z)
            for key in ('rings', 'paths', 'coordinates'):
                if key in g: collect(g[key]); break
            if pts:
                pt = (sum(q[0] for q in pts) / len(pts), sum(q[1] for q in pts) / len(pts))
        if pt and -180 <= pt[0] <= -60 and 15 <= pt[1] <= 72:
            ab = which_state(*pt)
            if ab: votes[ab] += 1
    if votes:
        ab, c = votes.most_common(1)[0]
        if c >= need: return ab, c
    return None, 0


def proj_fallback(url, wkid):
    """proj-XXXX 专用：wkid 若在美国 EPSG 集合内，把 extent 中心点转到 4326 再判州。"""
    try:
        w = int(wkid)
    except Exception:  # noqa: BLE001
        return None, 'proj-nonint'
    if not US_EPSG or w not in US_EPSG:
        return None, 'proj-nonus-%s' % wkid
    try:
        base = url_clean(url)
        m = http_json(base + '?f=json')
        ext = m.get('extent') or m.get('fullExtent') or {}
        if ext.get('xmin') is None:
            return None, 'proj-noext-%s' % wkid
        x = (float(ext['xmin']) + float(ext['xmax'])) / 2
        y = (float(ext['ymin']) + float(ext['ymax'])) / 2
        tr = Transformer.from_crs(CRS.from_epsg(w), CRS.from_epsg(4326), always_xy=True)
        lon, lat = tr.transform(x, y)
        if -180 <= lon <= -60 and 15 <= lat <= 72:
            ab = which_state(lon, lat)
            if ab: return ab, 'proj-fix-%s' % wkid
    except Exception:  # noqa: BLE001
        pass
    return None, 'proj-fail-%s' % wkid


def one(row):
    # 标题优先（零成本）
    st = title_state(row.get('title', ''))
    if st: return st, 'title'
    u = row.get('url') or ''
    pt, how = geo_probe(u)
    if not pt:
        if how == 'multi-state':
            ab, c = feature_vote(u)
            if ab: return ab, 'vote-%d' % c
            return None, 'multi-state'
        if how.startswith('proj-') and 'fail' not in how and 'nonus' not in how:
            ab, h2 = proj_fallback(u, how[5:])
            if ab: return ab, h2
            return None, h2
        return None, how
    ab = which_state(*pt)
    if ab: return ab, 'geo-' + how
    # 2026-10-28 修：有坐标但州界多边形判定不在美国 → 必须单独归类，
    # 原来返回 (None, 'geo-feature-point')，把这个最关键的信号吞掉了。
    return None, 'outside_us'

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    write = '--write' in sys.argv
    rows = list(csv.DictReader(open(SRC, encoding='utf-8', errors='ignore')))
    fields = list(rows[0].keys())
    todo = [r for r in rows if (r.get('state') or '') in ('', '未定位')]
    if limit: todo = todo[:limit]
    print('待定位:', len(todo), '| 写回:', write)
    stat = Counter(); filled = 0; t0 = time.time()
    rows_by = Counter(); samples = {}
    def reason_of(how):
        return how.split(':')[0] if ':' in how else how
    def work(r):
        st, how = one(r); return r, st, how
    with ThreadPoolExecutor(16) as ex:
        for i, (r, st, how) in enumerate(ex.map(work, todo), 1):
            rs = reason_of(how)
            stat[rs] += 1
            try: rows_by[rs] += int(float(r.get('row_count') or 0))
            except Exception: pass
            if st: r['state'] = st; r['state_src'] = how; filled += 1
            else:
                r['state_src'] = 'fail:' + how
                bucket = samples.setdefault(rs, [])
                if len(bucket) < 5:
                    bucket.append({'title': (r.get('title') or '')[:90],
                                   'url': (r.get('url') or '')[:130],
                                   'row_count': r.get('row_count')})
            if i % 200 == 0: print(f'  {i}/{len(todo)} ok={filled} {time.time()-t0:.0f}s')

    # ★ 归因报告：无副作用，任何模式下都写（2026-10-28 新增）
    by_reason_layers = {}
    for r in todo:
        rs = reason_of(r.get('state_src', 'fail:unknown').replace('fail:', ''))
        if not r.get('state'):
            by_reason_layers.setdefault(rs, []).append(r.get('layer') or r.get('id') or '')
    rep = {
        'layers_by_reason': by_reason_layers,
        'generated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'source': 'collect/layer_plan_clean.csv（state=未定位 的层）',
        'total_todo': len(todo), 'filled': filled,
        'unfilled': len(todo) - filled,
        'by_reason': dict(stat.most_common()),
        'rows_by_reason': {k: rows_by[k] for k, _ in stat.most_common()},
        'samples': samples,
        'note': 'only 陈述事实：每类各多少层、多少行、样本层是什么。补不补、怎么补由大脑决定。',
    }
    json.dump(rep, open(os.path.join(HERE, 'geo_fill_report.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    if write:
        with open(SRC, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(rows)
    print(json.dumps(dict(todo=len(todo), filled=filled, by_src=dict(stat), secs=round(time.time()-t0,1)), ensure_ascii=False, indent=1))

if __name__ == '__main__':
    main()
