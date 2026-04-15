# x-twitter-scraper

X/Twitter public data scraper — no login required.

> OpenClaw Skill — works with [OpenClaw](https://github.com/openclaw/openclaw) AI agents

## What It Does

Scrapes public X/Twitter data using the GraphQL API with guest tokens — no account needed. Supports fetching user profiles, recent timelines (up to ~20 tweets), and full single-tweet content including Note Tweet long-form text. Outputs clean text or structured JSON.

## Quick Start

```bash
openclaw skill install x-twitter-scraper
# Or:
git clone https://github.com/rrrrrredy/x-twitter-scraper.git ~/.openclaw/skills/x-twitter-scraper
```

Run dependency setup on first use:
```bash
bash scripts/setup.sh
pip install httpx -q
```

## Features

- **No login required**: guest token authentication for public data
- **User profiles**: followers, following, bio, pinned tweets
- **Timeline scraping**: up to ~20 most recent tweets per user
- **Full tweet content**: includes Note Tweet long-form text
- **JSON output**: add `--json` flag for structured data
- **Auto-updatable**: GraphQL query IDs refreshable via setup script
- **Hard stop protection**: auto-stops after 3 consecutive failures

## Usage

Trigger with natural language:

- "查 @elonmusk 的 X 主页"
- "看 @某人 最新推文"
- "获取这条推文的完整内容"
- "查 X 动态" / "看推特"

CLI examples:
```bash
python3 scripts/x_scraper.py profile _LuoFuli
python3 scripts/x_scraper.py timeline elonmusk --count 5
python3 scripts/x_scraper.py tweet 2034379957913129140
python3 scripts/x_scraper.py profile _LuoFuli --json
```

## Project Structure

```
x-twitter-scraper/
├── SKILL.md              # Skill definition and workflow
├── scripts/
│   ├── setup.sh          # Dependency setup & query ID extraction
│   └── x_scraper.py      # Main scraper CLI tool
├── README.md
├── LICENSE
└── .gitignore
```

## Requirements

- OpenClaw agent runtime
- Python 3 with `httpx` (`pip install httpx`)
- Upstream proxy for X API access (set `X_PROXY` env var)

## License

[MIT](LICENSE)
