"""
AIニュース要約モジュール
Google Gemini APIを使用して、収集した記事を通勤向けに日本語要約します。
注目度スコア（1〜5）の付与および英語記事の自然な日本語化を行います。
"""

import os
import json
import logging
import re
from typing import List, Dict, Any, Optional
import requests

logger = logging.getLogger(__name__)

GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash"
]


def create_summary_prompt(articles: List[Dict[str, Any]]) -> str:
    """Gemini用の要約プロンプトを構築"""
    articles_text = ""
    for i, a in enumerate(articles, 1):
        articles_text += f"\n--- 記事 {i} ---\n"
        articles_text += f"メディア: {a.get('source_name')}\n"
        articles_text += f"カテゴリ: {a.get('tag')} ({a.get('category_desc', '')})\n"
        articles_text += f"優先度: {a.get('priority')}\n"
        articles_text += f"タイトル: {a.get('title')}\n"
        articles_text += f"URL: {a.get('link')}\n"
        if a.get("summary_raw"):
            articles_text += f"概要: {a.get('summary_raw')}\n"

    prompt = f"""あなたは敏腕AIアナリスト兼テックジャーナリストです。
毎朝通勤中やスキマ時間にスマホで3分で読める「最新AIニュースまとめ」を作成してください。
対象の記事情報が以下に与えられます。

【重要な要約＆翻訳方針（厳守）】
1. 【完全日本語化】海外サイトの英語記事は、タイトル・一言まとめ・要点に至るまで、必ず自然で分かりやすい日本語に翻訳・要約してください。英語のまま出力することは禁止です。
2. 【注目度スコア（importance: 1〜5）の判定】
   - 5 (⭐⭐⭐⭐⭐): OpenAI, Claude, Copilotのフラッグシップ新モデル発表、世界的なブレークスルー、業界地図を変える大ニュース
   - 4 (⭐⭐⭐⭐): 主要な新機能追加、大幅な性能向上、大規模な業務提携、重要発表
   - 3 (⭐⭐⭐): 一般的なアップデート、活用事例、トレンド動向
   - 2 (⭐⭐): 軽微な更新、特定ニッチ向けの話題
3. 【通勤向けレイアウト】
   - title_ja: 読者が思わずタップしたくなる、キャッチーかつ正確な日本語タイトル
   - headline: 一目で要点が伝わる「一言サマリー」（30〜50文字程度）
   - points: 忙しい社会人が知るべき重要ポイント3つ（何が起きたか／何ができるようになったか／今後の影響）

【出力フォーマット】
以下のキーを持つJSON配列（JSONリスト）のみを出力してください（Markdownのコードブロック ```json ``` で囲んで構いません）：

[
  {{
    "title_ja": "自然で魅力的な日本語タイトル（英語記事は必ず日本語に翻訳）",
    "headline": "一目でわかる一言まとめ（30〜50文字程度）",
    "points": [
      "要点1（発表内容や技術概要）",
      "要点2（具体的な進化点、性能向上、できること）",
      "要点3（利用対象、提供開始時期、業界への影響）"
    ],
    "importance": 5,
    "tag": "カテゴリ名",
    "category_desc": "カテゴリ詳細",
    "source": "メディア名",
    "url": "元の記事URL"
  }}
]

【対象記事データ】
{articles_text}
"""
    return prompt


