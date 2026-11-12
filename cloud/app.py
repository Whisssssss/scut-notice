# -*- coding: utf-8 -*-
"""阿里云 FC 3.0 Web 函数（自定义运行时 Python 3.10）：
反向代理 jw.scut.edu.cn，解决 GitHub Actions 境外 IP 被 403 的问题。

自定义运行时要求代码自己起 HTTP Server 监听端口，所以这里用标准库实现。
启动命令：python3 app.py
"""
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

TARGET = "https://jw.scut.edu.cn"
PORT = 9000


class Proxy(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self._forward()

    def do_POST(self):
        self._forward()

    def _forward(self):
        length = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(length) if length else None
        url = TARGET + self.path

        headers = {
            "User-Agent": self.headers.get("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"),
            "Referer": TARGET + "/",
        }
        ctype = self.headers.get("Content-Type")
        if ctype:
            headers["Content-Type"] = ctype

        try:
            req = urllib.request.Request(url, data=body, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as r:
                data = r.read()
                self.send_response(r.status)
                self.send_header("Content-Type", r.headers.get("Content-Type", "text/html; charset=utf-8"))
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            msg = ("proxy error: " + str(e)).encode()
            self.send_response(502)
            self.send_header("Content-Length", str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)

    def log_message(self, fmt, *args):
        print("[proxy] " + (fmt % args))


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", PORT), Proxy).serve_forever()
