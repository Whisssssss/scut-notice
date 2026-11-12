# -*- coding: utf-8 -*-
"""阿里云 FC 3.0 Web 函数（WSGI）：反向代理 jw.scut.edu.cn

创建 Web 函数时：
  运行环境  Python 3.10
  启动命令  留空（平台自动识别 WSGI）
  监听端口  9000
  入口        proxy_wsgi.handler

部署后把函数 URL 配到 GitHub Secrets 的 JW_BASE。
"""
import urllib.error
import urllib.request

TARGET = "https://jw.scut.edu.cn"


def handler(environ, start_response):
    path = environ.get("PATH_INFO") or "/"
    if not path.startswith("/"):
        path = "/" + path
    qs = environ.get("QUERY_STRING") or ""
    length = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(length) if length > 0 else None

    url = TARGET + path + ("?" + qs if qs else "")
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": environ.get("HTTP_USER_AGENT", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
        "Content-Type": environ.get("CONTENT_TYPE", "application/x-www-form-urlencoded"),
        "Accept": environ.get("HTTP_ACCEPT", "*/*"),
        "Referer": TARGET + "/",
    })
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read()
            ctype = r.headers.get("Content-Type", "text/html; charset=utf-8")
            start_response("200 OK", [("Content-Type", ctype)])
            return [data]
    except urllib.error.HTTPError as e:
        data = e.read()
        start_response(str(e.code) + " Error", [("Content-Type", "text/html; charset=utf-8")])
        return [data]
