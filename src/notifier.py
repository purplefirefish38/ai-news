"""
通知モジュール
Discord Webhook および LINE Messaging API へ最新ニュースとWeb版リンクを配信します。
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)


def send_discord_notification(summaries: List[Dict[str, Any]], web_url: Optional[str] = None) -> bool:
    """Discord Webhook経由でリッチなEmbedメッセージを送信"""
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        logger.info("DISCORD_WEBHOOK_URL is not set. Skipping Discord notification.")
        return False

    embeds = []
    # Discordの1メッセージあたり最大10個のEmbed
    for item in summaries[:10]:
        title = item.get("title_ja", item.get("title", ""))
        headline = item.get("headline", "")
        points = item.get("points", [])
        tag = item.get("tag", "AI")
        source = item.get("source", "Web")
        url = item.get("url", "")

        desc = f"**⚡ {headline}**\n\n"
        for p in points:
            desc += f"・{p}\n"

        # カテゴリに応じたカラーコード
        color = 0x3b82f6 # default blue
        tag_lower = tag.lower()
        if "chatgpt" in tag_lower or "openai" in tag_lower:
            color = 0x10b981 # emerald
        elif "claude" in tag_lower or "anthropic" in tag_lower:
            color = 0xd97706 # amber
        elif "copilot" in tag_lower or "microsoft" in tag_lower:
            color = 0x6366f1 # indigo
        elif "国内" in tag:
            color = 0xec4899 # pink

        embed = {
            "title": f"[{tag}] {title}",
            "url": url if url else None,
            "description": desc,
            "color": color,
            "footer": {
                "text": f"出典: {source}"
            }
        }
        embeds.append(embed)

    content_text = "🌅 **【毎朝AIニュース要約】本日の最新トピックをお届けします！**"
    if web_url:
        content_text += f"\n📱 **[地下鉄や電波圏外でも読める軽量Web版はこちら]({web_url})**"

    payload = {
        "content": content_text,
        "embeds": embeds
    }

    try:
        resp = requests.post(webhook_url, json=payload, timeout=15)
        if resp.status_code in [200, 204]:
            logger.info("Successfully sent notification to Discord.")
            return True
        else:
            logger.error(f"Failed to send to Discord: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"Discord notification error: {e}")
        return False


def send_line_notification(summaries: List[Dict[str, Any]], web_url: Optional[str] = None) -> bool:
    """LINE Messaging API経由でプッシュ通知を送信"""
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    user_id = os.environ.get("LINE_USER_ID")
    if not token or not user_id:
        logger.info("LINE credentials not fully set. Skipping LINE notification.")
        return False

    # LINE用テキストメッセージ整形（通勤中にパッと読める簡潔な形式）
    text_lines = ["🌅 【今朝の最新AIニュース要約】\n"]
    for i, item in enumerate(summaries[:6], 1):
        title = item.get("title_ja", item.get("title", ""))
        headline = item.get("headline", "")
        tag = item.get("tag", "")
        url = item.get("url", "")
        text_lines.append(f"📰 {i}. [{tag}] {title}")
        text_lines.append(f"⚡ {headline}")
        if url:
            text_lines.append(f"🔗 {url}")
        text_lines.append("")

    if web_url:
        text_lines.append(f"📱 圏外でも読めるWeb版:\n{web_url}")

    message_text = "\n".join(text_lines)

    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    payload = {
        "to": user_id,
        "messages": [
            {
                "type": "text",
                "text": message_text[:4900] # 5000字制限対策
            }
        ]
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=15)
        if resp.status_code == 200:
            logger.info("Successfully sent notification to LINE.")
            return True
        else:
            logger.error(f"Failed to send to LINE: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        logger.error(f"LINE notification error: {e}")
        return False


def notify_all(summaries: List[Dict[str, Any]], web_url: Optional[str] = None):
    """設定されているすべての通知先へ送信"""
    discord_sent = send_discord_notification(summaries, web_url)
    line_sent = send_line_notification(summaries, web_url)

    if not discord_sent and not line_sent:
        logger.info("No notification services configured. Printed summary to stdout (dry-run).")


if __name__ == "__main__":
    sample = [
        {
            "title_ja": "テスト記事: GPT-6発表",
            "headline": "OpenAIが新モデルを発表しました。",
            "points": ["ポイント1", "ポイント2", "ポイント3"],
            "tag": "ChatGPT / OpenAI",
            "source": "OpenAI News",
            "url": "https://openai.com"
        }
    ]
    notify_all(sample, "https://example.github.io/my-news/")
