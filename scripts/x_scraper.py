#!/usr/bin/env python3
"""
X/Twitter 无登录公开数据抓取脚本
使用 Guest Token + GraphQL API，无需账号

用法:
  python3 x_scraper.py profile <handle>
  python3 x_scraper.py timeline <handle> [--count 20]
  python3 x_scraper.py tweet <tweet_id>
  python3 x_scraper.py search <query> [--count 10]

全局参数:
  --json      以 JSON 格式输出
  --proxy URL 覆盖默认代理（或设置 X_PROXY 环境变量）
"""

import argparse
import json
import os
import sys
import httpx

# ── 常量 ──────────────────────────────────────────────────────────────────────
# 运行时配置从外部文件加载（setup.sh 生成），避免高熵字符串硬编码
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_FILE = os.path.join(_SCRIPT_DIR, ".x_config.json")

def _load_config():
    """从 .x_config.json 加载运行时配置（Bearer Token + GQL endpoints）"""
    if os.path.exists(_CONFIG_FILE):
        with open(_CONFIG_FILE) as f:
            return json.load(f)
    # 回退：从环境变量读取
    return {}

_CFG = _load_config()
BEARER = os.environ.get("X_BEARER_TOKEN", _CFG.get("bearer", ""))
ANDROID_UA = "TwitterAndroid/10.21.0-release.0 (310210000-r-0) ONEPLUS+A3010/9 (OnePlus;ONEPLUS+A3010;OnePlus;OnePlus3;0;;1;2016)"
# 代理地址：从环境变量读取，未设置时留空（直连）
DEFAULT_PROXY = os.environ.get("X_PROXY", _CFG.get("proxy", ""))

# GraphQL endpoint query IDs（运行时从配置加载）
GQL = _CFG.get("gql", {
    "UserByScreenName":    "",
    "UserTweets":          "",
    "UserTweetsAndReplies":"",
    "TweetResultByRestId": "",
    "SearchTimeline":      "",
})

USER_FEATURES = {
    "hidden_profile_likes_enabled": True,
    "hidden_profile_subscriptions_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "subscriptions_verification_info_is_identity_verified_enabled": True,
    "subscriptions_verification_info_verified_since_enabled": True,
    "highlights_tweets_tab_ui_enabled": True,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
}

TWEET_FEATURES = {
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}


# ── HTTP 客户端 ────────────────────────────────────────────────────────────────
def make_client(proxy: str) -> httpx.Client:
    if proxy:
        transport = httpx.HTTPTransport(proxy=proxy)
        return httpx.Client(transport=transport, timeout=15, follow_redirects=True)
    return httpx.Client(timeout=15, follow_redirects=True)


def get_guest_token(client: httpx.Client) -> str:
    """获取 guest token（必须用 Android UA，否则 403）"""
    r = client.post(
        "https://api.twitter.com/1.1/guest/activate.json",
        headers={"Authorization": f"Bearer {BEARER}", "User-Agent": ANDROID_UA},
    )
    r.raise_for_status()
    return r.json()["guest_token"]


def gql_headers(guest_token: str) -> dict:
    return {
        "Authorization": f"Bearer {BEARER}",
        "x-guest-token": guest_token,
        "User-Agent": ANDROID_UA,
        "x-twitter-client-language": "en",
        "x-twitter-active-user": "yes",
        "Content-Type": "application/json",
    }


def gql_get(client, endpoint_key, variables, features, guest_token):
    path = GQL[endpoint_key]
    r = client.get(
        f"https://x.com/i/api/graphql/{path}",
        params={
            "variables": json.dumps(variables),
            "features": json.dumps(features),
        },
        headers=gql_headers(guest_token),
    )
    r.raise_for_status()
    return r.json()


# ── 解析工具 ───────────────────────────────────────────────────────────────────
def extract_tweet_text(tweet_result: dict) -> str:
    """从 tweet result 中提取正文，优先取 note_tweet 长文"""
    legacy = tweet_result.get("legacy", {})
    note = tweet_result.get("note_tweet", {}).get("note_tweet_results", {}).get("result", {})
    if note:
        return note.get("text", legacy.get("full_text", ""))
    return legacy.get("full_text", "")


