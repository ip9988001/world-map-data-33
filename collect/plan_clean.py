#!/usr/bin/env python3
"""plan_clean.py — layer_plan 清洗：剔空层/skip + 域名与标题直映射州（零网络）"""
import csv, re, collections, json, pathlib

SRC = pathlib.Path('collect/layer_plan.csv')
OUT = pathlib.Path('collect/layer_plan_clean.csv')
REPORT = pathlib.Path('collect/plan_clean_report.json')

STATE_NAMES = {
 'alabama':'AL','alaska':'AK','arizona':'AZ','arkansas':'AR','california':'CA','colorado':'CO',
 'connecticut':'CT','delaware':'DE','florida':'FL','georgia':'GA','hawaii':'HI','idaho':'ID',
 'illinois':'IL','indiana':'IN','iowa':'IA','kansas':'KS','kentucky':'KY','louisiana':'LA',
 'maine':'ME','maryland':'MD','massachusetts':'MA','michigan':'MI','minnesota':'MN','mississippi':'MS',
 'missouri':'MO','montana':'MT','nebraska':'NE','nevada':'NV','newhampshire':'NH','newjersey':'NJ',
 'newmexico':'NM','newyork':'NY','northcarolina':'NC','northdakota':'ND','ohio':'OH','oklahoma':'OK',
 'oregon':'OR','pennsylvania':'PA','rhodeisland':'RI','southcarolina':'SC','southdakota':'SD',
 'tennessee':'TN','texas':'TX','utah':'UT','vermont':'VT','virginia':'VA','washington':'WA',
 'westvirginia':'WV','wisconsin':'WI','wyoming':'WY','districtofcolumbia':'DC'}
ABBR = set(STATE_NAMES.values())

def state_from_url(url):
    if not url: return None, None
    m = re.search(r'https?://([^/]+)', url)
    if not m: return None, None
    host = m.group(1).lower()
    parts = host.split('.')
    # 1) 形如 data.ny.gov / xxx.tx.gov
    for i, p in enumerate(parts):
        if p == 'gov' and i > 0:
            cand = parts[i-1].upper()
            if cand in ABBR: return cand, 'domain-abbr'
    # 2) 州全名出现在域名里
    flat = host.replace('.', '').replace('-', '')
    for name, ab in STATE_NAMES.items():
        if name in flat: return ab, 'domain-name'
    # 3) 子域后缀带州缩写：cookcountyil / ramseycountymn
    for p in reversed(parts[:-1]):
        for ab in ABBR:
            if p.endswith(ab.lower()) and len(p) > 3: return ab, 'domain-suffix'
    return None, None

def state_from_title(t):
    if not t: return None, None
    low = t.lower()
    for name, ab in STATE_NAMES.items():
        if re.search(r'\b' + name + r'\b', low): return ab, 'title-name'
    return None, None

rows = list(csv.DictReader(SRC.open(encoding='utf-8', errors='ignore')))
fields = list(rows[0].keys()) + ['drop_reason', 'state_src']
kept, dropped, fixed = [], collections.Counter(), collections.Counter()
for r in rows:
    if (r.get('plan') or '') == 'skip':
        dropped['plan=skip'] += 1; continue
    try: rc = int(r.get('row_count') or 0)
    except Exception: rc = 0
    if rc == 0:
        dropped['row_count=0'] += 1; continue
    r['drop_reason'] = ''
    if (r.get('state') or '') in ('', '未定位'):
        ab, src = state_from_url(r.get('url', ''))
        if not ab: ab, src = state_from_title(r.get('title', ''))
        if ab: r['state'] = ab; r['state_src'] = src; fixed[src] += 1
        else: r['state_src'] = 'still-unknown'
    else:
        r['state_src'] = 'orig'
    kept.append(r)

with OUT.open('w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore'); w.writeheader(); w.writerows(kept)

un = sum(1 for r in kept if (r.get('state') or '') in ('', '未定位'))
rep = dict(total=len(rows), kept=len(kept), dropped=dict(dropped), fixed_by=dict(fixed),
           still_unknown=un, kept_rows=sum(int(r.get('row_count') or 0) for r in kept))
REPORT.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding='utf-8')
print(json.dumps(rep, ensure_ascii=False, indent=1))
