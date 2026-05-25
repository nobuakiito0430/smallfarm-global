"""
SmallFarm Global — Gemini API Prompt Definitions
Prompt templates and category definitions for AI analysis.
"""

# ── Bottleneck Categories ────────────────────────────────────────
BOTTLENECK_CATEGORIES = {
    "input_market": {
        "name_ja": "投入市場の信頼性",
        "name_en": "Input Market Reliability",
        "icon": "🌱",
        "color": "#ef4444",
        "description": "種子・肥料等の品質不確実性、偽装問題、アクセス不足"
    },
    "market_access": {
        "name_ja": "市場アクセス",
        "name_en": "Market Access",
        "icon": "🛒",
        "color": "#f59e0b",
        "description": "物理的インフラ不備、仲買人依存、価格情報の欠如"
    },
    "financial_access": {
        "name_ja": "金融アクセス",
        "name_en": "Financial Access",
        "icon": "💰",
        "color": "#8b5cf6",
        "description": "融資不足、担保要件、農業保険の未整備"
    },
    "knowledge_gap": {
        "name_ja": "技術・知識ギャップ",
        "name_en": "Knowledge Gap",
        "icon": "📚",
        "color": "#3b82f6",
        "description": "普及サービス不足、情報の非対称性、技術研修の欠如"
    },
    "institutional": {
        "name_ja": "制度・政策環境",
        "name_en": "Institutional Environment",
        "icon": "🏛️",
        "color": "#6366f1",
        "description": "土地権の不安定さ、規制障壁、政府の実施能力不足"
    },
    "climate_risk": {
        "name_ja": "気候・環境リスク",
        "name_en": "Climate Risk",
        "icon": "🌡️",
        "color": "#ec4899",
        "description": "干ばつ、洪水、塩害、異常気象"
    },
    "gender": {
        "name_ja": "ジェンダー格差",
        "name_en": "Gender Gap",
        "icon": "⚖️",
        "color": "#14b8a6",
        "description": "女性農家の意思決定権限不足、資源アクセスの不平等"
    },
    "post_harvest": {
        "name_ja": "ポストハーベストロス",
        "name_en": "Post-Harvest Loss",
        "icon": "📦",
        "color": "#f97316",
        "description": "貯蔵・流通インフラの未整備、品質劣化"
    },
    "scalability": {
        "name_ja": "スケーラビリティ",
        "name_en": "Scalability",
        "icon": "📈",
        "color": "#eab308",
        "description": "パイロットから広域展開への障壁、質の維持"
    }
}

# ── Success Factor Categories ────────────────────────────────────
SUCCESS_FACTOR_CATEGORIES = {
    "farmer_ownership": {
        "name_ja": "農家のオーナーシップ",
        "name_en": "Farmer Ownership",
        "icon": "🙋",
        "description": "農家自身が意思決定する仕組み"
    },
    "behavioral_change": {
        "name_ja": "行動変容アプローチ",
        "name_en": "Behavioral Change",
        "icon": "🧠",
        "description": "心理学的理論（SDT等）の活用"
    },
    "public_private": {
        "name_ja": "官民連携",
        "name_en": "Public-Private Partnership",
        "icon": "🤝",
        "description": "政府・民間セクターの協働"
    },
    "gender_mainstream": {
        "name_ja": "ジェンダー主流化",
        "name_en": "Gender Mainstreaming",
        "icon": "👩‍🌾",
        "description": "女性参加の制度化"
    },
    "phased_scaleup": {
        "name_ja": "段階的スケールアップ",
        "name_en": "Phased Scale-up",
        "icon": "🪜",
        "description": "パイロット→実証→展開の段階的拡大"
    },
    "ict_use": {
        "name_ja": "ICT活用",
        "name_en": "ICT Utilization",
        "icon": "📱",
        "description": "デジタルツールの導入"
    },
    "market_linkage": {
        "name_ja": "市場関係者との直接接続",
        "name_en": "Market Linkage",
        "icon": "🔗",
        "description": "中間搾取の排除・直接取引"
    },
    "institutional_integration": {
        "name_ja": "現地制度への統合",
        "name_en": "Institutional Integration",
        "icon": "🏗️",
        "description": "各国政府の既存システムへの組み込み"
    }
}

# ── Article Analysis Prompt ──────────────────────────────────────
ARTICLE_ANALYSIS_PROMPT = """
あなたは開発経済学の専門家です。以下の記事/論文を読み、
小規模農家の商業的農業化に関する構造化データを抽出してください。

## 分析対象の記事
タイトル: {title}
ソース: {source}
日付: {date}
本文: {content}

## 出力形式（JSON）
以下のJSON形式で出力してください。該当しない項目はnullにしてください。

{{
  "is_relevant": true/false,
  "relevance_score": 0-100,
  "summary_ja": "日本語での2-3文の要約",
  "summary_en": "English summary in 2-3 sentences",

  "project": {{
    "name": "プロジェクト名（あれば）",
    "country": ["関連国のリスト"],
    "region": "Sub-Saharan Africa / South Asia / Southeast Asia / Latin America / MENA / Other",
    "implementer": "実施機関名",
    "approach": ["該当するものを選択: market-oriented / value-chain / input-market / climate-smart / digital / financial-inclusion / cooperative / nutrition"],
    "target_crops": ["対象作物"],
    "climate_relevance": "high / medium / low / none"
  }},

  "outcomes": {{
    "income_change_pct": null,
    "participants": null,
    "key_result": "最も重要な成果を1文で"
  }},

  "bottlenecks": [
    {{
      "category": "以下から選択: input_market / market_access / financial_access / knowledge_gap / institutional / climate_risk / gender / post_harvest / scalability",
      "description": "具体的な説明（日本語・1-2文）",
      "severity": "high / medium / low"
    }}
  ],

  "success_factors": [
    {{
      "category": "以下から選択: farmer_ownership / behavioral_change / public_private / gender_mainstream / phased_scaleup / ict_use / market_linkage / institutional_integration",
      "description": "具体的な説明（日本語・1-2文）"
    }}
  ],

  "tags": ["関連タグのリスト（英語）"],
  "source_url": "{url}"
}}

## 重要な注意
- is_relevant: 小規模農家の商業的農業化に無関係な記事はfalseにする
- bottlenecksとsuccess_factors: 記事から読み取れるもののみ。推測は最小限に
- 必ず有効なJSON形式で出力すること
"""


def format_analysis_prompt(title: str, source: str, date: str, content: str, url: str) -> str:
    """Format the analysis prompt with article data."""
    return ARTICLE_ANALYSIS_PROMPT.format(
        title=title,
        source=source,
        date=date,
        content=content[:5000],  # Truncate long content
        url=url
    )