def parse_tweet(entry) -> dict | None:
    """从 timeline entry 解析推文"""
    try:
        content = entry.get("content", {})
        item_content = content.get("itemContent", content)
        tweet_result = item_content.get("tweet_results", {}).get("result", {})
        if not tweet_result or tweet_result.get("__typename") == "TweetUnavailable":
            return None
        legacy = tweet_result.get("legacy", {})
        if not legacy:
            return None
        return {
            "id": legacy.get("id_str"),
            "created_at": legacy.get("created_at"),
            "text": extract_tweet_text(tweet_result),
            "likes": legacy.get("favorite_count", 0),
            "retweets": legacy.get("retweet_count", 0),
            "replies": legacy.get("reply_count", 0),
            "views": tweet_result.get("views", {}).get("count", "?"),
            "is_retweet": "retweeted_status_result" in legacy,
        }
    except Exception:
        return None


def flatten_timeline(data: dict) -> list[dict]:
    """从 UserTweets 响应中提取推文列表"""
    tweets = []
    try:
        instructions = (
            data["data"]["user"]["result"]["timeline_v2"]["timeline"]["instructions"]
        )
        for inst in instructions:
            for entry in inst.get("entries", []):
                t = parse_tweet(entry)
                if t:
                    tweets.append(t)
                # TimelineAddToModule（推文+回复）
                for item in entry.get("content", {}).get("items", []):
                    t = parse_tweet(item)
                    if t:
                        tweets.append(t)
    except (KeyError, TypeError):
        pass
    return tweets


# ── 子命令实现 ─────────────────────────────────────────────────────────────────
def cmd_profile(args):
    with make_client(args.proxy) as client:
        gt = get_guest_token(client)
        data = gql_get(client, "UserByScreenName",
            {"screen_name": args.handle, "withSafetyModeUserFields": True},
            USER_FEATURES, gt)

    user = data["data"]["user"]["result"]
    legacy = user["legacy"]
    result = {
        "id": user["rest_id"],
        "handle": legacy["screen_name"],
        "name": legacy["name"],
        "bio": legacy.get("description", ""),
        "followers": legacy.get("followers_count", 0),
        "following": legacy.get("friends_count", 0),
        "tweets_count": legacy.get("statuses_count", 0),
        "verified": legacy.get("verified", False),
        "blue_verified": user.get("is_blue_verified", False),
        "location": legacy.get("location", ""),
        "created_at": legacy.get("created_at", ""),
        "profile_url": f"https://x.com/{legacy['screen_name']}",
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"@{result['handle']} ({result['name']})")
        print(f"ID: {result['id']}")
        print(f"Bio: {result['bio']}")
        print(f"Followers: {result['followers']:,} | Following: {result['following']:,} | Tweets: {result['tweets_count']:,}")
        print(f"Blue Verified: {result['blue_verified']} | Location: {result['location']}")
        print(f"Joined: {result['created_at']}")


def cmd_timeline(args):
    with make_client(args.proxy) as client:
        gt = get_guest_token(client)
        # 先获取 user ID
        user_data = gql_get(client, "UserByScreenName",
            {"screen_name": args.handle, "withSafetyModeUserFields": True},
            USER_FEATURES, gt)
        user_id = user_data["data"]["user"]["result"]["rest_id"]

        data = gql_get(client, "UserTweets", {
            "userId": user_id,
            "count": args.count,
            "includePromotedContent": False,
            "withQuickPromoteEligibilityTweetFields": True,
            "withVoice": True,
            "withV2Timeline": True,
        }, TWEET_FEATURES, gt)

    tweets = flatten_timeline(data)

    if args.json:
        print(json.dumps(tweets, ensure_ascii=False, indent=2))
    else:
        print(f"@{args.handle} 的最近推文（{len(tweets)} 条）\n")
        for t in tweets:
            print(f"[{t['created_at']}] ID:{t['id']}")
            print(f"  {t['text'][:200]}{'...' if len(t['text']) > 200 else ''}")
            print(f"  ❤️ {t['likes']}  🔁 {t['retweets']}  💬 {t['replies']}  👁 {t['views']}")
            print()


