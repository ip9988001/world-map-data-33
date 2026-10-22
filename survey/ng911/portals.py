#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""逐州官方门户：自动识别平台（Socrata / CKAN / ArcGIS Hub）并抓取全部相关数据集"""
import argparse, json, os
from ng911_inventory import ch_portal, NAME

HERE = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    a = ap.parse_args()
    ab = a.state.upper()
    recs, meta = ch_portal(ab)
    json.dump({"state": ab, "name": NAME.get(ab), "portals": meta, "rows": recs},
              open(os.path.join(HERE, "portal_%s.json" % ab), "w"), ensure_ascii=False)
    print("[%s] portals=%s recs=%d" % (ab, meta, len(recs)), flush=True)
