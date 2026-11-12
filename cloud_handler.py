#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""国内云函数入口：只补跑本科生院两个源（GitHub Actions 在国外会被 403）。

阿里云 FC 的请求处理程序填: cloud_handler.handler
腾讯云 SCF 的入口函数填:     cloud_handler.main_handler
"""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.abspath(__file__))


def _run():
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    r = subprocess.run(
        [sys.executable, "fetch.py", "--only-jw", "--days", "2",
         "--no-attach", "--only-yesterday"],
        cwd=BASE, env=env, capture_output=True, text=True, timeout=120,
    )
    out = (r.stdout or "") + (r.stderr or "")
    print(out)
    return {"ok": r.returncode == 0, "tail": out[-1500:]}


def handler(event, context):
    return _run()


def main_handler(event, context):
    return _run()
