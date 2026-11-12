# 阿里云函数计算（国内出口）

两条路，按需选：

| 方案 | 用途 | 状态 |
|---|---|---|
| **A. 反向代理** | 只解决 GitHub Actions 访问本科生院 403，其余仍在 Actions 跑 | ✅ 已验证 |
| B. 全量迁移 | 整个抓取搬到阿里云（要 OSS 存库） | 备选 |

---

## 方案 A：反向代理（推荐）

### 背景

`jw.scut.edu.cn` 的 WAF 按 IP 地域拦截，GitHub 的境外 runner 会拿到 403。
用阿里云 FC 做一个 HTTP 反代，Actions 把 `JW_BASE` 指向它，出口就变成国内 IP。

### 1. 创建 Web 函数

阿里云 FC 控制台 → 创建函数 → **Web 函数**（不要选事件函数）。

| 项 | 值 |
|---|---|
| 函数名称 | `scut-jw-proxy` |
| 运行环境 | 自定义运行时 / Python 3.10 (Debian 11) |
| 代码上传方式 | 通过 ZIP 包上传代码 |
| 代码包 | `scut-jw-proxy.zip`（本目录，内含 `app.py`） |
| 启动命令 | `python3 app.py` |
| 监听端口 | `9000` |
| 执行超时 | 60 秒 |
| 规格 | 0.35 vCPU / 0.5 GB / 512 MB |
| **最小实例数** | **0**（设为 1 会常驻计费） |
| 单实例并发度 | 20 |

### 2. 网络配置（关键）

| 项 | 值 |
|---|---|
| 允许默认网卡访问公网 | **必须开启**，否则访问不了学校 |
| 允许访问 VPC | 关 |
| 挂载 NAS / OSS | 关 |
| 日志监控 | 建议开（免费额度够） |
| 链路追踪 | **关**（会产生费用） |
| 延时释放弹性实例 | **关**（会产生费用） |

### 3. 认证方式改成匿名

**这是最容易卡住的一步。** 创建后访问函数 URL 会返回：

```json
{"Code":"InvalidArgument","Message":"invalid authorization ''"}
```

说明函数 URL 在要求签名认证。去 **触发器 → defaultTrigger → 编辑**，把认证方式改成 **匿名认证**。

### 4. 未带 Date 头会返回 400

改匿名之前，还可能先遇到：

```json
{"Code":"MissingRequiredHeader","Message":"required HTTP header Date was not specified"}
```

阿里云 FC 的 HTTP 网关**强制要求请求带 `Date` 头**，而 `curl` 和 Python `urllib` 默认都不发。
`fetch.py` 已经在 `http_get` 里统一补上了 `Date`，自建脚本调用反代时也要注意。

### 5. 验证

```bash
curl -s -o /dev/null -w "%{http_code}" \
  https://你的函数URL/zhinan/cms/index.do
```

返回 `200` 即通。POST 接口验证：

```bash
curl -s -H "Date: $(date -u +'%a, %d %b %Y %H:%M:%S GMT')" \
  -H "Content-Type: application/x-www-form-urlencoded; charset=UTF-8" \
  --data "category=0&tag=&keyword=&pageNum=1&pageSize=2" \
  https://你的函数URL/zhinan/cms/article/v2/findInformNotice.do
```

### 6. 配置到 GitHub

仓库 Settings → Secrets → Actions → New repository secret：

| Name | Value |
|---|---|
| `JW_BASE` | `https://你的函数URL` |

`fetch.py` 会用它替换本科生院域名；留空则自动回落官方域名，不影响其他 8 个源。

### 验证结果

2026-11-12 实测：

```
[ 9/10] 本科生院/通知公告   列表 50  窗口内新增  4
[10/10] 本科生院/学院通知   列表 50  窗口内新增  0
数据源成功 10/10，本次新增 4 条
  邮件推送成功 -> 134***@qq.com
```

### 注意

- 反代是单点：函数挂了本科生院抓不到，其余 8 个源不受影响
- 免费额度的函数 URL 有 QPS 限制，本项目串行抓取，不会触发
- 学校看到的是阿里云机房 IP（深圳），与 Actions 出境 IP 不同

---

## 方案 B：全量迁移（备选）

如果想让整个抓取都在国内跑（含附件、正文、简报），需要解决持久化：

1. 阿里云 FC 定时触发（每天 07:30）
2. `scut.sqlite` 放 OSS，函数启动时下载到 `/tmp`、跑完上传
3. 环境变量注入 `SMTP_USER` / `SMTP_PASS`

代码已经预留：`cloud_handler.py` 支持环境变量注入凭据，`--only-jw` 可单独跑本科生院。
全量迁移还需要一个 OSS 读写层，尚未实现。
