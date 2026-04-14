---
name: x-twitter-scraper
description: "X/Twitter public data scraper without login. Supports user profile, recent timeline (≤20 tweets), and full tweet content (including Note Tweet long-form). Triggers: check Twitter user, view tweets, scrape X profile, search X. Not for: full history timeline (>20 tweets) or advanced search (requires login)."
tags: [twitter, x, scraping, social-media]
---

# X/Twitter 无登录数据抓取 V1

## 首次使用

首次使用前请运行依赖检测脚本：
```bash
bash scripts/setup.sh
```
> Agent 会在首次触发时自动执行此脚本，通常无需手动操作。

通过 X GraphQL API + guest token，**无需账号**抓取 X/Twitter 公开数据。

---

## ⚠️ Gotchas

> 遇到问题先看这里。

⚠️ **沙箱必须走代理** → 沙箱直连 x.com 可能超时。使用前设置环境变量 `X_PROXY`（如 `export X_PROXY=http://your-proxy:3128`），未设置时脚本直连。

⚠️ **普通 UA 获取 guest token 返回 403** → 必须用 Android UA（`TwitterAndroid/10.21.0-release.0`），脚本已处理，不要修改 UA。

⚠️ **Timeline 只返回最近约 20 条** → X GraphQL API 对未登录用户限制 timeline 深度，无法翻页拉取历史。需完整历史 → 需登录态（auth_token + ct0）。

⚠️ **搜索（search 命令）guest token 下几乎无效** → SearchTimeline endpoint 对 guest token 高度受限，通常返回空或 404。搜索需提供 X 登录 cookie。

⚠️ **GraphQL query ID 可能过期** → X 会不定期更新 endpoint 的 query ID。失效时删除 `scripts/.x_config.json`，升级 twikit（`pip install -U twikit`），再重新运行 `bash scripts/setup.sh` 即可自动提取最新值。

⚠️ **置顶推文不在 timeline 里** → 需用 profile 接口取 `pinned_tweet_ids_str`，再用 tweet 命令逐条获取。

---

## 🛑 Hard Stop

同一工具调用失败超过 3 次，立即停止，列出失败原因，标记 **"需要人工介入"**，等待人工确认。

---

## 场景映射表

| 用户说 | 执行命令 |
|--------|---------|
| 查 @_LuoFuli 的 X 主页 | `python3 x_scraper.py profile _LuoFuli` |
| 看 @某人 最新推文 | `python3 x_scraper.py timeline 某人 --count 10` |
| 获取这条推文的完整内容 | `python3 x_scraper.py tweet <tweet_id>` |
| 查置顶推文 | 先 `profile` 取 pinned_tweet_ids，再 `tweet <id>` |
| 搜推特（需登录）| `python3 x_scraper.py search "关键词"` ⚠️ guest 下受限 |
| 拿 JSON 数据做后续处理 | 任意命令加 `--json` 参数 |

---

## 快速开始

```bash
SKILL_DIR=$(find ~/.openclaw/skills ~/.openclaw/workspace/skills -name "x_scraper.py" 2>/dev/null | head -1 | xargs dirname)
pip install httpx -q

# 查用户
python3 $SKILL_DIR/x_scraper.py profile _LuoFuli

# 查最新推文
python3 $SKILL_DIR/x_scraper.py timeline elonmusk --count 5

# 查单条完整推文（含长文）
python3 $SKILL_DIR/x_scraper.py tweet 2034379957913129140

# JSON 输出
python3 $SKILL_DIR/x_scraper.py profile _LuoFuli --json
```

---

## GraphQL Endpoints 参考

Query IDs 由 `setup.sh` 运行时生成到 `scripts/.x_config.json`。支持的 endpoints：
- 用户信息（by handle / by ID）
- 用户 Timeline / 推文+回复
- 单条推文（含 Note Tweet 长文）
- 搜索 Timeline
- 关注者 / 正在关注

更新方式（query ID 过期时）：
```bash
rm scripts/.x_config.json
pip install -U twikit
bash scripts/setup.sh
```

---

## 技术原理

1. POST `api.twitter.com/1.1/guest/activate.json`（Android UA）→ 获取 guest token
2. GET `x.com/i/api/graphql/<query_id>/<endpoint>`（带 guest token + Bearer）→ 拿数据
3. 必须走上游代理（沙箱直连超时）

依赖：`httpx`（`pip install httpx`）
