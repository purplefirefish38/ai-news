"""
ニュース収集モジュール
RSSフィードおよびAnthropic公式ニュース等のWebページから最新記事を収集します。
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import requests
import feedparser
from dateutil import parser as date_parser
from lxml import html

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
}


def parse_date(date_str: Optional[str]) -> Optional[datetime]:
    """日付文字列をdatetime(UTC)に変換"""
    if not date_str:
        return None
    try:
        dt = date_parser.parse(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)
        return dt
    except Exception:
        return None


def fetch_rss_feed(feed_cfg: Dict[str, Any], hours_lookback: int) -> List[Dict[str, Any]]:
    """標準RSSフィードから記事を取得"""
    articles = []
    url = feed_cfg["url"]
    name = feed_cfg["name"]
    tag = feed_cfg.get("tag", "AI")
    category_desc = feed_cfg.get("category_desc", "ニュース")
    priority = feed_cfg.get("priority", 2)
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_lookback)

    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"Failed to fetch {name} ({url}): HTTP {resp.status_code}")
            return []

        parsed = feedparser.parse(resp.content)
        for entry in parsed.entries[:10]:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            raw_summary = entry.get("summary", "") or entry.get("description", "")
            
            # 日付取得
            pub_date = None
            if "published" in entry:
                pub_date = parse_date(entry.published)
            elif "updated" in entry:
                pub_date = parse_date(entry.updated)
            elif "pubDate" in entry:
                pub_date = parse_date(entry.pubDate)

            # 日時フィルタ（判定不能な場合は最新上位3件を採用）
            if pub_date and pub_date < cutoff_time:
                continue

            if title and link:
                articles.append({
                    "title": title,
                    "link": link,
                    "summary_raw": raw_summary[:400] if raw_summary else "",
                    "source_name": name,
                    "tag": tag,
                    "category_desc": category_desc,
                    "priority": priority,
                    "published_at": pub_date.isoformat() if pub_date else datetime.now(timezone.utc).isoformat()
                })
        
        # もし直近の記事が0件だった場合、最新3件をフォールバックとして取得
        if not articles and parsed.entries:
            for entry in parsed.entries[:3]:
                t = entry.get("title", "").strip()
                l = entry.get("link", "").strip()
                s = entry.get("summary", "") or entry.get("description", "")
                if t and l:
                    articles.append({
                        "title": t,
                        "link": l,
                        "summary_raw": s[:400] if s else "",
                        "source_name": name,
                        "tag": tag,
                        "category_desc": category_desc,
                        "priority": priority,
                        "published_at": datetime.now(timezone.utc).isoformat()
                    })

        logger.info(f"Fetched {len(articles)} articles from {name}")
    except Exception as e:
        logger.error(f"Error fetching RSS for {name}: {e}")

    return articles


def fetch_anthropic_news(feed_cfg: Dict[str, Any], hours_lookback: int) -> List[Dict[str, Any]]:
    """Anthropic公式ニュースページから直接スクレイピングして取得"""
    articles = []
    name = feed_cfg.get("name", "Anthropic News")
    url = feed_cfg.get("url", "https://www.anthropic.com/news")
    tag = feed_cfg.get("tag", "Claude / Anthropic")
    category_desc = feed_cfg.get("category_desc", "一次情報・公式")
    priority = feed_cfg.get("priority", 1)

    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"Failed to fetch Anthropic ({url}): HTTP {resp.status_code}")
            return []

        tree = html.fromstring(resp.content)
        news_links = tree.xpath('//a[starts-with(@href, "/news/")]')
        seen_links = set()

        for a in news_links:
            href = a.get("href", "")
            if not href or href == "/news" or href in seen_links:
                continue
            seen_links.add(href)

            full_link = f"https://www.anthropic.com{href}"
            raw_text = " ".join([t.strip() for t in a.itertext() if t.strip()])
            
            # テキストからタイトルや日付を推測
            if len(raw_text) < 15:
                continue

            title = raw_text
            parts = raw_text.split("Announcements ")
            if len(parts) > 1:
                title = parts[-1]
            elif "Product " in raw_text:
                title = raw_text.split("Product ")[-1]

            articles.append({
                "title": title,
                "link": full_link,
                "summary_raw": raw_text[:400],
                "source_name": name,
                "tag": tag,
                "category_desc": category_desc,
                "priority": priority,
                "published_at": datetime.now(timezone.utc).isoformat()
            })
            if len(articles) >= 3:
                break

        logger.info(f"Fetched {len(articles)} articles from Anthropic News")
    except Exception as e:
        logger.error(f"Error fetching Anthropic news: {e}")

    return articles


def collect_all_news(config_path: str = "config.json") -> List[Dict[str, Any]]:
    """設定ファイルに基づき全フィードから記事を収集・整理"""
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    hours_lookback = config.get("app", {}).get("hours_lookback", 48)
    feeds = config.get("feeds", [])
    
    all_articles = []
    seen_urls = set()

    for feed_cfg in feeds:
        if not feed_cfg.get("enabled", True):
            continue

        feed_type = feed_cfg.get("type", "rss")
        if feed_type == "anthropic_scraper":
            items = fetch_anthropic_news(feed_cfg, hours_lookback)
        else:
            items = fetch_rss_feed(feed_cfg, hours_lookback)

        for item in items:
            if item["link"] not in seen_urls:
                seen_urls.add(item["link"])
                all_articles.append(item)

    # 優先度順(小さいほど高優先度)、同じ優先度なら新しい順
    all_articles.sort(key=lambda x: (x["priority"], x["published_at"]), reverse=False)

    logger.info(f"Total collected unique articles: {len(all_articles)}")
    return all_articles


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    articles = collect_all_news()
    print(f"\n--- Preview of collected articles ({len(articles)}) ---")
    for i, a in enumerate(articles[:10], 1):
        print(f"[{i}] [{a['tag']}] {a['title']}")
        print(f"    URL: {a['link']}")
        print(f"    Date: {a['published_at']} | Priority: {a['priority']}\n")
