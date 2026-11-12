#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全文搜索已抓取的通知（标题 + 正文）。

  python search.py 奖学金
  python search.py 期末 考试
  python search.py 推免 --site 学院 --limit 5
"""
import argparse, json, os, sqlite3, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(BASE, "config.json")
if not os.path.exists(CFG_PATH):
    sys.exit("未找到 config.json：请先复制 config.example.json 并填写")
CFG = json.load(open(CFG_PATH, encoding="utf-8"))


def snippet(body, terms, width=55):
    if not body:
        return ""
    b = " ".join(body.split())
    for t in terms:
        i = b.find(t)
        if i >= 0:
            s, e = max(0, i - width), min(len(b), i + len(t) + width)
            return ("…" if s else "") + b[s:e] + ("…" if e < len(b) else "")
    return b[: width * 2] + ("…" if len(b) > width * 2 else "")


def main():
    ap = argparse.ArgumentParser(description="搜索已抓取的通知")
    ap.add_argument("terms", nargs="+", help="关键词，多个为 AND")
    ap.add_argument("--site", help="限定站点，如 学校 / 学院 / 本科生院")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args()

    conn = sqlite3.connect(os.path.join(BASE, CFG["db"]))
    where, params = [], []
    for t in args.terms:
        where.append("(title LIKE ? OR body LIKE ?)")
        params += [f"%{t}%", f"%{t}%"]
    sql = ("SELECT pub_date, site, column_name, title, url, body FROM notices "
           "WHERE " + " AND ".join(where))
    if args.site:
        sql += " AND site = ?"
        params.append(args.site)
    sql += " ORDER BY pub_date DESC LIMIT ?"
    params.append(args.limit)

    rows = conn.execute(sql, params).fetchall()
    if not rows:
        print(f"没有匹配「{' '.join(args.terms)}」的通知。")
        return
    print(f"命中 {len(rows)} 条（最新在前）\n")
    for pub_date, site, col, title, url, body in rows:
        print(f"● {pub_date}  [{site}/{col}]")
        print(f"  {title}")
        print(f"  {url}")
        sn = snippet(body, args.terms)
        if sn:
            print(f"  └ {sn}")
        print()


if __name__ == "__main__":
    main()
