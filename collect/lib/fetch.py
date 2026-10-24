# -*- coding: utf-8 -*-
"""HTTP 层：ArcGIS 取数。从 pilot.py 抽出。

★ 关键约定：HTTP 200 但 body 是 {"error":...} 时也当错误（返回 __error__）。
   san_juan 那种服务就是这样报「Pagination is not supported」，以前被当成成功，
   导致该层永远只拿到 maxRecordCount 一页，而且 err 一直为空。
"""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (compatible; collect-pilot/1.0)"}


def get_json(url, timeout=180, tries=3):
    """★ 保留服务端原始报文：400 的 body 往往就是答案
       （例如 `{"error":{"message":"Pagination is not supported."}}`），
       以前只剩 `HTTP Error 400`，同一个坑要走三轮才定位。"""
    last = ""
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                d = json.loads(r.read().decode("utf-8", "replace"))
                # ★ 2026-10-24 实测：有的服务用 HTTP 200 包着 {"error":{...}} 报错
                #   （san_juan MapServer 就是这样，于是「成功」却只有 2000 行，err 一直是空）。
                if isinstance(d, dict) and d.get("error"):
                    return {"__error__": "svcerr:%s" % json.dumps(d["error"], ensure_ascii=False)[:300]}
                return d
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                body = ""
            last = "http%d:%s" % (e.code, body[:300])
            if e.code in (400, 401, 403, 404):   # 请求本身错了，重试无意义
                return {"__error__": last}
            time.sleep(1.5 * (i + 1))
        except Exception as e:  # 429 / 5xx 退避
            last = str(e)[:120]
            time.sleep(1.5 * (i + 1))
    return {"__error__": last}
