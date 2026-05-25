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

# ── Article Analysis Prompt (Anti-Hallucination Version) ─────────
ARTICLE_ANALYSIS_PROMPT = """
あなたは開発経済学の専門家です。以下の記事/論文を読み、
小規模農家の商業的農業化に関する構造化データを抽出してください。

## ★最重要ルール：ハルシネーション防止★
1. **原文に明示的に書かれていることだけ**を抽出してください
2. 推測・推論・一般論は絶対に含めないでください
3. 全てのボトルネックと成功要因には、**原文からの直接引用（evidence_quote）**を必ず添えてください
4. 原文に根拠がない項目は、無理に埋めず null または空配列 [] にしてください
5. 不確かな場合は extraction_confidence を下げ、uncertainty_note に理由を書いてください

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
  "extraction_confidence": 0-100,
  "uncertainty_note": "抽出に不確かさがある場合、その理由を記載。問題なければnull",
  "summary_ja": "日本語での2-3文の要約（原文の内容のみ反映）",
  "summary_en": "English summary in 2-3 sentences (source content only)",

  "project": {{
    "name": "プロジェクト名（原文に明記されている場合のみ）",
    "country": ["原文に明記された国のみ"],
    "region": "Sub-Saharan Africa / South Asia / Southeast Asia / Latin America / MENA / Other",
    "implementer": "原文に明記された実施機関名のみ",
    "approach": ["該当するものを選択: market-oriented / value-chain / input-market / climate-smart / digital / financial-inclusion / cooperative / nutrition"],
    "target_crops": ["原文に明記された作物のみ"],
    "climate_relevance": "high / medium / low / none"
  }},

  "outcomes": {{
    "income_change_pct": "原文に数値が明記されている場合のみ（例: 70）。推定値は不可",
    "participants": "原文に数値が明記されている場合のみ",
    "key_result": "原文に記載された具体的な成果を1文で。推測不可"
  }},

  "bottlenecks": [
    {{
      "category": "以下から選択: input_market / market_access / financial_access / knowledge_gap / institutional / climate_risk / gender / post_harvest / scalability",
      "description": "具体的な説明（日本語・1-2文）",
      "severity": "high / medium / low",
      "evidence_quote": "★この分析の根拠となる原文の一節をそのまま引用（英語可）★",
      "is_explicit": true
    }}
  ],

  "success_factors": [
    {{
      "category": "以下から選択: farmer_ownership / behavioral_change / public_private / gender_mainstream / phased_scaleup / ict_use / market_linkage / institutional_integration",
      "description": "具体的な説明（日本語・1-2文）",
      "evidence_quote": "★この分析の根拠となる原文の一節をそのまま引用（英語可）★",
      "is_explicit": true
    }}
  ],

  "grounding_check": {{
    "all_claims_sourced": true/false,
    "unsourced_claims": ["原文に根拠が見つからなかった主張があればここにリスト"],
    "source_quality": "primary_research / secondary_report / news_article / opinion"
  }},

  "tags": ["関連タグのリスト（英語）"],
  "source_url": "{url}"
}}

## 重要な注意
- is_relevant: 小規模農家の商業的農業化に無関係な記事はfalseにする
- bottlenecksとsuccess_factors: **原文に明示的に書かれているもののみ**
- evidence_quote が空欄のbottleneck/success_factorは無効とみなされます
- outcomes の数値: 原文に具体的な数字がない場合は必ずnullにする
- grounding_check: 自己検証として、全ての主張に原文の根拠があるか確認する
- 必ず有効なJSON形式で出力すること
"""

# ── Verification Prompt (Second-pass hallucination check) ────────
VERIFICATION_PROMPT = """
あなたはファクトチェッカーです。以下の「原文」と「AI分析結果」を比較し、
分析結果に含まれる各主張が原文に裏付けられているか検証してください。

## 原文
{content}

## AI分析結果
{analysis}

## 検証タスク
以下のJSON形式で検証結果を出力してください：

{{
  "verification_passed": true/false,
  "overall_accuracy": 0-100,
  "issues": [
    {{
      "field": "問題のあるフィールド名（例: bottlenecks[0]）",
      "claim": "AIが主張した内容",
      "verdict": "supported / unsupported / partially_supported",
      "reason": "判定理由"
    }}
  ],
  "recommended_removals": ["削除すべきフィールドのパス（例: bottlenecks[1]）"],
  "corrected_confidence": 0-100
}}

重要: 原文に明示的な根拠がない主張は「unsupported」としてください。
一般的知識からの推論は「unsupported」です。
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


def format_verification_prompt(content: str, analysis: str) -> str:
    """Format the verification prompt for second-pass hallucination check."""
    return VERIFICATION_PROMPT.format(
        content=content[:3000],
        analysis=analysis[:3000]
    )

