"""
オフライン対応・超軽量Webページ（PWA）生成モジュール
未読/既読管理（localStorage）、本日の注目Top10、サイト別タブ（ジャンル解説付き）、
星評価（1〜5）、Google翻訳リンク、および暗証番号（パスコード）ロック画面を完備。
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

DOCS_DIR = "docs"


def ensure_pwa_assets(output_dir: str):
    """PWA用の manifest.json および sw.js (Service Worker) を生成"""
    os.makedirs(output_dir, exist_ok=True)
    
    manifest = {
        "name": "毎朝AIニュース",
        "short_name": "AIニュース",
        "description": "通勤中や圏外でもサクッと読める最新AIニュースまとめ",
        "start_url": "./index.html",
        "display": "standalone",
        "background_color": "#0f172a",
        "theme_color": "#2563eb",
        "icons": [
            {
                "src": "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='20' fill='%232563eb'/><text x='50' y='65' font-size='50' font-family='sans-serif' text-anchor='middle' fill='white'>AI</text></svg>",
                "sizes": "192x192 512x512",
                "type": "image/svg+xml"
            }
        ]
    }
    with open(os.path.join(output_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    sw_code = """// Service Worker: オフライン（電波圏外）キャッシュ
const CACHE_NAME = 'ai-news-v3';
const ASSETS_TO_CACHE = [
  './',
  './index.html',
  './manifest.json'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS_TO_CACHE))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      const fetchPromise = fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      }).catch(() => cachedResponse);
      return cachedResponse || fetchPromise;
    })
  );
});
"""
    with open(os.path.join(output_dir, "sw.js"), "w", encoding="utf-8") as f:
        f.write(sw_code)


def get_tag_badge_class(tag: str) -> str:
    """タグに応じたCSSバッジスタイルを返却"""
    tag_lower = tag.lower()
    if "chatgpt" in tag_lower or "openai" in tag_lower:
        return "badge-openai"
    elif "claude" in tag_lower or "anthropic" in tag_lower:
        return "badge-claude"
    elif "copilot" in tag_lower or "microsoft" in tag_lower:
        return "badge-copilot"
    elif "国内" in tag:
        return "badge-japan"
    elif "エンジニア" in tag or "技術" in tag:
        return "badge-tech"
    return "badge-default"


def generate_html(summaries: List[Dict[str, Any]], updated_time_jst: str, auth_cfg: Optional[Dict[str, Any]] = None) -> str:
    """未読/既読、注目Top10、サイト別タブ、暗証番号認証を完備したHTMLを構築"""
    
    auth_cfg = auth_cfg or {}
    auth_enabled = auth_cfg.get("enabled", True)
    passcode = str(auth_cfg.get("passcode", "1234"))
    passcode_hash = hashlib.sha256(passcode.encode("utf-8")).hexdigest()

    # サイト（メディア）一覧の集計
    site_map = {}
    for s in summaries:
        s_name = s.get("source", "その他")
        cat_desc = s.get("category_desc", s.get("tag", "ニュース"))
        if s_name not in site_map:
            site_map[s_name] = cat_desc

    # 各記事カードのHTML生成
    cards_html = ""
    for idx, item in enumerate(summaries):
        card_id = f"art-{idx}"
        tag = item.get("tag", "AIニュース")
        cat_desc = item.get("category_desc", "")
        badge_cls = get_tag_badge_class(tag)
        title = item.get("title_ja", item.get("title", ""))
        headline = item.get("headline", "")
        points = item.get("points", [])
        url = item.get("url", "#")
        source = item.get("source", "")
        importance = item.get("importance", 3)
        stars = "★" * importance + "☆" * (5 - importance)

        is_overseas = ("国内" not in tag and "技術" not in tag)
        btn_label = "🔗 記事を読む（Safari翻訳対応）" if is_overseas else "🔗 記事を読む"
        points_li = "".join([f"<li><span class='p-icon'>🔹</span><div class='p-text'>{p}</div></li>" for p in points])

        cards_html += f"""
        <article class="news-card" id="{card_id}" data-id="{card_id}" data-source="{source}" data-importance="{importance}">
          <div class="card-header">
            <div class="header-left">
              <span class="badge {badge_cls}">{tag}</span>
              <span class="source-info">{source} <span class="cat-pill">({cat_desc})</span></span>
            </div>
            <div class="header-right">
              <span class="stars" title="注目度: {importance}/5">{stars}</span>
              <button class="read-toggle-btn" onclick="toggleRead('{card_id}')" title="既読/未読を切り替え">
                <span class="read-check">✓</span>
              </button>
            </div>
          </div>
          <h2 class="card-title">{title}</h2>
          <div class="headline-box">
            <span class="headline-icon">⚡</span>
            <span class="headline-text">{headline}</span>
          </div>
          <ul class="points-list">
            {points_li}
          </ul>
          <div class="card-footer">
            <a href="{url}" target="_blank" rel="noopener noreferrer" class="action-btn read-btn" onclick="markAsRead('{card_id}')">{btn_label} &rarr;</a>
          </div>
        </article>
        """

    site_tabs_html = ""
    for s_name, c_desc in site_map.items():
        site_tabs_html += f"""
        <button class="filter-btn site-tab" data-filter="site" data-site="{s_name}">
          <span class="tab-name">{s_name}</span>
          <span class="tab-desc">{c_desc}</span>
        </button>
        """

    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="AIニュース">
  <meta name="theme-color" content="#0f172a">
  <title>毎朝AIニュース要約 | 通勤用まとめ</title>
  <link rel="manifest" href="manifest.json">
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --border: #334155;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #3b82f6;
      --accent: #f59e0b;
      --badge-openai: #10b981;
      --badge-claude: #d97706;
      --badge-copilot: #6366f1;
      --badge-japan: #ec4899;
      --badge-tech: #06b6d4;
      --star-color: #fbbf24;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.5;
      padding: 12px;
      padding-bottom: 70px;
      max-width: 680px;
      margin: 0 auto;
      min-height: 100vh;
    }}

    /* ロック画面（暗証番号入力画面） */
    #lockScreen {{
      position: fixed;
      top: 0; left: 0; width: 100vw; height: 100vh;
      background: #090d16;
      z-index: 99999;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 24px 16px;
    }}
    .lock-box {{
      width: 100%;
      max-width: 320px;
      text-align: center;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .lock-icon {{
      font-size: 2.4rem;
      margin-bottom: 12px;
    }}
    .lock-title {{
      font-size: 1.3rem;
      font-weight: 700;
      color: #fff;
      margin-bottom: 6px;
    }}
    .lock-desc {{
      font-size: 0.85rem;
      color: var(--text-muted);
      margin-bottom: 24px;
    }}
    .pin-dots {{
      display: flex;
      justify-content: center;
      gap: 16px;
      margin-bottom: 24px;
      height: 20px;
      align-items: center;
    }}
    .pin-dot {{
      width: 14px;
      height: 14px;
      border-radius: 50%;
      border: 2px solid #475569;
      transition: all 0.2s;
    }}
    .pin-dot.filled {{
      background: var(--primary);
      border-color: var(--primary);
      box-shadow: 0 0 10px rgba(59, 130, 246, 0.6);
      transform: scale(1.15);
    }}
    .keypad {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px 20px;
      width: 100%;
      margin-bottom: 20px;
    }}
    .key-btn {{
      background: rgba(30, 41, 59, 0.8);
      border: 1px solid var(--border);
      color: #fff;
      font-size: 1.4rem;
      font-weight: 600;
      width: 68px;
      height: 68px;
      border-radius: 50%;
      margin: 0 auto;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      user-select: none;
      transition: all 0.15s;
    }}
    .key-btn:active {{
      background: var(--primary);
      transform: scale(0.92);
    }}
    .key-btn.action-key {{
      font-size: 1rem;
      background: transparent;
      border-color: transparent;
      color: var(--text-muted);
    }}
    .remember-device {{
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.8rem;
      color: var(--text-muted);
      margin-top: 8px;
      cursor: pointer;
    }}
    .remember-device input {{
      accent-color: var(--primary);
      width: 16px;
      height: 16px;
    }}
    .error-msg {{
      color: #ef4444;
      font-size: 0.8rem;
      font-weight: 600;
      height: 20px;
      margin-top: 10px;
    }}
    .shake {{
      animation: shake 0.4s ease-in-out;
    }}
    @keyframes shake {{
      0%, 100% {{ transform: translateX(0); }}
      20%, 60% {{ transform: translateX(-10px); }}
      40%, 80% {{ transform: translateX(10px); }}
    }}

    /* メインコンテンツ（認証後に表示） */
    #mainContent {{
      display: none;
    }}

    header {{
      padding: 14px 0 10px 0;
      border-bottom: 1px solid var(--border);
      margin-bottom: 10px;
    }}
    .header-top {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 6px;
    }}
    h1 {{
      font-size: 1.3rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 6px;
    }}
    .status-badge {{
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 9999px;
      background: #065f46;
      color: #a7f3d0;
      font-weight: 600;
    }}
    .status-badge.offline {{
      background: #831843;
      color: #fbcfe8;
    }}
    .meta-bar {{
      font-size: 0.78rem;
      color: var(--text-muted);
      display: flex;
      justify-content: space-between;
    }}
    
    .tabs-wrapper {{
      margin-bottom: 12px;
    }}
    .main-tabs {{
      display: flex;
      gap: 6px;
      margin-bottom: 8px;
    }}
    .main-tab-btn {{
      flex: 1;
      background: #1e293b;
      border: 1px solid var(--border);
      color: var(--text-muted);
      padding: 8px 4px;
      border-radius: 10px;
      font-size: 0.82rem;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 5px;
      transition: all 0.2s;
    }}
    .main-tab-btn.active {{
      background: var(--primary);
      color: #ffffff;
      border-color: var(--primary);
      box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
    }}
    .badge-count {{
      background: rgba(255, 255, 255, 0.2);
      padding: 1px 6px;
      border-radius: 9999px;
      font-size: 0.7rem;
    }}
    .main-tab-btn.active .badge-count {{
      background: #ffffff;
      color: var(--primary);
    }}

    .sub-tabs-scroll {{
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding: 4px 0 6px 0;
      scrollbar-width: none;
    }}
    .sub-tabs-scroll::-webkit-scrollbar {{ display: none; }}
    .filter-btn.site-tab {{
      background: rgba(30, 41, 59, 0.7);
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 12px;
      border-radius: 16px;
      font-size: 0.75rem;
      white-space: nowrap;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 2px;
      transition: all 0.2s;
    }}
    .filter-btn.site-tab .tab-name {{
      font-weight: 600;
      font-size: 0.78rem;
    }}
    .filter-btn.site-tab .tab-desc {{
      font-size: 0.65rem;
      color: var(--text-muted);
    }}
    .filter-btn.site-tab.active {{
      background: #3b82f6;
      border-color: #3b82f6;
      color: #fff;
    }}
    .filter-btn.site-tab.active .tab-desc {{
      color: #e0f2fe;
    }}

    /* 記事カード */
    .news-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 15px;
      margin-bottom: 12px;
      box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
      position: relative;
      transition: opacity 0.2s, transform 0.2s;
    }}
    .news-card.is-read {{
      opacity: 0.65;
      border-color: #273549;
    }}
    .news-card.is-read .card-title {{
      color: #94a3b8;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
    }}
    .header-left {{
      display: flex;
      align-items: center;
      gap: 6px;
      flex-wrap: wrap;
    }}
    .header-right {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .badge {{
      font-size: 0.72rem;
      font-weight: 700;
      padding: 2px 7px;
      border-radius: 6px;
      text-transform: uppercase;
    }}
    .badge-openai {{ background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4); }}
    .badge-claude {{ background: rgba(217, 119, 6, 0.2); color: #fbbf24; border: 1px solid rgba(217, 119, 6, 0.4); }}
    .badge-copilot {{ background: rgba(99, 102, 241, 0.2); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.4); }}
    .badge-japan {{ background: rgba(236, 72, 153, 0.2); color: #f472b6; border: 1px solid rgba(236, 72, 153, 0.4); }}
    .badge-tech {{ background: rgba(6, 182, 212, 0.2); color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.4); }}
    .badge-default {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; }}
    
    .source-info {{
      font-size: 0.73rem;
      color: var(--text-muted);
    }}
    .cat-pill {{
      font-size: 0.68rem;
      color: #38bdf8;
      font-weight: 500;
    }}
    .stars {{
      color: var(--star-color);
      font-size: 0.75rem;
      letter-spacing: -1px;
    }}
    .read-toggle-btn {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid var(--border);
      color: var(--text-muted);
      width: 26px;
      height: 26px;
      border-radius: 50%;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.75rem;
      transition: all 0.2s;
    }}
    .news-card.is-read .read-toggle-btn {{
      background: #10b981;
      border-color: #10b981;
      color: #fff;
    }}
    .card-title {{
      font-size: 1.02rem;
      font-weight: 700;
      line-height: 1.38;
      margin-bottom: 10px;
      color: #ffffff;
    }}
    .headline-box {{
      background: rgba(245, 158, 11, 0.12);
      border-left: 3px solid var(--accent);
      padding: 8px 10px;
      border-radius: 0 8px 8px 0;
      margin-bottom: 10px;
      display: flex;
      align-items: flex-start;
      gap: 6px;
    }}
    .headline-icon {{ font-size: 0.95rem; line-height: 1.2; }}
    .headline-text {{
      font-size: 0.85rem;
      font-weight: 600;
      color: #fef3c7;
      line-height: 1.35;
    }}
    .points-list {{
      list-style: none;
      margin-bottom: 12px;
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .points-list li {{
      font-size: 0.85rem;
      color: #e2e8f0;
      display: flex;
      align-items: flex-start;
      gap: 8px;
      line-height: 1.4;
    }}
    .p-icon {{
      color: var(--primary);
      font-size: 0.8rem;
      flex-shrink: 0;
      margin-top: 1px;
    }}
    .p-text {{
      flex: 1;
    }}
    .card-footer {{
      display: flex;
      justify-content: flex-end;
      gap: 8px;
      padding-top: 8px;
      border-top: 1px dashed var(--border);
    }}
    .action-btn {{
      font-size: 0.75rem;
      padding: 4px 10px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      transition: all 0.2s;
    .read-btn {{
      background: #2563eb;
      color: #ffffff;
      padding: 6px 14px;
      border-radius: 8px;
      font-size: 0.78rem;
      font-weight: 600;
      border: none;
      box-shadow: 0 2px 4px rgba(37, 99, 235, 0.3);
    }}
    .read-btn:hover {{
      background: #1d4ed8;
    }}
    .safari-tip {{
      background: rgba(59, 130, 246, 0.12);
      border: 1px solid rgba(59, 130, 246, 0.3);
      padding: 8px 12px;
      border-radius: 10px;
      font-size: 0.76rem;
      color: #93c5fd;
      margin-bottom: 10px;
      display: flex;
      align-items: center;
      gap: 6px;
      line-height: 1.35;
    }}
    .empty-state {{
      text-align: center;
      padding: 40px 16px;
      color: var(--text-muted);
      font-size: 0.9rem;
      display: none;
    }}
  </style>
</head>
<body>

  <!-- 暗証番号ロック画面 -->
  <div id="lockScreen" style="{'' if auth_enabled else 'display:none;'}">
    <div class="lock-box">
      <div class="lock-icon">🔒</div>
      <div class="lock-title">AIニュース（専用）</div>
      <div class="lock-desc">暗証番号を入力してロックを解除してください</div>
      
      <div class="pin-dots">
        <div class="pin-dot" id="dot-0"></div>
        <div class="pin-dot" id="dot-1"></div>
        <div class="pin-dot" id="dot-2"></div>
        <div class="pin-dot" id="dot-3"></div>
      </div>

      <div class="keypad">
        <button class="key-btn" onclick="pressKey('1')">1</button>
        <button class="key-btn" onclick="pressKey('2')">2</button>
        <button class="key-btn" onclick="pressKey('3')">3</button>
        <button class="key-btn" onclick="pressKey('4')">4</button>
        <button class="key-btn" onclick="pressKey('5')">5</button>
        <button class="key-btn" onclick="pressKey('6')">6</button>
        <button class="key-btn" onclick="pressKey('7')">7</button>
        <button class="key-btn" onclick="pressKey('8')">8</button>
        <button class="key-btn" onclick="pressKey('9')">9</button>
        <button class="key-btn action-key" onclick="clearPin()">クリア</button>
        <button class="key-btn" onclick="pressKey('0')">0</button>
        <button class="key-btn action-key" onclick="backspacePin()">⌫</button>
      </div>

      <label class="remember-device">
        <input type="checkbox" id="rememberDevice" checked>
        <span>この端末を記憶する（次回から自動解除）</span>
      </label>

      <div id="errorMsg" class="error-msg"></div>
    </div>
  </div>

  <!-- メインコンテンツ -->
  <div id="mainContent" style="{'' if not auth_enabled else ''}">
    <header>
      <div class="header-top">
        <h1>🌅 毎朝AIニュース</h1>
        <span id="connStatus" class="status-badge">⚡ オンライン</span>
      </div>
      <div class="meta-bar">
        <span>更新: {updated_time_jst}</span>
        <span>計 {len(summaries)} 件取得</span>
      </div>
    </header>

    <div class="safari-tip">
      <span>💡</span>
      <div><strong>iPhoneの方へ:</strong> 英語記事を開いた後、画面左下の「<strong>あA</strong>」（または『翻訳』アイコン）を押すと一瞬で自然な日本語になります！</div>
    </div>

    <div class="tabs-wrapper">
      <!-- メインタブ（注目・未読・既読） -->
      <div class="main-tabs">
        <button class="main-tab-btn active" onclick="switchMainTab('unread')">
          <span>📬 未読</span>
          <span id="unreadCount" class="badge-count">0</span>
        </button>
        <button class="main-tab-btn" onclick="switchMainTab('featured')">
          <span>🌟 本日の注目 (Top 10)</span>
        </button>
        <button class="main-tab-btn" onclick="switchMainTab('read')">
          <span>✅ 既読</span>
          <span id="readCount" class="badge-count">0</span>
        </button>
      </div>

      <!-- サイト別タブ（横スクロール） -->
      <div class="sub-tabs-scroll">
        {site_tabs_html}
      </div>
    </div>

    <main id="newsContainer">
      {cards_html}
      <div id="emptyState" class="empty-state">
        🎉 該当する記事はありません
      </div>
    </main>
  </div>

  <script>
    // 認証設定
    const AUTH_ENABLED = {str(auth_enabled).lower()};
    const EXPECTED_HASH = "{passcode_hash}";
    const STORAGE_AUTH_KEY = "ai_news_auth_token_v2";

    let currentPin = "";

    // SHA-256計算関数 (Web Crypto API)
    async function sha256(str) {{
      const buf = new TextEncoder().encode(str);
      const digest = await crypto.subtle.digest('SHA-256', buf);
      return Array.from(new Uint8Array(digest)).map(b => b.toString(16).padStart(2, '0')).join('');
    }}

    // 認証チェック
    async function checkAuth() {{
      if (!AUTH_ENABLED) {{
        unlockScreen();
        return;
      }}
      const saved = localStorage.getItem(STORAGE_AUTH_KEY);
      if (saved === EXPECTED_HASH) {{
        unlockScreen();
      }} else {{
        document.getElementById('lockScreen').style.display = 'flex';
        document.getElementById('mainContent').style.display = 'none';
      }}
    }}

    function unlockScreen() {{
      const lock = document.getElementById('lockScreen');
      if (lock) lock.style.display = 'none';
      document.getElementById('mainContent').style.display = 'block';
      applyReadState();
      renderView();
    }}

    async function pressKey(num) {{
      if (currentPin.length >= 8) return;
      currentPin += num;
      updateDots();
      document.getElementById('errorMsg').textContent = "";

      // 4文字以上で検証チェック
      if (currentPin.length >= 4) {{
        const hash = await sha256(currentPin);
        if (hash === EXPECTED_HASH) {{
          if (document.getElementById('rememberDevice').checked) {{
            localStorage.setItem(STORAGE_AUTH_KEY, EXPECTED_HASH);
          }}
          unlockScreen();
          currentPin = "";
          updateDots();
        }} else if (currentPin.length >= 6) {{
          triggerError();
        }}
      }}
    }}

    function updateDots() {{
      for (let i = 0; i < 4; i++) {{
        const dot = document.getElementById('dot-' + i);
        if (dot) {{
          if (i < currentPin.length) {{
            dot.classList.add('filled');
          }} else {{
            dot.classList.remove('filled');
          }}
        }}
      }}
    }}

    function backspacePin() {{
      currentPin = currentPin.slice(0, -1);
      updateDots();
      document.getElementById('errorMsg').textContent = "";
    }}

    function clearPin() {{
      currentPin = "";
      updateDots();
      document.getElementById('errorMsg').textContent = "";
    }}

    function triggerError() {{
      const lockBox = document.querySelector('.lock-box');
      lockBox.classList.add('shake');
      document.getElementById('errorMsg').textContent = "暗証番号が正しくありません";
      setTimeout(() => {{
        lockBox.classList.remove('shake');
        clearPin();
      }}, 500);
    }}

    // PCキーボード入力対応
    window.addEventListener('keydown', (e) => {{
      if (document.getElementById('lockScreen').style.display !== 'none') {{
        if (e.key >= '0' && e.key <= '9') {{
          pressKey(e.key);
        }} else if (e.key === 'Backspace') {{
          backspacePin();
        }} else if (e.key === 'Escape') {{
          clearPin();
        }}
      }}
    }});

    // サービスワーカー登録（オフライン対応）
    if ('serviceWorker' in navigator) {{
      navigator.serviceWorker.register('./sw.js').then(reg => {{
        console.log('SW registered:', reg.scope);
      }}).catch(err => {{
        console.log('SW registration failed:', err);
      }});
    }}

    // オンライン/圏外判定
    function updateOnlineStatus() {{
      const el = document.getElementById('connStatus');
      if (navigator.onLine) {{
        el.textContent = '⚡ オンライン';
        el.className = 'status-badge';
      }} else {{
        el.textContent = '📶 圏外 (オフライン保存中)';
        el.className = 'status-badge offline';
      }}
    }}
    window.addEventListener('online', updateOnlineStatus);
    window.addEventListener('offline', updateOnlineStatus);
    updateOnlineStatus();

    // 既読/未読の管理 (localStorage)
    const STORAGE_KEY = 'ai_news_read_ids_v1';
    function getReadIds() {{
      try {{
        return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
      }} catch (e) {{
        return [];
      }}
    }}
    function saveReadIds(ids) {{
      try {{
        localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
      }} catch (e) {{}}
    }}

    function markAsRead(id) {{
      const ids = getReadIds();
      if (!ids.includes(id)) {{
        ids.push(id);
        saveReadIds(ids);
        applyReadState();
        renderView();
      }}
    }}

    function toggleRead(id) {{
      let ids = getReadIds();
      if (ids.includes(id)) {{
        ids = ids.filter(x => x !== id);
      }} else {{
        ids.push(id);
      }}
      saveReadIds(ids);
      applyReadState();
      renderView();
    }}

    function applyReadState() {{
      const readIds = getReadIds();
      const allCards = document.querySelectorAll('.news-card');
      let readCount = 0;
      let unreadCount = 0;

      allCards.forEach(card => {{
        const id = card.getAttribute('data-id');
        if (readIds.includes(id)) {{
          card.classList.add('is-read');
          readCount++;
        }} else {{
          card.classList.remove('is-read');
          unreadCount++;
        }}
      }});

      const rEl = document.getElementById('readCount');
      const uEl = document.getElementById('unreadCount');
      if (rEl) rEl.textContent = readCount;
      if (uEl) uEl.textContent = unreadCount;
    }}

    // 表示制御（タブの切り替え）
    let currentTab = 'unread';
    let currentSite = '';

    function switchMainTab(tab) {{
      currentTab = tab;
      currentSite = '';
      document.querySelectorAll('.main-tab-btn').forEach(btn => btn.classList.remove('active'));
      document.querySelectorAll('.filter-btn.site-tab').forEach(btn => btn.classList.remove('active'));

      if (tab === 'unread') {{
        document.querySelectorAll('.main-tab-btn')[0].classList.add('active');
      }} else if (tab === 'featured') {{
        document.querySelectorAll('.main-tab-btn')[1].classList.add('active');
      }} else if (tab === 'read') {{
        document.querySelectorAll('.main-tab-btn')[2].classList.add('active');
      }}
      renderView();
    }}

    document.querySelectorAll('.filter-btn.site-tab').forEach(btn => {{
      btn.addEventListener('click', () => {{
        const site = btn.getAttribute('data-site');
        document.querySelectorAll('.main-tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.filter-btn.site-tab').forEach(b => b.classList.remove('active'));
        
        btn.classList.add('active');
        currentTab = 'site';
        currentSite = site;
        renderView();
      }});
    }});

    function renderView() {{
      const readIds = getReadIds();
      const cards = Array.from(document.querySelectorAll('.news-card'));
      const container = document.getElementById('newsContainer');
      const emptyState = document.getElementById('emptyState');
      if (!container) return;
      let visibleCount = 0;

      if (currentTab === 'featured') {{
        cards.sort((a, b) => {{
          return parseInt(b.getAttribute('data-importance')) - parseInt(a.getAttribute('data-importance'));
        }});
        cards.forEach((card, index) => {{
          container.insertBefore(card, emptyState);
          if (index < 10) {{
            card.style.display = 'block';
            visibleCount++;
          }} else {{
            card.style.display = 'none';
          }}
        }});
      }} else {{
        cards.forEach(card => {{
          const id = card.getAttribute('data-id');
          const isRead = readIds.includes(id);
          const site = card.getAttribute('data-source');

          let show = false;
          if (currentTab === 'unread') {{
            show = !isRead;
          }} else if (currentTab === 'read') {{
            show = isRead;
          }} else if (currentTab === 'site') {{
            show = (site === currentSite);
          }}

          if (show) {{
            card.style.display = 'block';
            visibleCount++;
          }} else {{
            card.style.display = 'none';
          }}
        }});
      }}

      if (emptyState) emptyState.style.display = (visibleCount === 0) ? 'block' : 'none';
    }}

    // 初回認証チェック起動
    checkAuth();
  </script>
</body>
</html>
"""
    return html_content


def generate_web_page(summaries: List[Dict[str, Any]], output_dir: str = DOCS_DIR, auth_cfg: Optional[Dict[str, Any]] = None) -> str:
    """Webページ一式（docs/index.html等）を生成して保存"""
    ensure_pwa_assets(output_dir)

    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst).strftime("%Y/%m/%d %H:%M JST")

    html = generate_html(summaries, now_jst, auth_cfg)
    out_file = os.path.join(output_dir, "index.html")

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    archive_file = os.path.join(output_dir, "latest_news.json")
    with open(archive_file, "w", encoding="utf-8") as f:
        json.dump({
            "updated_at": now_jst,
            "articles": summaries
        }, f, indent=2, ensure_ascii=False)

    logger.info(f"Generated lightweight offline web page at: {out_file}")
    return out_file