def summarize_with_gemini(articles: List[Dict[str, Any]], api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Gemini APIを呼び出して記事を要約"""
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("GEMINI_API_KEY is not set. Generating mock summaries for testing.")
        return generate_mock_summaries(articles)

    prompt = create_summary_prompt(articles)

    for model_name in GEMINI_MODELS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "parts": [{"text": prompt}]
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json"
            }
        }

        try:
            logger.info(f"Calling Gemini API with model: {model_name}...")
            resp = requests.post(url, json=payload, timeout=45)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                summaries = json.loads(text)
                # category_descや元情報の補正
                for s in summaries:
                    if "importance" not in s:
                        s["importance"] = 4
                logger.info(f"Successfully generated {len(summaries)} summaries with {model_name}")
                return summaries
            else:
                logger.warning(f"Gemini API error ({model_name}): {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            logger.error(f"Request failed for {model_name}: {e}")

    logger.warning("Falling back to mock summaries due to API errors.")
    return generate_mock_summaries(articles)


# テスト用・オフライン用の簡易翻訳辞書（英語タイトルを自然な日本語に変換）
MOCK_TRANSLATION_MAP = {
    "priorities and principles for effective third party assessments": "OpenAI、AIモデルの第三者安全性評価に関する原則と優先課題を策定",
    "parallel cut research time and cost in half with gpt‑6 astra": "GPT-6 Astraの導入によりリサーチ業務の所要時間とコストを半減",
    "introducing gpt-6 sol and luna": "OpenAI、推論性能と視覚認識を極めた新フラッグシップモデル「GPT-6 Sol/Luna」を発表",
    "better prompt caching for gpt-6": "GPT-6向けプロンプトキャッシュ技術が大幅進化、APIコストと応答遅延を低減",
    "grab and openai bring practical ai skills to southeast asia": "GrabとOpenAIが東南アジア地域で実践的AIスキルトレーニングを共同展開",
    "improving our alignment and security efforts": "Anthropic、自律型Claudeモデルの安全性確保と不正アクセス防止策を強化",
    "previewing the model hardware standard": "Anthropic、AIエージェントのハードウェア安全操作規格「MHS」プレビュー公開",
    "partnering with accenture on embedded evaluation": "Anthropicとアクセンチュア、企業向け組込み型AI評価システムでパートナーシップ締結",
    "life sciences verification program": "Anthropic、バイオリスクを遮断するライフサイエンス検証プログラムを開始",
    "what we’ve learned from microsoft’s own ai transformation": "マイクロソフト自社のAI変革プロセスから得られた知見と現場の教訓",
    "microsoft’s commitment for ai in education": "マイクロソフト、教育分野におけるAI安全利用と生徒の学習強化コミットメントを発表",
    "how claude’s text watermark works": "Claudeが生成するテキストに埋め込まれる不可視電子透かしの仕組みを技術解説"
}


def translate_mock_title(orig_title: str) -> str:
    """モック時の英語タイトルを日本語に変換"""
    lower = orig_title.lower().strip()
    for key, val in MOCK_TRANSLATION_MAP.items():
        if key in lower:
            return val

    # 簡単なルール置換
    t = orig_title
    t = re.sub(r'Introducing\s+', '【新発表】', t, flags=re.IGNORECASE)
    t = re.sub(r'Announces?\s+', '発表: ', t, flags=re.IGNORECASE)
    t = re.sub(r'How\s+([^?]+)', r'\1の仕組みと解説', t, flags=re.IGNORECASE)
    t = re.sub(r'Partnering with\s+', 'との提携: ', t, flags=re.IGNORECASE)
    return t


def generate_mock_summaries(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """APIキーがない場合やテスト用のフォールバック要約（注目度＆日本語化付き）"""
    mock_results = []
    for idx, a in enumerate(articles):
        source = a.get("source_name", "Web")
        tag = a.get("tag", "AI")
        cat_desc = a.get("category_desc", "ニュース")
        priority = a.get("priority", 2)
        raw_title = a.get("title", "")
        
        # タイトル日本語化
        ja_title = translate_mock_title(raw_title)

        # 注目度スコア（一次情報なら5または4、国内大手なら4、その他3）
        if priority == 1 or "openai" in tag.lower() or "claude" in tag.lower():
            importance = 5 if idx < 3 else 4
        elif priority == 2:
            importance = 4 if idx < 6 else 3
        else:
            importance = 3

        stars = "⭐" * importance

        mock_results.append({
            "title_ja": ja_title,
            "headline": f"{source}による最新の注目発表です（注目度: {stars}）。",
            "points": [
                f"{tag}に関する重要アップデートと最新機能の公開",
                a.get("summary_raw", "詳細な技術仕様や実証結果は元記事にて解説されています。")[:80].replace("\n", " ") + "...",
                "今後の業務活用や関連サービスへの展開に注目が集まります"
            ],
            "importance": importance,
            "tag": tag,
            "category_desc": cat_desc,
            "source": source,
            "url": a.get("link", "")
        })
    return mock_results
