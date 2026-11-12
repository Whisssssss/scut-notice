# SCUT Notice Crawler · 华南理工大学通知抓取

每天自动抓取华南理工大学的通知，包含增量去重、正文入库、生成带目录的简报等功能。

可以推送到邮箱（**推荐使用QQ邮箱并绑定微信，这样微信就会每天推送新通知**）。

纯 Python 标准库实现，**零第三方依赖**。

>给化院的本科生同学用的，会抓化院的网页消息♥

>想要自定义扒取源的[**点这里**](docs/customize-sources.md)。

## 抓取范围

| 站点 | 栏目 | 数量 |
|---|---|---|
| 学校首页 | 校园新闻、教学科研通知、学术预告 | 3 |
| 化学与化工学院 | 公务通知、教务通知、学术通知、本科生通知、研究生通知 | 5 |
| 本科生院 | 通知公告、学院通知 | 2 |

共 **10 个数据源**。栏目可在 `config.json` 的 `sources` 里增删。

## 特性

- **增量去重**：以内容 ID 为主键，重复运行不重复入库、不重复推送
- **正文入库**：正文存进 SQLite，支持全文搜索
- **关键词提醒**：标题命中关注词（考试 / 选课 / 奖学金 …）的条目标 ⭐
- **附件下载**：通知里的 pdf / xlsx / zip 一并保存到 `attachments/`
- **可跳转简报**：Markdown 带锚点目录，GitHub / VS Code / Typora 都能点
- **周报**：`--weekly` 生成最近 7 天汇总
- **邮件推送**：无额度限制，HTML 正文，手机微信有提醒
- **容错**：单源失败不影响整体，自动重试，日志可查

## 两种使用方式

