# 国内云函数补跑（本科生院）

GitHub Actions 的 runner 在国外，jw.scut.edu.cn 会返回 403。
用国内云函数补跑这两个源，免费额度足够（每天一次、每次几秒）。

## 1. 生成上传包

Windows 上执行：

    powershell -ExecutionPolicy Bypass -File make_cloud_package.ps1

产物 cloud/scut-jw-fc.zip，含 fetch.py / cloud_handler.py / config.json 三个文件，
不含任何凭据（凭据通过环境变量注入）。

## 2. 阿里云函数计算 FC

1. 打开函数计算控制台 fc.console.aliyun.com，首次进入会提示开通（有免费额度）
2. 创建函数 → 从头创建
   - 函数名称：scut-jw
   - 运行环境：Python 3.10
   - 请求处理程序：cloud_handler.handler
   - 代码上传：选择 scut-jw-fc.zip
   - 内存：128 MB，超时：120 秒
3. 环境变量（函数配置 → 环境变量）
   - SMTP_USER = 你的 QQ 邮箱
   - SMTP_PASS = 邮箱授权码
4. 触发器 → 创建触发器 → 定时触发器
   - 触发方式：Cron
   - 表达式：0 40 7 * * *（6 段：秒 分 时 日 月 周，每天 07:40 北京时间）
5. 保存后点测试，手动跑一次，看日志里有没有『数据源成功 2/10』和『邮件推送成功』

## 3. 腾讯云云函数 SCF（备选）

1. 打开 console.cloud.tencent.com/scf，新建函数 → 空白函数
2. 运行环境 Python 3.10，提交方法选上传 zip 包，选 scut-jw-fc.zip
3. 入口函数填 cloud_handler.main_handler
4. 函数配置 → 环境变量，同样加 SMTP_USER / SMTP_PASS
5. 触发器 → 定时触发器，Cron 表达式是 7 段：0 40 7 * * * *
6. 测试一次看日志

## 为什么不会重复推送

云函数每次都是全新实例，没有持久数据库，所以它跑的是：

    python fetch.py --only-jw --days 2 --no-attach --only-yesterday

--days 2 只用来抓取列表，--only-yesterday 保证只推送昨天发布的通知。
今天跑推昨天的、明天跑推今天的，窗口互不重叠，不会重复。
代价是延迟一天；公示类通知通常有 3 天时效，可以接受。

## 与 Actions 的分工

| 渠道 | 负责 | 时间 |
|---|---|---|
| GitHub Actions | 学校 3 个源 + 学院 5 个源（8/10） | 每天 07:30 |
| 国内云函数 | 本科生院 2 个源，只发昨天的 | 每天 07:40 |
