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

# ---------------------------------------------------------------- 失败分类（单一来源）
# ★ muse-000146 第 5 项：分页抓取里 400 与 404/500 混在一个失败桶 —— 400 通常是**可修的**
#   参数/分页越界（resultOffset/resultRecordCount 越界、"Pagination is not supported"），
#   404/500 是上游坏（不可修）。混在一起就无法定向修，故拆开并各给一个稳定名字，
#   账本 / plan 摘要 / 判据卡一律用这套名字，禁止在别处另起一套。
KIND_OK = "ok"
KIND_BAD_PAGING = "bad_request_paging"     # 400 + 分页/参数语义（可修）
KIND_400 = "bad_request_400"               # 400 但与分页无关（也可修，只是病因不同）
KIND_404 = "not_found_404"                 # 端点没了（不可修，只可判 empty/unverified）
KIND_5XX = "server_5xx"                    # 上游服务端坏（不可修，重试收益趋零）
KIND_429 = "rate_limited_429"              # 限流（等一等能好）
KIND_AUTH = "auth_4xx"                     # 401/403（凭据/权限）
KIND_SVCERR = "svcerr"                     # HTTP 200 但 body 带 {"error":...}
KIND_TIMEOUT = "timeout"                   # 超时/连接异常
KIND_OTHER = "other"

ALL_KINDS = (KIND_OK, KIND_BAD_PAGING, KIND_400, KIND_404, KIND_5XX, KIND_429,
             KIND_AUTH, KIND_SVCERR, KIND_TIMEOUT, KIND_OTHER)
# 400 的 body 里出现这些信号 → 归「分页/参数越界」而不是普通 400
PAGING_HINTS = ("pagination", "resultoffset", "resultrecordcount", "result offset",
                "result record count", "invalid query parameters", "invalid url parameters",
                "parameters are invalid", "count(*)")

# 可修（改代码/改参数就能再试）= 不判死；不可修（上游没了/坏了）= 判死
FIXABLE_KINDS = (KIND_BAD_PAGING, KIND_400, KIND_429)


def classify_failure(code=None, body="", status=None, exc=""):
    """把一次失败归到上面那套名字里的**一个**。

    code     HTTP 状态码（None = 没拿到响应，如超时/连接异常）
    body     响应体（字符串；400 的 body 往往就是答案）
    status   HTTP 状态（200 但 body 带 error 时传 200）
    exc      异常文本（没拿到响应时）
    """
    text = body.decode("utf-8", "replace") if isinstance(body, (bytes, bytearray)) else (body or "")
    low = text.lower()
    if code == 429 or "too many requests" in low or "429" in str(exc)[:40]:
        return KIND_429
    if code == 400:
        return KIND_BAD_PAGING if any(h in low for h in PAGING_HINTS) else KIND_400
    if code in (401, 403):
        return KIND_AUTH
    if code == 404:
        return KIND_404
    if code is not None and 500 <= int(code) <= 599:
        return KIND_5XX
    if status == 200 and '"error"' in low.replace(" ", ""):
        return KIND_SVCERR
    if "pagination is not supported" in low:
        return KIND_BAD_PAGING
    if code is None and exc:
        return KIND_TIMEOUT
    return KIND_OTHER


def kinds_tally(items, key="kind"):
    """按分类计数（账本 / plan 摘要共用）。返回 {kind: n}，顺序稳定、零值也列出。"""
    out = {k: 0 for k in ALL_KINDS if k != KIND_OK}
    for it in items or []:
        k = (it.get(key) if isinstance(it, dict) else str(it)) or KIND_OTHER
        out[k] = out.get(k, 0) + 1
    return out


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
                    return {"__error__": "svcerr:%s" % json.dumps(d["error"], ensure_ascii=False)[:300],
                            "__kind__": classify_failure(status=200, body=json.dumps(d["error"]))}
                return d
        except urllib.error.HTTPError as e:
            try:
                body = e.read().decode("utf-8", "replace")
            except Exception:
                body = ""
            last = "http%d:%s" % (e.code, body[:300])
            if e.code in (400, 401, 403, 404):   # 请求本身错了，重试无意义
                # ★ 第 5 项：400 必须与 404 分桶（400 可修、404 不可修）
                return {"__error__": last, "__kind__": classify_failure(e.code, body)}
            time.sleep(1.5 * (i + 1))
        except Exception as e:  # 429 / 5xx 退避
            last = str(e)[:120]
            time.sleep(1.5 * (i + 1))
    return {"__error__": last, "__kind__": classify_failure(code=None, body=last, exc=last)}
