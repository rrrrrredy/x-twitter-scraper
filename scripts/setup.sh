#!/usr/bin/env bash
# setup.sh - 首次使用依赖检测、安装、运行时配置生成
# Usage: bash scripts/setup.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG_FILE="$SCRIPT_DIR/.x_config.json"

echo "🔍 检测依赖..."

MISSING=0

if ! python3 -c "import httpx" 2>/dev/null; then
  echo "📦 安装 httpx..."
  pip install -q httpx
  MISSING=1
fi

if ! python3 -c "import twikit" 2>/dev/null; then
  echo "📦 安装 twikit（用于提取运行时配置）..."
  pip install -q twikit
  MISSING=1
fi

if [ "$MISSING" -eq 0 ]; then
  echo "✅ 所有依赖已就绪"
else
  echo "✅ 依赖安装完成"
fi

# 从 twikit 包动态提取 Bearer Token + GraphQL endpoints 生成运行时配置
if [ ! -f "$CONFIG_FILE" ]; then
  echo "📝 从 twikit 提取运行时配置..."
  _X_CONFIG_PATH="$CONFIG_FILE" python3 << 'PYEOF'
import json, os
from twikit.constants import TOKEN
from twikit.client.gql import Endpoint

config = {
    "bearer": TOKEN,
    "proxy": os.environ.get("X_PROXY", ""),
    "gql": {
        "UserByScreenName": Endpoint.USER_BY_SCREEN_NAME.rsplit("/i/api/graphql/", 1)[-1],
        "UserTweets": Endpoint.USER_TWEETS.rsplit("/i/api/graphql/", 1)[-1],
        "UserTweetsAndReplies": Endpoint.USER_TWEETS_AND_REPLIES.rsplit("/i/api/graphql/", 1)[-1],
        "TweetResultByRestId": Endpoint.TWEET_RESULT_BY_REST_ID.rsplit("/i/api/graphql/", 1)[-1],
        "SearchTimeline": Endpoint.SEARCH_TIMELINE.rsplit("/i/api/graphql/", 1)[-1],
    }
}

with open(os.environ["_X_CONFIG_PATH"], "w") as f:
    json.dump(config, f, indent=2)
print("✅ 配置已写入 .x_config.json")
PYEOF
else
  echo "✅ 运行时配置已存在"
fi

# 最终验证
python3 -c "import httpx; print('验证通过: httpx')"
python3 -c "
import json
with open('$CONFIG_FILE') as f:
    cfg = json.load(f)
assert cfg.get('bearer'), 'Bearer token missing'
assert cfg.get('gql', {}).get('UserTweets'), 'GQL endpoints missing'
print('验证通过: 运行时配置')
"
echo "🎉 setup 完成，可以正常使用"