| 方式 | 适合谁 | 环境 | 常驻设备 |
|---|---|---|---|
| **[本地运行](#method-local)** | 自用、完全掌控 | 本地设备(Python 3.8+) | 需要 |
| **[Github Actions](#method-actions)** | 长期自动 | GitHub 账号 + 阿里云反代（免费额度够用） | 不需要 |

两种方式共用同一套 `fetch.py`，区别只在“谁来定时”和“谁去访问学校网站”。

**注意**：两种方法不要双开，不然一天会收到两封完全相同的邮件

---

<a id="method-local"></a>

# 方式一：本地运行

## 1. 准备

```bash
git clone https://github.com/Whisssssss/scut-notice.git
cd scut-notice
python --version        # 需要 3.8 及以上
```

没有 Git 也可以直接在仓库页面点 **Code → Download ZIP** 解压。

## 2. 配置

```bash
cp config.example.json config.json
```

编辑 `config.json`，最小改动是邮件推送这一段：

```json
"smtp": {
  "host": "smtp.qq.com",
  "port": 465,
  "user": "你的QQ邮箱@qq.com",
  "password": "QQ邮箱授权码",
  "to": "你的QQ邮箱@qq.com"
}
```

授权码获取：电脑登录 [mail.qq.com](https://mail.qq.com)(或者你的目标邮箱) → 设置 → 账户 → 开启「IMAP/SMTP 服务」→ 生成授权码。**注意不是 QQ 密码。**

不填 `smtp` 也可以用，只是不能推送，抓下来的通知只存到本地。

## 3. 运行

```bash
python fetch.py --days 30        # 首次：回填最近 30 天
python fetch.py                  # 日常：抓近 3 天，有新通知才推送
python fetch.py --digest-only    # 只重建简报，不抓取
python fetch.py --weekly         # 最近 7 天周报
python search.py 奖学金          # 全文搜索标题和正文
python search.py 期末 考试 --site 学院
```

Windows 上也可以双击 `run.bat`。

## 4. 定时（**Windows**系统）

** A：计划任务（每天固定时间）**

```bat
schtasks /Create /F /TN "SCUT-Notice-Daily" /TR "wscript.exe \"D:\\path\\to\\scut-notice\\run_hidden.vbs\"" /SC DAILY /ST 07:30
```

** B：开机自启（登录时补跑）**

把 `run_hidden.vbs` 的快捷方式放进启动文件夹：

```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
```

`run_task.bat` 带 `--once-per-day`，同一天只真正跑一次，不会重复推送。

删除定时：

```bat
schtasks /Delete /TN "SCUT-Notice-Daily" /F
```

## 5. 定时（**Linux**）

```cron
30 7 * * * cd /path/to/scut-notice && /usr/bin/python3 fetch.py >> logs/cron.log 2>&1
```

> `run.bat` / `run_hidden.vbs` / `run_task.bat` 是 Windows 专用，Linux 直接跑 `python3 fetch.py`。

---

<a id="method-actions"></a>

# 方式二：GitHub Actions（推荐）

电脑关机也能跑，零成本。

## 为什么还需要一台阿里云函数 

`jw.scut.edu.cn`（本科生院）的 WAF **按 IP 地域拦截**：GitHub 的 runner 都在境外，直接访问返回 **403**。

解决办法是用阿里云函数计算做一次国内转发（免费额度内），Actions 通过它访问本科生院：

```
GitHub Actions（境外） → 阿里云 FC（深圳） → jw.scut.edu.cn
```

其余 8 个源（学校、学院）不需要转发，Actions 直连即可。

>注：一个号的免费额度理论上够1000+人每月用，但是不知道学校会不会封高频访问ip，不过小范围共享给好哥们/姐们用没问题。

## 1. Fork 仓库

右上角 **Fork** → 选自己的账号。fork 出来的仓库 **默认不启用 Actions**。

## 2. 启用 Actions

进入你 fork 仓库的 **Actions** 页面，点击绿色的：

```
I understand my workflows, go ahead and enable them
```

## 3. 去掉 owner 限制

打开 `.github/workflows/daily.yml` 和 `weekly.yml`，找到这一行：

```yaml
if: github.repository_owner == 'Whisssssss'
```

改成你的 GitHub 用户名，或整行删除（连同上一行注释）。**不改的话 job 会被直接跳过。**

## 4. 部署阿里云反代

### 4.1 创建 Web 函数

登录 [函数计算控制台](https://fc.console.aliyun.com/)（首次进入会提示开通，有免费额度）。

**创建函数 → 选择「Web 函数」**（不是事件函数），按下表填写：

| 配置项 | 值 |
|---|---|
| 地域 | 华南1（深圳）或其他国内地域 |
| 函数名称 | `scut-jw-proxy` |
| 运行环境 | 自定义运行时 / Python 3.10 |
| 代码上传方式 | 通过 ZIP 包上传代码 |
| 代码包 | 根目录的 `scut-jw-proxy.zip` |
| 启动命令 | `python3 app.py` |
| 监听端口 | `9000` |
| 执行超时 | 60 秒 |
| 规格 | 0.35 vCPU / 0.5 GB |
| 最小实例数 | **0**（设成 1 会常驻计费） |
| 单实例并发度 | 20 |

**高级配置**：

| 配置项 | 值 | 说明 |
|---|---|---|
| 允许默认网卡访问公网 | **必须开启** | 关闭则访问不了学校，返回 502 |
| 允许访问 VPC | 关 | |
| 挂载 NAS / OSS | 关 | |
| 日志监控 | 建议开 | 免费额度够用 |
| 链路追踪 | **关** | 会产生费用 |
| 延时释放弹性实例 | **关** | 会产生费用 |
| 时区 | Asia/Shanghai | 日志时间用北京时间 |
| 函数角色 / 环境变量 | 不用配 | 反代没有依赖 |

> `scut-jw-proxy.zip` 里只有一个 `app.py`（标准库写成的 HTTP 反代），不含任何凭据。

### 4.2 认证方式改成匿名

**这是最容易卡住的一步。** 创建后如果访问函数 URL 返回：

```json
{"Code":"InvalidArgument","Message":"invalid authorization ''"}
```

说明函数 URL 在要求签名认证。去 **触发器 → defaultTrigger → 编辑**，把认证方式改成 **匿名认证**。

### 4.3 验证反代

拿到函数 URL（形如 `https://scut-jw-proxy-xxxxx.cn-shenzhen.fcapp.run`）后：

```bash
curl -s -o /dev/null -w "%{http_code}" \
  https://你的函数URL/zhinan/cms/index.do
```

返回 `200` 即通。

> `fetch.py` 已自动补 `Date` 请求头——阿里云 FC 的网关强制要求，curl 和 urllib 默认都不发。

## 5. 配置 Secrets

仓库 **Settings → Secrets and variables → Actions → New repository secret**，添加三个：

| Name | Value | 必填 |
|---|---|---|
| `SMTP_USER` | 你的 QQ 邮箱 | 是 |
| `SMTP_PASS` | QQ 邮箱授权码 | 是 |
| `JW_BASE` | 反代函数 URL | 是（否则本科生院 403） |

> 没配 `JW_BASE` 也能跑，只是本科生院两个源会失败（8/10）；其余 8 个不受影响。

## 6. 手动验证

**Actions → Daily Crawl → Run workflow**。约 1 分钟，日志里确认：

```
[ 9/10] 本科生院/通知公告   列表 50  窗口内新增  N
[10/10] 本科生院/学院通知   列表 50  窗口内新增  M
数据源成功 10/10，本次新增 X 条
  邮件推送成功 -> ******@**.com
库内 22 条，正文为空 0 条
```

## 7. 定时

`daily.yml` 已内置：每天北京时间 **07:30**（`cron: '30 23 * * *'`，UTC）。
`weekly.yml`：每周一早上发周报。

数据库通过 `actions/cache` 跨运行保留（key 前缀 `db-`），首次运行是空库、会回填，之后只推增量。

> **不要同时开本地计划任务和 Actions**，两边数据库不共享，会重复推送。

---

## 配置说明（config.json）

| 字段 | 说明 |
|---|---|
| `sources` | 要抓的栏目。`type: "boda"`（HTML 列表）或 `type: "jw"`（JSON 接口） |
| `smtp` | 邮件推送。QQ 邮箱为 `smtp.qq.com` / 465 / 授权码 |
| `wecom_webhook` | 企业微信**内部群**机器人地址（可选） |
| `highlight_keywords` | 简报里标 ⭐ 的关键词列表 |
| `max_pages` | 每栏目最多翻几页，默认 3 |
| `delay` | 请求间隔秒数，默认 1.0，不建议调低 |

## 命令参考

| 命令 | 作用 |
|---|---|
| `python fetch.py` | 抓近 3 天，有新通知则推送 |
| `python fetch.py --days 30` | 回填 / 补发 |
| `python fetch.py --digest-only` | 只从库重建简报 |
| `python fetch.py --weekly` | 最近 7 天周报 |
| `python fetch.py --only-jw` | 只跑本科生院 |
| `python fetch.py --refetch-empty` | 补抓正文为空的条目 |
| `python fetch.py --limit 3 --no-push` | 调试 |
| `python fetch.py --no-attach` | 跳过附件下载 |
| `python search.py 关键词` | 全文搜索 |

## 文件结构

```
scut-notice/
├── fetch.py                主脚本
├── search.py               全文搜索
├── config.example.json     配置模板（复制为 config.json 使用）
├── scut-jw-proxy.zip       阿里云反代上传包（方式二用）
├── cloud/app.py            反代源码（zip 里的那个文件）
├── run.bat                 本地双击运行
├── run_task.bat            计划任务调用（带每日去重）
├── run_hidden.vbs          隐藏窗口启动
├── .github/workflows/      Actions 流水线
├── scut.sqlite             本地数据库（不提交）
├── digest/                 每日简报（不提交）
├── data/                   原始记录（不提交）
├── attachments/            下载的附件（不提交）
└── logs/                   运行日志（不提交）
```

## 数据与隐私

`.gitignore` 已排除 `config.json`、`scut.sqlite`、`data/`、`digest/`、`attachments/`、`logs/`。

**提交前请确认没有把邮箱授权码或抓取数据带进仓库。** 公开仓库的 Actions 日志任何人可读，脚本已对邮箱做打码（`134***@qq.com`）。

## 免责声明

本项目仅用于个人学习与信息聚合，抓取的是学校公开发布的通知页面。请遵守目标站点的 robots.txt 与合理使用约定：脚本默认串行请求、间隔 1 秒，单次运行约 20~30 个请求。请勿提高频率或用于商业用途。

## 已知限制

- 方式一在电脑关机/睡眠时不运行；方式二不受影响
- GitHub Actions 的 runner 在境外，本科生院必须经国内反代（方式二的方式）
- 本科生院部分通知详情是跳转页，需登录教务系统，只保存标题和链接
- 学院「学术通知」中有公众号文章外链，不抓正文
- 博达 CMS 列表排序不严格倒序，去重必须用 URL 里的内容 ID

## 踩坑记录

1. `www.scut.edu.cn` / `news.scut.edu.cn` 只接受 legacy cipher，OpenSSL 3.x 默认会
   `SSL: SSLV3_ALERT_HANDSHAKE_FAILURE`，必须 `CTX.set_ciphers("DEFAULT:@SECLEVEL=0")`
2. 本科生院首页列表是前端模板渲染的，真实数据在
   `POST /zhinan/cms/article/v2/findInformNotice.do`（category=0 通知公告 / 1 学院通知）
3. 博达 CMS 列表排序不严格倒序，去重必须用内容 ID，不能靠日期截断
4. 企业微信**外部群**不支持群机器人，自建应用也无法向群发消息
5. 阿里云 FC 的 HTTP 网关**强制要求请求带 `Date` 头**，缺了返回 `MissingRequiredHeader`
6. 阿里云 FC 的函数 URL 默认可能要求签名认证，需手动改成**匿名认证**，否则返回 `invalid authorization ''`
7. 启用反代后，`ext`（是否外链）**不能只判断 `scut.edu.cn`**——反代域名不含这个字符串，会被误判为外链而静默跳过正文抓取。代码已改为同时识别 `JW_BASE` 前缀

## License

MIT
