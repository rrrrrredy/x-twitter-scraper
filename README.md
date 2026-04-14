# x-twitter-scraper

X/Twitter public data scraper without login — using Guest Token + GraphQL API.

An [OpenClaw](https://github.com/openclaw/openclaw) Skill for scraping public X/Twitter data without requiring an account.

## Installation

### Option A: OpenClaw (recommended)
```bash
# Clone to OpenClaw skills directory
git clone https://github.com/rrrrrredy/x-twitter-scraper ~/.openclaw/skills/x-twitter-scraper

# Run setup (installs dependencies + generates runtime config)
bash ~/.openclaw/skills/x-twitter-scraper/scripts/setup.sh
```

### Option B: Standalone
```bash
git clone https://github.com/rrrrrredy/x-twitter-scraper
cd x-twitter-scraper
bash scripts/setup.sh
```

## Dependencies

### Python packages
- `httpx` (`pip install httpx`)
- `twikit` (`pip install twikit`) — used by setup.sh to extract runtime config (Bearer Token + GraphQL endpoint IDs)

### Environment Variables (optional)
- `X_PROXY` — HTTP proxy URL (e.g., `http://your-proxy:3128`). Required if direct connection to x.com is blocked.
- `X_BEARER_TOKEN` — Override Bearer token (normally auto-extracted by setup.sh)

## Usage

### Get user profile
```bash
python3 scripts/x_scraper.py profile elonmusk
```

### Get recent tweets
```bash
python3 scripts/x_scraper.py timeline elonmusk --count 10
```

### Get full tweet content (including Note Tweet long-form)
```bash
python3 scripts/x_scraper.py tweet 1234567890123456789
```

### Search (limited under guest token)
```bash
python3 scripts/x_scraper.py search "AI agents" --count 5
```

### JSON output
```bash
python3 scripts/x_scraper.py profile elonmusk --json
```

## Limitations

- Guest token timeline returns ~20 recent tweets max (no pagination)
- Search is highly restricted under guest token (may return empty)
- GraphQL query IDs may expire — run `bash scripts/setup.sh` to refresh
- Only public tweets are accessible (no private/protected accounts)

## Project Structure

```
x-twitter-scraper/
├── SKILL.md              # Main skill definition
├── scripts/
│   ├── setup.sh          # Dependency install + runtime config generation
│   └── x_scraper.py      # Core scraping script (CLI)
└── README.md
```

## License

MIT
