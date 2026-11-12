#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""华南理工大学通知抓取器 —— 纯脚本 / 零第三方依赖 / 幂等可重复运行

  python fetch.py                   日常：抓近 3 天，新增条目推微信
  python fetch.py --days 30         回填最近 30 天
  python fetch.py --limit 3         调试：每个源最多 3 条
  python fetch.py --no-body         只抓列表，不抓正文
"""
import argparse, hashlib, json, os, re, smtplib, sqlite3, ssl, sys, time
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import urllib.request, urllib.parse
from html import unescape
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
BASE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(BASE, "config.json")
if not os.path.exists(CFG_PATH):
    sys.exit("未找到 config.json：请先复制 config.example.json 并填写推送配置")
CFG = json.load(open(CFG_PATH, encoding="utf-8"))

# 学校主站(www.scut.edu.cn / news.scut.edu.cn)只接受 legacy cipher，
# OpenSSL 3.x 默认安全级别会直接 handshake failure，必须降到 SECLEVEL=0
CTX = ssl.create_default_context()
CTX.set_ciphers("DEFAULT:@SECLEVEL=0")

DATE_RE = re.compile(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})")
UA = CFG["user_agent"]

def log(msg):
    print(msg, flush=True)

def http_get(url, data=None, referer=None):
    h = {"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"}
    if referer: h["Referer"] = referer
    if data is not None:
        data = urllib.parse.urlencode(data).encode()
        h["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
        h["X-Requested-With"] = "XMLHttpRequest"
    req = urllib.request.Request(url, data=data, headers=h)
    last = None
    for i in range(CFG.get("retry", 3)):
        try:
            with urllib.request.urlopen(req, timeout=CFG.get("timeout", 30), context=CTX) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last

def norm_date(m):
    return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

def page_url(url, p):
    return url if p == 1 else re.sub(r"list\.htm$", f"list{p}.htm", url)

# ---------- 列表解析 ----------
def parse_boda(html, base):
    out, seen = [], set()
    for m in re.finditer(r"""<a\s[^>]*href=['"]([^'"]+)['"][^>]*title=['"]([^'"]*)['"][^>]*>""", html):
        href, title = m.group(1), m.group(2).strip()
        if not href or href.startswith("javascript") or not title:
            continue
        dm = DATE_RE.search(html[m.end():m.end() + 500])
        if not dm:
            continue
        if href.startswith("/"):
            href = base + href
        if href in seen:
            continue
        seen.add(href)
        out.append({"title": title, "url": href, "date": norm_date(dm)})
    return out

def parse_jw(cat, page, size=50):
    body = http_get("https://jw.scut.edu.cn/zhinan/cms/article/v2/findInformNotice.do",
                    data={"category": cat, "tag": "", "keyword": "", "pageNum": page, "pageSize": size},
                    referer="https://jw.scut.edu.cn/zhinan/cms/index.do")
    j = json.loads(body)
    rows = [{"title": it["title"],
             "url": "https://jw.scut.edu.cn/zhinan/cms/article/view.do?type=posts&id=" + it["id"],
             "date": it["createTime"].replace(".", "-"),
             "id": it["id"]} for it in j.get("list", [])]
    return j.get("total", 0), rows

# ---------- 正文 ----------
def balanced_div(src, start):
    depth = 0
    for m in re.finditer(r"</?div\b[^>]*>", src, re.I):
        if m.start() < start:
            continue
        if m.group(0).startswith("</"):
            depth -= 1
            if depth == 0:
                return src[start:m.start()]
        else:
            depth += 1
    return src[start:]

def to_text(frag):
    s = re.sub(r"<(script|style)\b[\s\S]*?</\1>", " ", frag, flags=re.I)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    s = re.sub(r"</(p|div|li|tr|h[1-6])>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    s = unescape(s)
    s = re.sub(r"[ \t\u3000]+", " ", s)
    s = re.sub(r"\n[ ]+", "\n", s)
    s = re.sub(r"\n{2,}", "\n\n", s)
    return s.strip()

def fetch_body(url, kind):
    html = http_get(url, referer=url)
    if kind == "jw":
        m = re.search(r'class="content"', html)
        if not m:
            return ""
        start = html.rfind("<div", 0, m.start())
        frag = balanced_div(html, start)
        frag = re.sub(r"<h[35]\b[\s\S]*?</h[35]>", " ", frag, flags=re.I)
        return to_text(frag)
    i = html.find("wp_articlecontent")
    if i < 0:
        return ""
    return to_text(balanced_div(html, html.rfind("<div", 0, i)))

def make_uid(item):
    if "id" in item:
        return "jw:" + item["id"]
    m = re.search(r"c\d+a\d+", item["url"])
    if m:
        return "boda:" + m.group(0)
    return "url:" + hashlib.md5(item["url"].encode()).hexdigest()[:16]

# ---------- 存储 ----------
def open_db():
    conn = sqlite3.connect(os.path.join(BASE, CFG["db"]))
    conn.execute("""CREATE TABLE IF NOT EXISTS notices(
        uid TEXT PRIMARY KEY, site TEXT, column_name TEXT, title TEXT,
        url TEXT, pub_date TEXT, body TEXT, summary TEXT,
        external INTEGER DEFAULT 0, fetched_at TEXT)""")
    conn.commit()
    return conn

def push_wecom(markdown):
    hook = CFG.get("wecom_webhook", "").strip()
    if not hook:
        return False
    chunks, cur = [], ""
    for line in markdown.split("\n"):
        if len(cur) + len(line) > 3800:
            chunks.append(cur); cur = ""
        cur += line + "\n"
    if cur.strip():
        chunks.append(cur)
    for c in chunks:
        body = json.dumps({"msgtype": "markdown", "markdown": {"content": c}}, ensure_ascii=False).encode()
        req = urllib.request.Request(hook, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                log(f"  企业微信推送 {len(c)} 字节: {r.read().decode()[:80]}")
        except Exception as e:
            log(f"  推送失败: {e}")
        time.sleep(0.5)
    return True

def _linkify(s):
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)

def md_to_html(md):
    out, lis = [], []
    def flush():
        nonlocal lis
        if lis:
            out.append("<ul>" + "".join("<li>" + x + "</li>" for x in lis) + "</ul>")
            lis = []
    for line in md.split("\n"):
        t = line.rstrip()
        if t.startswith("### "):
            flush(); out.append(f"<h4>{t[4:]}</h4>")
        elif t.startswith("## "):
            flush(); out.append(f"<h3>{t[3:]}</h3>")
        elif t.startswith("# "):
            flush(); out.append(f"<h2>{t[2:]}</h2>")
        elif t.startswith("- "):
            lis.append(_linkify(t[2:]))
        elif t.strip().startswith("> "):
            flush()
            out.append('<blockquote style="color:#666;margin:2px 0 10px 16px;'
                       'border-left:3px solid #ddd;padding-left:10px">'
                       + _linkify(t.strip()[2:]) + "</blockquote>")
        elif t.strip().startswith("**") and t.strip().endswith("**"):
            out.append(f"<p><b>{t.strip().strip('*')}</b></p>")
        elif t.strip().startswith("*") and t.strip().endswith("*") and len(t.strip()) > 2:
            out.append(f"<p><i>{t.strip().strip('*')}</i></p>")
        elif not t.strip():
            flush(); out.append("<br>")
        else:
            flush(); out.append(f"<p>{_linkify(t)}</p>")
    flush()
    return ("<html><body style=\"font-family:system-ui,-apple-system,sans-serif;"
            "line-height:1.6;font-size:14px\">" + "\n".join(out) + "</body></html>")

def push_email(title, markdown):
    s = CFG.get("smtp") or {}
    if not s.get("host") or not s.get("user"):
        return False
    to = s.get("to") or s["user"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(title, "utf-8")
    msg["From"] = s["user"]
    msg["To"] = to
    msg.attach(MIMEText(md_to_html(markdown), "html", "utf-8"))
    try:
        with smtplib.SMTP_SSL(s["host"], int(s.get("port", 465)), timeout=30) as sm:
            sm.login(s["user"], s["password"])
            sm.sendmail(s["user"], [to], msg.as_string())
        log(f"  邮件推送成功 -> {to}")
    except Exception as e:
        log(f"  邮件推送失败: {e}")
    return True

def build_digest_md(conn, today):
    """从库生成当日简报，带可点击目录（GitHub / VS Code / Typora 均可跳转）。"""
    rows = conn.execute(
        "SELECT site, column_name, title, url, pub_date, summary FROM notices "
        "WHERE fetched_at=? ORDER BY pub_date DESC", (today,)).fetchall()
    if not rows:
        return None

    sites = []
    for s in CFG["sources"]:
        if s["site"] not in sites:
            sites.append(s["site"])
    tree = {}
    for r in rows:
        tree.setdefault(r[0], {}).setdefault(r[1], []).append(r)

    lines = [f"# 华工通知日报 {today}", "", f"今日新增 **{len(rows)}** 条通知", "", "## 目录", ""]
    for si, site in enumerate(sites):
        cols = [s for s in CFG["sources"] if s["site"] == site]
        total = sum(len(tree.get(site, {}).get(c["column"], [])) for c in cols)
        if not total:
            continue
        lines.append(f"- [**{site}**](#site-{si}) · {total} 条")
        for ci, c in enumerate(cols):
            n = len(tree.get(site, {}).get(c["column"], []))
            if n:
                lines.append(f"  - [{c['column']}](#col-{si}-{ci}) · {n} 条")
    lines += ["", "---", ""]

    for si, site in enumerate(sites):
        cols = [s for s in CFG["sources"] if s["site"] == site]
        if not any(tree.get(site, {}).get(c["column"]) for c in cols):
            continue
        lines += [f'<a id="site-{si}"></a>', "", f"## {site}", ""]
        for ci, c in enumerate(cols):
            items = tree.get(site, {}).get(c["column"], [])
            if not items:
                continue
            lines += [f'<a id="col-{si}-{ci}"></a>', "", f"### {c['column']}", ""]
            for _, _, title, url, pub_date, summary in items:
                lines.append(f"- **{pub_date}** [{title}]({url})")
                if summary:
                    lines.append(f"  > {summary[:120]}")
            lines.append("")
    return "\n".join(lines)

def push_message(title, markdown):
    sent = False
    if push_wecom(markdown):
        sent = True
    if push_email(title, markdown):
        sent = True
    if not sent:
        log("  (未配置任何推送渠道，仅保存本地)")

# ---------- 主流程 ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=3, help="时间窗天数（回填用大值）")
    ap.add_argument("--limit", type=int, default=0, help="每个源最多处理条数（调试）")
    ap.add_argument("--no-body", action="store_true", help="不抓正文")
    ap.add_argument("--no-push", action="store_true", help="不推送")
    ap.add_argument("--once-per-day", action="store_true", help="今天已跑过则跳过（供开机自启去重）")
    ap.add_argument("--digest-only", action="store_true", help="不抓取，只从库重建当日简报")
    args = ap.parse_args()

    today = datetime.now().strftime("%Y-%m-%d")
    marker = os.path.join(BASE, "logs", ".last_run")
    if args.once_per_day:
        os.makedirs(os.path.dirname(marker), exist_ok=True)
        if os.path.exists(marker) and open(marker).read().strip() == today:
            log(f"今天 {today} 已运行过，跳过。")
            return
    if args.digest_only:
        conn0 = open_db()
        md0 = build_digest_md(conn0, today)
        if md0 is None:
            log("今天没有新通知。")
            return
        os.makedirs(os.path.join(BASE, CFG["digest_dir"]), exist_ok=True)
        dp = os.path.join(BASE, CFG["digest_dir"], f"{today}.md")
        with open(dp, "w", encoding="utf-8") as f:
            f.write(md0)
        log(f"简报已重建: {dp}")
        return
    cutoff = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    log(f"时间窗 >= {cutoff}   共 {len(CFG['sources'])} 个数据源\n")

    conn = open_db()
    known = {r[0] for r in conn.execute("SELECT uid FROM notices")}
    fresh_all, n_src_ok = [], 0

    for idx, src in enumerate(CFG["sources"], 1):
        label = f"{src['site']}/{src['column']}"
        items = []
        try:
            if src["type"] == "jw":
                for p in range(1, CFG["max_pages"] + 1):
                    _, rows = parse_jw(src["category"], p)
                    items += rows
                    time.sleep(CFG["delay"])
                    if rows and rows[-1]["date"] < cutoff:
                        break
            else:
                for p in range(1, CFG["max_pages"] + 1):
                    rows = parse_boda(http_get(page_url(src["url"], p)), src["base"])
                    items += rows
                    time.sleep(CFG["delay"])
                    if not rows or rows[-1]["date"] < cutoff:
                        break
            n_src_ok += 1
        except Exception as e:
            log(f"[{idx:2d}/{len(CFG['sources'])}] {label:16s} 列表失败 {type(e).__name__}: {str(e)[:60]}")
            continue

        fresh = []
        for it in items:
            if it["date"] < cutoff:
                continue
            uid = make_uid(it)
            if uid in known:
                continue
            it.update(uid=uid, site=src["site"], column=src["column"], _idx=idx)
            known.add(uid)
            fresh.append(it)
        if args.limit:
            fresh = fresh[:args.limit]

        log(f"[{idx:2d}/{len(CFG['sources'])}] {label:16s} 列表{len(items):3d}  窗口内新增{len(fresh):3d}")

        for it in fresh:
            ext = not re.search(r"scut\.edu\.cn", it["url"])
            body = ""
            if not ext and not args.no_body:
                try:
                    body = fetch_body(it["url"], "jw" if it["uid"].startswith("jw:") else "boda")
                    time.sleep(CFG["delay"])
                except Exception as e:
                    log(f"       正文失败: {str(e)[:50]}")
            summary = " ".join(body.split())[:180]
            if not ext and not body:
                summary = "（该通知为站内跳转页，正文需登录后查看）"
            it.update(external=int(ext), body=body[:20000], summary=summary)
            conn.execute("INSERT OR REPLACE INTO notices VALUES(?,?,?,?,?,?,?,?,?,?)",
                         (it["uid"], it["site"], it["column"], it["title"], it["url"],
                          it["date"], it["body"], it["summary"], it["external"], today))
            fresh_all.append(it)
        conn.commit()

    log(f"\n数据源成功 {n_src_ok}/{len(CFG['sources'])}，本次新增 {len(fresh_all)} 条")

    os.makedirs(os.path.join(BASE, CFG["data_dir"]), exist_ok=True)
    with open(os.path.join(BASE, CFG["data_dir"], f"{today}.jsonl"), "a", encoding="utf-8") as f:
        for it in fresh_all:
            f.write(json.dumps({k: v for k, v in it.items() if not k.startswith("_")}, ensure_ascii=False) + "\n")

    # 当日简报以"今天入库的全部条目"为准：多次运行会累积成一份完整日报
    os.makedirs(os.path.join(BASE, CFG["digest_dir"]), exist_ok=True)
    md = build_digest_md(conn, today)
    if md is None:
        log("今天没有新通知。")
        return

    dpath = os.path.join(BASE, CFG["digest_dir"], f"{today}.md")
    with open(dpath, "w", encoding="utf-8") as f:
        f.write(md)
    log(f"简报已生成: {dpath}")

    # 推送只发"本次运行新增"，避免回填那天刷屏（简报文件仍是当日全量）
    if not args.no_push and fresh_all:
        fresh_all.sort(key=lambda r: r["date"], reverse=True)
        fresh_all.sort(key=lambda r: r["_idx"])
        pm = [f"## 华工通知 · {today} 新增 {len(fresh_all)} 条", ""]
        s = c = None
        for it in fresh_all:
            if it["site"] != s:
                s, c = it["site"], None
                pm += ["", f"**{s}**", ""]
            if it["column"] != c:
                c = it["column"]
                pm += [f"*{c}*", ""]
            pm.append(f"- {it['date']} [{it['title']}]({it['url']})")
        push_message(f"华工通知 {today} 新增 {len(fresh_all)} 条", "\n".join(pm))

    with open(marker, "w") as mf:
        mf.write(today)

if __name__ == "__main__":
    main()