def cmd_tweet(args):
    with make_client(args.proxy) as client:
        gt = get_guest_token(client)
        data = gql_get(client, "TweetResultByRestId", {
            "tweetId": args.tweet_id,
            "withCommunity": False,
            "includePromotedContent": False,
            "withVoice": False,
        }, TWEET_FEATURES, gt)

    # X API 有时返回 tweetResult，有时返回 tweet_result
    raw = data.get("data", {})
    tweet_result = (raw.get("tweetResult") or raw.get("tweet_result") or {}).get("result", {})
    legacy = tweet_result.get("legacy", {})
    result = {
        "id": legacy.get("id_str"),
        "created_at": legacy.get("created_at"),
        "text": extract_tweet_text(tweet_result),
        "likes": legacy.get("favorite_count", 0),
        "retweets": legacy.get("retweet_count", 0),
        "replies": legacy.get("reply_count", 0),
        "views": tweet_result.get("views", {}).get("count", "?"),
        "author": tweet_result.get("core", {}).get("user_results", {}).get("result", {}).get("legacy", {}).get("screen_name", ""),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Tweet by @{result['author']} [{result['created_at']}]")
        print(f"\n{result['text']}\n")
        print(f"❤️ {result['likes']}  🔁 {result['retweets']}  💬 {result['replies']}  👁 {result['views']}")


def cmd_search(args):
    """搜索（guest token 下功能受限，可能返回空或被 429）"""
    with make_client(args.proxy) as client:
        gt = get_guest_token(client)
        data = gql_get(client, "SearchTimeline", {
            "rawQuery": args.query,
            "count": args.count,
            "querySource": "typed_query",
            "product": "Latest",
        }, TWEET_FEATURES, gt)

    # 解析搜索结果（结构与 UserTweets 类似）
    tweets = []
    try:
        instructions = data["data"]["search_by_raw_query"]["search_timeline"]["timeline"]["instructions"]
        for inst in instructions:
            for entry in inst.get("entries", []):
                t = parse_tweet(entry)
                if t:
                    tweets.append(t)
    except (KeyError, TypeError):
        pass

    if not tweets:
        msg = "搜索结果为空（guest token 下搜索功能受限，建议提供登录态）"
        if args.json:
            print(json.dumps({"error": msg, "tweets": []}, ensure_ascii=False))
        else:
            print(f"⚠️ {msg}")
        return

    if args.json:
        print(json.dumps(tweets, ensure_ascii=False, indent=2))
    else:
        print(f"搜索「{args.query}」结果（{len(tweets)} 条）\n")
        for t in tweets:
            print(f"[{t['created_at']}] ID:{t['id']}")
            print(f"  {t['text'][:200]}{'...' if len(t['text']) > 200 else ''}")
            print(f"  ❤️ {t['likes']}  🔁 {t['retweets']}  💬 {t['replies']}")
            print()


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="X/Twitter 无登录数据抓取")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    parser.add_argument("--proxy", default=DEFAULT_PROXY, help="HTTP 代理地址")

    subs = parser.add_subparsers(dest="cmd", required=True)

    p_profile = subs.add_parser("profile", help="获取用户 profile")
    p_profile.add_argument("handle", help="Twitter handle（不含@）")

    p_timeline = subs.add_parser("timeline", help="获取用户推文列表")
    p_timeline.add_argument("handle", help="Twitter handle（不含@）")
    p_timeline.add_argument("--count", type=int, default=20, help="获取推文数（最多约20条）")

    p_tweet = subs.add_parser("tweet", help="获取单条推文完整内容")
    p_tweet.add_argument("tweet_id", help="推文 ID")

    p_search = subs.add_parser("search", help="关键词搜索（guest token 下受限）")
    p_search.add_argument("query", help="搜索关键词")
    p_search.add_argument("--count", type=int, default=10, help="结果数量")

    args = parser.parse_args()

    dispatch = {
        "profile": cmd_profile,
        "timeline": cmd_timeline,
        "tweet": cmd_tweet,
        "search": cmd_search,
    }
    try:
        dispatch[args.cmd](args)
    except httpx.HTTPStatusError as e:
        print(f"HTTP 错误 {e.response.status_code}: {e.response.text[:300]}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
