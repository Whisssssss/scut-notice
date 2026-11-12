# SCUT Notice Crawler · 华工通知抓取

每天自动抓取华南理工大学 10 个栏目的新通知，去重入库、生成带目录的简报，并推送到邮箱（微信会弹提醒）。

纯 Python 标准库实现，**零第三方依赖**。

## 特性

- **10 个数据源**：学校校园新闻 / 教学科研通知 / 学术预告，化学与化工学院 5 个栏目，本科生院通知公告 + 学院通知
- **增量去重**：以内容 ID 为主键，重复运行不重复入库、不重复推送
- **正文入库**：只对新条目抓详情页正文，存进 SQLite，可全文检索
- **关键词提醒**：标题命中关注词（考试 / 选课 / 奖学金 …）的条目标 ⭐
- **附件下载**：通知里的 pdf / xlsx / zip 一并保存到 `attachments/`
- **全文搜索**：`python search.py 奖学金` 直接搜标题和正文
- **可跳转简报**：Markdown 带锚点目录，GitHub / VS Code / Typora 都能点
- **周报**：`python fetch.py --weekly` 发最近 7 天汇总
- **邮件推送**：无额度限制，正文为 HTML，手机微信有提醒
- **容错**：单源失败不影响整体，自动重试，日志可查

## 快速开始

```bash
git clone <your-repo-url> && cd scut-notice
cp config.example.json config.json
# 编辑 config.json，填入 smtp 或 wecom_webhook
python fetch.py --days 30
```

> `config.json` 被 `.gitignore` 排除，未创建时脚本会提示先复制。

## 配置

| 字段 | 说明 |
|---|---|
| `sources` | 要抓的栏目。`type: "boda"`（HTML 列表）或 `type: "jw"`（JSON 接口） |
| `smtp` | 邮件推送。QQ 邮箱为 `smtp.qq.com` / 465 / 授权码 |
| `wecom_webhook` | 企业微信**内部群**机器人地址（可选） |
| `highlight_keywords` | 简报里标 ⭐ 的关键词列表 |
| `max_pages` | 每栏目最多翻几页，默认 3 |
| `delay` | 请求间隔秒数，默认 1.0，不建议调低 |

### 推送渠道

- **邮件**：填 `smtp.user` + `smtp.password`（授权码，非登录密码）。QQ 邮箱在「设置 → 账户 → 开启 IMAP/SMTP」生成
- **企业微信群机器人**：填 `wecom_webhook`。注意**外部群（含微信用户）不支持机器人**，必须是纯内部群

## 运行

```bash
python fetch.py                  # 日常：抓近 3 天，有新通知则推送
python fetch.py --days 30        # 回填 / 补发
python fetch.py --digest-only    # 不抓取，只从库重建简报
python fetch.py --weekly         # 周报（最近 7 天）
python fetch.py --limit 3 --no-push   # 调试
python fetch.py --no-attach      # 跳过附件下载

python search.py 奖学金           # 全文搜索
python search.py 期末 考试 --site 学院 --limit 5
```

### 定时（Windows）

```bat
schtasks /Create /F /TN "SCUT-Notice-Daily" /TR "wscript.exe \"D:\\path\\run_hidden.vbs\"" /SC DAILY /ST 07:30
```

配合启动项 `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\SCUT-Notice.vbs` 实现开机补跑（`--once-per-day` 保证同一天只跑一次）。

### 定时（Linux cron）

```cron
30 7 * * * cd /path/to/scut-notice && /usr/bin/python3 fetch.py >> logs/cron.log 2>&1
```

### 定时（GitHub Actions，无需开机）

仓库已带 `.github/workflows/daily.yml`（每天北京时间 07:30）和 `weekly.yml`（每周一早上周报）。

启用步骤：

1. 仓库 Settings → Secrets and variables → Actions，添加 `SMTP_USER`、`SMTP_PASS`
2. Actions 页面手动触发一次 `Daily Crawl` 验证
3. 数据库通过 `actions/cache` 跨运行保留，实现去重

> 注意：Actions 与本地计划任务**不要同时开**，两边数据库不共享，会造成重复推送。
> 国外 runner 访问学校站点可能较慢，首次运行建议手动触发观察。

## 文件

| 文件 | 作用 |
|---|---|
| `fetch.py` | 主脚本 |
| `search.py` | 全文搜索 |
| `config.json` | 本地配置（不提交） |
| `scut.sqlite` | 全部已抓通知（含正文） |
| `digest/YYYY-MM-DD.md` | 当日简报（带目录） |
| `data/YYYY-MM-DD.jsonl` | 当日新增原始记录 |
| `attachments/` | 下载的附件 |
| `logs/task.log` | 计划任务日志 |

## 数据说明

`.gitignore` 已排除 `config.json`、`scut.sqlite`、`data/`、`digest/`、`logs/`、`attachments/`。**提交前请确认没有把邮箱授权码或抓取数据带进仓库。**

## 免责声明

本项目仅用于个人学习与信息聚合，抓取的是学校公开发布的通知页面。请遵守目标站点的 robots.txt 与合理使用约定：脚本默认串行请求、间隔 1 秒，单次运行约 20~30 个请求。请勿提高频率或用于商业用途。

## 已知限制

- 电脑关机/睡眠时不运行（Windows 方案）；Linux 服务器或 GitHub Actions 可 7×24
- 本科生院部分通知详情是跳转页，需登录教务系统，只保存标题和链接
- 学院「学术通知」中有公众号文章外链，不抓正文
- 博达 CMS 列表排序不严格倒序，去重必须用 URL 里的内容 ID

## 踩过的坑

1. `www.scut.edu.cn` / `news.scut.edu.cn` 只接受 legacy cipher，OpenSSL 3.x 默认会
   `SSL: SSLV3_ALERT_HANDSHAKE_FAILURE`，必须 `CTX.set_ciphers("DEFAULT:@SECLEVEL=0")`
2. 本科生院首页列表是前端模板渲染的，真实数据在
   `POST /zhinan/cms/article/v2/findInformNotice.do`（category=0 通知公告 / 1 学院通知）
3. 博达 CMS 列表排序不严格倒序，去重必须用内容 ID，不能靠日期截断
4. 企业微信**外部群**不支持群机器人，自建应用也无法向群发消息

## License

MIT
