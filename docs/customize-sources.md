# 自定义抓取源

本项目的所有栏目都写在 `config.json` 的 `sources` 数组里，添加/删除栏目只需要改配置，不用动代码。

## sources 的结构

每个栏目是一个对象，通用字段：

| 字段 | 必填 | 说明 |
|---|---|---|
| `site` | 是 | 分组名，出现在简报和邮件里的标题，如 `学校`、`学院`、`研究生院` |
| `column` | 是 | 栏目名，如 `校园新闻`、`招生通知` |
| `type` | 是 | 解析器类型：`boda`（HTML 列表页）或 `jw`（本科生院 JSON 接口） |

## 类型一：boda（博达 CMS 的 HTML 列表页）

**适用**：学校官网、各学院官网（`www.scut.edu.cn`、`www2.scut.edu.cn` 下的绝大多数栏目）。

**特征**：栏目页面以 `list.htm` 结尾，翻页是 `list2.htm`、`list3.htm`……

| 字段 | 说明 |
|---|---|
| `url` | 列表页第一页的完整地址 |
| `base` | 域名（用于补全相对链接），如 `https://www2.scut.edu.cn` |

**示例**：

```json
{
  "site": "学院",
  "column": "本科生通知",
  "type": "boda",
  "url": "https://www2.scut.edu.cn/ce/_t1674/bkstz/list.htm",
  "base": "https://www2.scut.edu.cn"
}
```

## 类型二：jw（本科生院的 JSON 接口）

**适用**：本科生院 `jw.scut.edu.cn`。它的首页是前端模板渲染的，HTML 里没有数据，必须走接口。

| 字段 | 说明 |
|---|---|
| `category` | `0` = 通知公告，`1` = 学院通知（各学院转发到本科生院的） |
| `tag` | 可选，细分标签：`1` 选课 / `2` 考试 / `3` 培养 / `4` 交流 / `5` 教师 / `6` 信息；留空表示全部 |

**示例**：

```json
{
  "site": "本科生院",
  "column": "通知公告",
  "type": "jw",
  "category": 0
}
```

> 只想看考试相关？加 `"tag": 2`，但注意这样会漏掉其他类型，通常建议留空。

## 完整示例：新增一个栏目

假设你想抓**研究生院**的招生通知：

1. 浏览器打开研究生院官网，找到「招生通知」栏目，点「更多」，确认地址以 `list.htm` 结尾（例如 `https://www2.scut.edu.cn/yjsy/xxxx/list.htm`）
2. 在 `config.json` 的 `sources` 数组里加一项：

```json
{
  "site": "研究生院",
  "column": "招生通知",
  "type": "boda",
  "url": "https://www2.scut.edu.cn/yjsy/xxxx/list.htm",
  "base": "https://www2.scut.edu.cn"
}
```

3. 测试（本地）：

```bash
python fetch.py --days 1 --no-push
```

日志里应该多出一行 `[11/11] 研究生院/招生通知  列表 N  窗口内新增 M`。

## 怎么快速判断该用哪种类型

| 现象 | 类型 |
|---|---|
| 页面地址以 `list.htm` 结尾，翻页是 `list2.htm` | **boda** |
| 看网页源码，列表内容直接写在 HTML 里 | **boda** |
| 看网页源码，列表是 `{{value.xxx}}` 这样的模板占位符 | 前端渲染，找它的 JSON 接口 → **jw** 或需要新增 parser |

## 常见问题

**Q：加了栏目但抓不到内容？**

- 先确认地址是列表页本身，不是首页或详情页
- 如果列表内容在浏览器里能看到、但源码里没有，说明是 JS 渲染，需要找接口（参考 `fetch.py` 里 `parse_jw` 的写法）

**Q：抓到的条目数量比页面上少？**

- 检查 `max_pages`（默认 3 页）
- 检查时间窗：`--days` 越小抓得越少，回填用 `--days 30`

**Q：日期识别不到？**

- 脚本会在每条链接后 500 字符内找 `YYYY-MM-DD`、`YYYY.MM.DD`、`YYYY/MM/DD` 形式的日期
- 如果目标站点的日期格式不同（比如只有「11月12日」没有年份），需要在 `parse_boda` 里扩充

**Q：想抓的站点既不是博达也不是本科生院？**

- 需要在 `fetch.py` 里新增一个 `parse_xxx` 解析器，再在 `main()` 的分支里加一个 `type`
- 主体流程（去重、正文、入库、推送）都是通用的，只需要写「列表页 → 条目数组」这一段

## 改完之后

- **本地方式**：直接跑 `python fetch.py` 即可
- **Actions 方式**：push 到仓库，Actions 下次运行自动用新配置（无需改 workflow）
