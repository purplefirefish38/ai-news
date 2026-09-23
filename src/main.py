"""
毎朝AIニュース自動要約・配信システム メインエントリポイント
Collector -> Summarizer -> Web Generator -> Notifier を統合実行します。
"""

import os
import sys
import json
import argparse
import logging
from typing import Optional

# カレントディレクトリに関わらず src/ 内部のモジュールを解決可能にする
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

# 自作モジュール
from collector import collect_all_news
from summarizer import summarize_with_gemini
from web_generator import generate_web_page
from notifier import notify_all

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="毎朝AIニュース要約システム")
    parser.add_argument("--config", default="config.json", help="設定ファイルのパス")
    parser.add_argument("--dry-run", action="store_true", help="通知を行わず要約とWeb生成のみ実行")
    parser.add_argument("--limit", type=int, default=None, help="要約する最大記事数")
    args = parser.parse_args()

    logger.info("=== 毎朝AIニュースまとめ処理を開始します ===")

    # 1. 設定の読み込み
    with open(args.config, "r", encoding="utf-8") as f:
        config = json.load(f)

    max_count = args.limit or config.get("app", {}).get("max_summary_count", 8)

    # 2. 記事の収集
    logger.info("Step 1: 各メディア・公式ブログから最新ニュースを収集しています...")
    articles = collect_all_news(args.config)
    if not articles:
        logger.warning("取得可能な新着記事がありませんでした。処理を終了します。")
        return

    # 上位N件を選定（一次情報優先）
    target_articles = articles[:max_count]
    logger.info(f"Step 2: 収集した {len(articles)} 件中、上位 {len(target_articles)} 件を要約対象とします。")

    # 3. Geminiによる要約
    logger.info("Step 3: AIによる要約・日本語化を行っています...")
    summaries = summarize_with_gemini(target_articles)

    # 4. オフライン対応Webページ生成
    logger.info("Step 4: オフライン対応の軽量Webページ（docs/index.html）を生成しています...")
    web_page_path = generate_web_page(summaries, output_dir="docs")
    logger.info(f"Webページ生成完了: {web_page_path}")

    # 5. 通知の送信
    web_url = os.environ.get("GITHUB_PAGES_URL")
    if args.dry_run:
        logger.info("ドライランモードのため、Discord/LINEへの外部通知はスキップします。")
    else:
        logger.info("Step 5: スマホへの通知配信を行っています...")
        notify_all(summaries, web_url=web_url)

    logger.info("=== すべての処理が正常に完了しました！ ===")


if __name__ == "__main__":
    main()
