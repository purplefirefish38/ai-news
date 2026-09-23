"""
オフライン対応・超軽量Webページ（PWA）生成モジュール
未読/既読管理（localStorage）、本日の注目Top10、サイト別タブ（ジャンル解説付き）、
星評価（1〜5）、Google翻訳リンクを完備したHTMLを生成します。
"""

import os
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

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
const CACHE_NAME = 'ai-news-v2';
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


def generate_html(summaries: List[Dict[str, Any]], updated_time_jst: str) -> str:
    """未読/既読、注目Top10、サイト別タブを完備したHTMLを構築"""
    
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

        # 翻訳URL
        trans_url = f"https://translate.google.com/translate?sl=auto&tl=ja&u={url}"

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
            <a href="{trans_url}" target="_blank" rel="noopener noreferrer" class="action-btn translate-btn" onclick="markAsRead('{card_id}')">🌐 日本語で読む</a>
            <a href="{url}" target="_blank" rel="noopener noreferrer" class="action-btn original-btn" onclick="markAsRead('{card_id}')">原文リンク &rarr;</a>
          </div>
        </article>
        """

    # サイト別タブボタンの生成
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
    
    /* タブコンテナ */
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
    }}
    .translate-btn {{
      background: rgba(59, 130, 246, 0.15);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.3);
    }}
    .original-btn {{
      background: rgba(255, 255, 255, 0.05);
      color: var(--text-muted);
      border: 1px solid var(--border);
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

  <script>
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

      document.getElementById('readCount').textContent = readCount;
      document.getElementById('unreadCount').textContent = unreadCount;
    }}

    // 表示制御（タブの切り替え）
    let currentTab = 'unread'; // 'unread' | 'featured' | 'read' | 'site'
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

    // サイトタブのクリックリスナー
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
      let visibleCount = 0;

      if (currentTab === 'featured') {{
        // 注目度（星）順にソートして上位10件を表示
        cards.sort((a, b) => {{
          return parseInt(b.getAttribute('data-importance')) - parseInt(a.getAttribute('data-importance'));
        }});
        // コンテナ内に再配置
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

      emptyState.style.display = (visibleCount === 0) ? 'block' : 'none';
    }}

    // 初期化実行
    applyReadState();
    renderView();
  </script>
</body>
</html>
"""
    return html_content


def generate_web_page(summaries: List[Dict[str, Any]], output_dir: str = DOCS_DIR) -> str:
    """Webページ一式（docs/index.html等）を生成して保存"""
    ensure_pwa_assets(output_dir)

    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst).strftime("%Y/%m/%d %H:%M JST")

    html = generate_html(summaries, now_jst)
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
