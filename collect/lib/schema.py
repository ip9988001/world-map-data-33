# -*- coding: utf-8 -*-
"""字段归一化（纯函数，无 IO、无全局状态）—— 从 pilot.py 抽出。"""
# ★ 抽模块时漏了这两行：normalize() 里用 re.match / hashlib.md5，
#   一旦某层带「完整地址」字段就 NameError 秒挂（STEP-03 灰度 20 层里挂了 5 层正是这个）。
import hashlib
import re

F_ADD = ("ADD_NUM", "ADDRNUM", "ADDRESS_NUMBER", "HOUSE_NUM", "HOUSENUM", "STREET_NUM", "ADDR_NO")
F_FULL = ("FULLADDR", "FULL_ADDR", "FULL_ADDRESS", "ADDRESS", "SITE_ADDRESS", "LOCATION")
F_PRE = ("PRE_DIR", "PREDIR", "PRE_DIRECTION")
F_ST = ("ST_NAME", "STREET", "STREET_NAME", "ROAD_NAME", "STR_NAME")
F_SUF = ("ST_SUF", "STTYPE", "STREET_TYPE", "SUFFIX")
F_POST = ("POST_DIR", "POSTDIR")
F_UNIT = ("SUBNUM", "UNIT", "UNIT_NUM", "SUITE", "APT", "BLDG", "UNITID")
F_CITY = ("CITY", "COMMUNITY", "MUNICIPALITY", "POST_CITY", "TOWN", "PLACE")
F_ZIP = ("ZIP", "ZIPCODE", "ZIP_CODE", "POSTAL_CODE", "ZIP5")
F_ESN = ("ESN", "ESN_ID", "ESNID")


def pick(attrs, names):
    up = {k.upper(): k for k in attrs}
    for n in names:
        if n in up:
            return str(attrs[up[n]] or "").strip()
    return ""


def normalize(attrs, lat, lon):
    add = pick(attrs, F_ADD)
    st = pick(attrs, F_ST)
    zipc = pick(attrs, F_ZIP)
    full = pick(attrs, F_FULL)
    if not add and full:
        m = re.match(r"\s*(\d+[\w-]*)", full)
        add = m.group(1) if m else ""
    if not st and full:
        parts = re.sub(r"^\s*\d+[\w-]*\s*", "", full).split(",")
        st = parts[0].strip() if parts else ""
    key = hashlib.md5(("%s|%s|%s" % (add.lower(), st.lower(), zipc)).encode()).hexdigest()[:16] if (add and st) else ""
    return {
        "add_num": add, "pre_dir": pick(attrs, F_PRE), "st_name": st,
        "st_suf": pick(attrs, F_SUF), "post_dir": pick(attrs, F_POST),
        "unit": pick(attrs, F_UNIT), "city": pick(attrs, F_CITY), "zip": zipc,
        "esn": pick(attrs, F_ESN), "lat": lat, "lon": lon, "addr_key": key,
    }
