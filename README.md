# 🌾 SmallFarm Global

> 小規模農家の商業的農業化に関する全世界の情報を **毎日自動収集・AI分析** し、共通のボトルネックと成功要因を可視化するWebプラットフォーム

[![Daily Data Collection](https://github.com/YOUR_USERNAME/smallfarm-global/actions/workflows/daily-collect.yml/badge.svg)](https://github.com/YOUR_USERNAME/smallfarm-global/actions)

---

## 🎯 概要

SmallFarm Globalは、JICAのSHEPをはじめとする世界中の小規模農家商業化プロジェクトを横断的に比較・分析するダッシュボード型Webアプリケーションです。

### 主な機能
- **📊 ダッシュボード**: プロジェクト統計、世界地図、最新更新タイムライン
- **📁 プロジェクトDB**: 16+のプロジェクトを検索・フィルタリング
- **⚠️ ボトルネック分析**: 全プロジェクト横断での障壁の可視化（棒グラフ・レーダーチャート・ヒートマップ）
- **✅ 成功要因分析**: 成功パターンの特定と可視化
- **🔄 比較ツール**: 最大4プロジェクトの並列比較
- **📚 最新リサーチ**: Semantic Scholar論文・AI分析済みニュース
- **🤖 毎日自動更新**: GitHub Actions + Semantic Scholar API + Gemini APIで新着情報を更新

### 差別化ポイント
- 論文はSemantic Scholarから検索し、ニュースはGeminiで要約・分類して構造化データとして抽出
- プロジェクト横断で「何がうまくいっていて、何が障壁か」を可視化
- **完全無料**（GitHub Pages + GitHub Actions + Gemini API無料枠）

---

## 🏗️ アーキテクチャ

```
GitHub Actions (毎朝6時JST)
  └── collect.py → Semantic Scholar API + RSSフィード
  └── analyze.py → Gemini API でニュースを構造化分析
  └── update_stats.py → 統計再計算
  └── git commit & push → data/*.json 更新

GitHub Pages (静的サイト)
  └── index.html + style.css + app.js + charts.js
  └── data/*.json を fetch して表示
```

---

## 🚀 セットアップ

### 1. リポジトリをクローン

```bash
git clone https://github.com/YOUR_USERNAME/smallfarm-global.git
cd smallfarm-global
```

### 2. ローカルで確認

```bash
# Python の簡易HTTPサーバーで起動
python -m http.server 8000

# ブラウザで http://localhost:8000 を開く
```

### 3. GitHub Pagesを有効化

1. Settings → Pages → Source: `main` branch → `/` (root)
2. Save

### 4. GitHub Secretsを設定（自動収集を有効にする場合）

| Secret名 | 説明 | 取得方法 |
|-----------|------|---------|
| `GEMINI_API_KEY` | ニュース分析用のGoogle Gemini APIキー | [Google AI Studio](https://aistudio.google.com/) |
| `SEMANTIC_SCHOLAR_API_KEY` | 論文検索用のSemantic Scholar APIキー（任意） | [Semantic Scholar API](https://www.semanticscholar.org/product/api) |

### 5. 手動で初回実行

Actions タブ → `Daily Data Collection & AI Analysis` → `Run workflow`

---

## 📁 ファイル構成

```
smallfarm-global/
├── .github/workflows/
│   └── daily-collect.yml      # GitHub Actions ワークフロー
├── pipeline/
│   ├── collect.py             # 記事・論文収集
│   ├── analyze.py             # Gemini API 分析
│   ├── prompts.py             # AI プロンプト定義
│   ├── update_stats.py        # 統計更新
│   └── requirements.txt       # Python依存パッケージ
├── data/
│   ├── projects.json          # プロジェクトDB（AI分析済み）
│   ├── news.json              # 最新ニュース
│   ├── papers.json            # 最新論文
│   ├── stats.json             # 集計統計
│   └── seed/
│       └── initial-projects.json  # 初期データ（16件）
├── index.html                 # メインHTML
├── style.css                  # スタイルシート
├── app.js                     # メインJS
├── charts.js                  # チャート描画
└── README.md
```

---

## 📊 データスキーマ

### プロジェクト (`projects.json`)

```json
{
  "id": "shep-phase1",
  "name": "SHEP Phase 1",
  "country": ["Kenya"],
  "region": "Sub-Saharan Africa",
  "implementer": "JICA",
  "approach": ["market-oriented"],
  "outcomes": {
    "income_change_pct": 70,
    "participants": 1200,
    "beneficiaries_total": 3000
  },
  "bottlenecks": [
    { "category": "input_market", "description": "...", "severity": "medium" }
  ],
  "success_factors": [
    { "category": "farmer_ownership", "description": "..." }
  ]
}
```

### ボトルネックカテゴリ

| カテゴリ | 日本語名 | アイコン |
|---------|---------|---------|
| `input_market` | 投入市場の信頼性 | 🌱 |
| `market_access` | 市場アクセス | 🛒 |
| `financial_access` | 金融アクセス | 💰 |
| `knowledge_gap` | 技術・知識ギャップ | 📚 |
| `institutional` | 制度・政策環境 | 🏛️ |
| `climate_risk` | 気候・環境リスク | 🌡️ |
| `gender` | ジェンダー格差 | ⚖️ |
| `post_harvest` | ポストハーベストロス | 📦 |
| `scalability` | スケーラビリティ | 📈 |

---

## 🔧 技術スタック

- **フロントエンド**: HTML5 + Vanilla CSS + Vanilla JavaScript
- **チャート**: [Chart.js](https://www.chartjs.org/) (CDN)
- **地図**: [Leaflet.js](https://leafletjs.com/) (CDN)
- **フォント**: [Google Fonts](https://fonts.google.com/) (Inter + Noto Sans JP)
- **AI分析**: [Google Gemini API](https://ai.google.dev/)（ニュース分析）
- **データ収集**: Python + [Semantic Scholar API](https://www.semanticscholar.org/product/api) + RSS
- **CI/CD**: GitHub Actions
- **ホスティング**: GitHub Pages

---

## 📝 ライセンス

MIT License

---

## 🙏 謝辞

- **JICA** — SHEP (Smallholder Horticulture Empowerment & Promotion)
- **FAO** — Farmer Field Schools
- **Semantic Scholar** — 学術論文検索API
- **Google** — Gemini API

---

*Built for JICA Internship Application 🌾*
