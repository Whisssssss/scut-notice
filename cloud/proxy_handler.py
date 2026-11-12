# -*- coding: utf-8 -*-
"""阿里云 FC 3.0 HTTP 函数：反向代理 jw.scut.edu.cn

用途：GitHub Actions 的境外 IP 访问本科生院会被学校 WAF 返回 403。
用国内 FC 函数做出口，Actions 请求本函数，本函数再访问学校。

部署后把函数 URL（形如 https://xxx.fcapp.run）配到 GitHub 仓库
Secrets 的 JW_BASE，Actions 就会通过它抓本科生院。

请求处理程序填：proxy.handler
"""
import base64
import json
import urllib.error
import urllib.request

TARGET = "https://jw.scut.edu.cn"


def handler(event, context):
    ev = event if isinstance(event, dict) else json.loads(event or "{}")
    path = ev.get("rawPath") or "/"
    qs = ev.get("rawQueryString") or ""
    hdrs = {k.lower(): v for k, v in (ev.get("headers") or {}).items()}

    body = ev.get("body") or ""
    if ev.get("isBase64Encoded"):
        body = base64.b64decode(body)
    elif isinstance(body, str):
        body = body.encode() or None

    url = TARGET + path + ("?" + qs if qs else "")
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": hdrs.get("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
        "Content-Type": hdrs.get("content-type", "application/x-www-form-urlencoded"),
        "Accept": hdrs.get("accept", "*/*"),
        "Referer": TARGET + "/",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read()
            return {
                "statusCode": r.status,
                "headers": {"content-type": r.headers.get("Content-Type", "text/html; charset=utf-8")},
                "body": data.decode("utf-8", "replace"),
                "isBase64Encoded": False,
            }
    except urllib.error.HTTPError as e:
        return {
            "statusCode": e.code,
            "headers": {"content-type": "text/html; charset=utf-8"},
            "body": e.read().decode("utf-8", "replace"),
        }
