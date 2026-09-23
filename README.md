# 🌅 毎朝AIニュース自動要約・スマホ配信システム

毎朝の通勤時間やスキマ時間に、最新のAIニュースを3分でキャッチアップできる**完全無料・完全自動**の配信システムです。

---

## ✨ 主な特徴

1. **完全無料・クレカ不要・半永久稼働**:
   - 実行基盤: **GitHub Actions**（月2,000分無料枠、消費は月20分未満）
   - 要約AI: **Google Gemini API**（無料枠: 1日最大1,500リクエスト）
   - ホスティング: **GitHub Pages**（完全無料・容量無制限）
   - **60日停止回避**: 毎朝の自動コミットにより、GitHub Actionsが自動休眠することなくずっと動き続けます。

2. **3大AIの公式一次情報を最優先取得**:
   - **ChatGPT (OpenAI)**: 公式RSS (`openai.com/news/rss.xml`)
   - **Claude (Anthropic)**: 公式ニュース (`anthropic.com/news`) から自動抽出
   - **Copilot (Microsoft)**: 公式ブログ (`blogs.microsoft.com/feed/`)
   - その他、国内外の主要メディア（ITmedia AI+, AINOW, Zenn, The Verge, TechCrunch）を網羅。

3. **電波の届かない地下鉄でも読める（オフラインPWA対応）**:
   - 超軽量（約15KB）なWebページを毎朝自動ビルド。
   - **Service Worker** による自動端末キャッシュを搭載。地下鉄のトンネル内や機内モード（完全圏外）でも瞬時に開けます。
   - iPhoneのSafariで「ホーム画面に追加」すれば、ネイティブアプリのように使えます。

4. **スマホ通知で毎朝お知らせ**:
   - **Discord Webhook** または **LINE Messaging API** に対応。
   - 毎朝7:00（日本時間）に通知が届き、リンクをタップするだけで即読めます。

---

## 🚀 セットアップ手順（約5〜10分で完了）

### ステップ 1: Google Gemini APIキーを取得（無料・クレカ不要）
1. [Google AI Studio](https://aistudio.google.com/) にアクセスし、Googleアカウントでログインします。
2. 「**Get API key**」をクリックし、新しいキーを作成してコピーします。

---

### ステップ 2: 通知先を用意する（Discord または LINE）

#### 【おすすめ】Discord を使う場合（設定が一番ラク）
1. Discordで自分専用のサーバーを作成します。
2. 通知を受け取りたいチャンネルの「⚙️（設定）」➔「**連携サービス**」➔「**ウェブフック**」をクリック。
3. 「**新しいウェブフック**」を作成し、「**ウェブフックURLをコピー**」します。

#### LINE を使う場合
1. [LINE Developers コンソール](https://developers.line.biz/) にログイン。
2. 「Messaging API」チャネルを作成します。
3. 「Messaging API設定」タブから「**チャネルアクセストークン（長期）**」を発行。
4. 「チャネル基本設定」タブから「**あなたのユーザーID**」を確認。
5. 作成したBotのQRコードを読み取り、友だち追加しておきます。

---

### ステップ 3: GitHubリポジトリを作成＆アップロード
本フォルダのソースコードをご自身のGitHubリポジトリ（Public または Private）にプッシュします。

```bash
git init
git add .
git commit -m "Initial commit: Daily AI News Summarizer"
git branch -M main
git remote add origin https://github.com/<あなたのユーザー名>/<リポジトリ名>.git
git push -u origin main
```

---

### ステップ 4: GitHub Secrets を設定する
GitHubリポジトリ画面で:
1. 「**Settings**」タブ ➔ 左メニュー「**Secrets and variables**」➔「**Actions**」をクリック。
2. 「**New repository secret**」ボタンを押し、以下を登録します：

| Secret名 | 設定する値 | 必須 |
| :--- | :--- | :---: |
| `GEMINI_API_KEY` | ステップ1で取得したGemini APIキー | **必須** |
| `DISCORD_WEBHOOK_URL` | ステップ2で取得したDiscord Webhook URL | 任意 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINEチャネルアクセストークン | 任意 |
| `LINE_USER_ID` | LINEのあなたのユーザーID | 任意 |

3. また、Actionsに書き込み権限を与えるため：
   - 「**Settings**」➔「**Actions**」➔「**General**」
   - 「**Workflow permissions**」で **「Read and write permissions」** を選択して「Save」します。

---

### ステップ 5: GitHub Pages（Webページ公開）を有効化
電波圏外でも読めるWebページを有効化します：
1. リポジトリの「**Settings**」タブ ➔ 左メニュー「**Pages**」をクリック。
2. **Build and deployment** の **Branch** で：
   - ブランチ: `main`
   - フォルダ: `/docs`
   を選択して「**Save**」します。
3. 数分後、画面上部に公開URL（`https://<ユーザー名>.github.io/<リポジトリ名>/`）が表示されます。

---

### ステップ 6: テスト実行
1. リポジトリの「**Actions**」タブを開きます。
2. 左メニュー「**Daily AI News Summary**」をクリック。
3. 右上の「**Run workflow**」ボタン ➔ 緑色の「**Run workflow**」を押します。
4. 処理が完了すると、Discord/LINEに通知が届き、Webページが更新されます！

---

## 📱 iPhoneでアプリ化して圏外でも読む方法

1. iPhoneのSafariで、公開されたGitHub PagesのURLを開きます。
2. 画面下部の中央にある **共有ボタン（四角から矢印が出ているアイコン）** をタップ。
3. メニューから「**ホーム画面に追加**」をタップ。
4. ホーム画面に「**AIニュース**」アイコンが追加されます！

> [!TIP]
> **地下鉄での読み方**:
> 家やオフィス（Wi-Fi等）で一度開いておけば、端末内に自動キャッシュされます。
> 地下鉄の駅間やトンネル内で電波が「圏外」になっても、アイコンをタップするだけで朝のニュースが瞬時に表示されます。

---

## 🛠️ 購読サイトのカスタマイズ方法

`config.json` を編集することで、好きなサイトの追加・削除が自由に行えます。

```json
{
  "name": "新しいサイト名",
  "url": "https://example.com/rss.xml",
  "tag": "カテゴリ名",
  "type": "rss",
  "priority": 2,
  "enabled": true
}
```
- `priority`: 優先度（`1` が最優先で上位に表示・要約されます）
- `enabled`: `false` にすると一時的に取得を停止できます
- 変更してGitHubにプッシュするだけで、翌朝から反映されます。
