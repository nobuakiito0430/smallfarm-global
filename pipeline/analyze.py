"""
SmallFarm Global — Gemini API Analysis Script
Analyzes collected articles using Google Gemini API.

Usage:
    python pipeline/analyze.py

Environment variables:
    GEMINI_API_KEY: Google Gemini API key (required)
"""

import os
import json
import re
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

# pyrefly: ignore [missing-import]
import google.generativeai as genai

from prompts import format_analysis_prompt, format_verification_prompt

# ── Configuration ────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = os.environ.get("GEMINI_MODEL") or "gemini-2.0-flash"
MAX_ITEMS_PER_RUN = int(os.environ.get("MAX_ITEMS_PER_RUN", "10"))
RETRY_DELAY = 10  # seconds between retries (increased for rate limits)
CONFIDENCE_THRESHOLD = 40  # Reject analyses below this confidence
ENABLE_VERIFICATION = False  # Disable by default to save API quota (set True if using paid tier)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("analyze")


class QuotaLimitError(Exception):
    """Raised when Gemini reports a quota or rate-limit error."""


def is_quota_error(error: Exception) -> bool:
    """Detect quota/rate-limit errors from Gemini client exceptions."""
    message = str(error).lower()
    return any(term in message for term in [
        "429",
        "quota",
        "rate limit",
        "rate_limit",
        "resource exhausted",
        "too many requests",
    ])

# ── Gemini Setup ─────────────────────────────────────────────────

def setup_gemini():
    """Initialize Gemini API client."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(MODEL_NAME)


# ── Analysis Functions ───────────────────────────────────────────

def _parse_json_response(text: str) -> dict | None:
    """Extract and parse JSON from a Gemini response."""
    text = text.strip()
    json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
    if json_match:
        text = json_match.group(1).strip()
    return json.loads(text)


def analyze_article(model, article: dict) -> dict | None:
    """Analyze a single article with Gemini API (with grounding checks)."""
    prompt = format_analysis_prompt(
        title=article.get("title", ""),
        source=article.get("source", ""),
        date=article.get("date", ""),
        content=article.get("content", ""),
        url=article.get("source_url", "")
    )

    for attempt in range(3):
        try:
            response = model.generate_content(prompt)
            result = _parse_json_response(response.text)

            # Compute confidence from multiple signals
            extraction_conf = result.get("extraction_confidence", 50)
            relevance_score = result.get("relevance_score", 50)
            grounding = result.get("grounding_check", {})
            all_sourced = grounding.get("all_claims_sourced", False)

            # Weighted confidence: grounding matters most
            confidence = int(
                extraction_conf * 0.5 +
                relevance_score * 0.3 +
                (100 if all_sourced else 30) * 0.2
            )
            result["ai_confidence"] = confidence
            result["analyzed_at"] = datetime.now().isoformat()

            # Strip claims that lack evidence quotes
            result = strip_ungrounded_claims(result)

            return result

        except json.JSONDecodeError as e:
            logger.warning(f"  JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            if is_quota_error(e):
                raise QuotaLimitError(str(e)) from e
            logger.warning(f"  API error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(RETRY_DELAY * (attempt + 1))

    return None


def strip_ungrounded_claims(result: dict) -> dict:
    """Remove bottlenecks/success_factors that lack evidence quotes."""
    original_b = len(result.get("bottlenecks", []))
    original_s = len(result.get("success_factors", []))

    result["bottlenecks"] = [
        b for b in result.get("bottlenecks", [])
        if b.get("evidence_quote") and len(b["evidence_quote"].strip()) > 10
    ]
    result["success_factors"] = [
        s for s in result.get("success_factors", [])
        if s.get("evidence_quote") and len(s["evidence_quote"].strip()) > 10
    ]

    removed_b = original_b - len(result["bottlenecks"])
    removed_s = original_s - len(result["success_factors"])
    if removed_b or removed_s:
        logger.info(f"  Grounding filter: removed {removed_b} bottleneck(s), {removed_s} success factor(s) without evidence")

    return result


def verify_analysis(model, article: dict, analysis: dict) -> dict:
    """Second-pass: verify that analysis claims are grounded in source text."""
    prompt = format_verification_prompt(
        content=article.get("content", ""),
        analysis=json.dumps(analysis, ensure_ascii=False, indent=2)
    )

    try:
        response = model.generate_content(prompt)
        verification = _parse_json_response(response.text)

        # Apply recommended removals
        removals = verification.get("recommended_removals", [])
        for path in removals:
            if path.startswith("bottlenecks["):
                idx = int(re.search(r'\[(\d+)\]', path).group(1))
                if 0 <= idx < len(analysis.get("bottlenecks", [])):
                    analysis["bottlenecks"][idx] = None
            elif path.startswith("success_factors["):
                idx = int(re.search(r'\[(\d+)\]', path).group(1))
                if 0 <= idx < len(analysis.get("success_factors", [])):
                    analysis["success_factors"][idx] = None

        analysis["bottlenecks"] = [b for b in analysis.get("bottlenecks", []) if b is not None]
        analysis["success_factors"] = [s for s in analysis.get("success_factors", []) if s is not None]

        # Update confidence with verifier's assessment
        corrected = verification.get("corrected_confidence")
        if corrected is not None:
            analysis["ai_confidence"] = min(analysis["ai_confidence"], corrected)

        analysis["verification"] = {
            "passed": verification.get("verification_passed", False),
            "accuracy": verification.get("overall_accuracy", 0),
            "issues_count": len(verification.get("issues", [])),
            "removals": len(removals)
        }

        logger.info(f"  Verification: passed={verification.get('verification_passed')}, "
                    f"accuracy={verification.get('overall_accuracy')}, "
                    f"removed={len(removals)} claims")

        return analysis

    except Exception as e:
        if is_quota_error(e):
            raise QuotaLimitError(str(e)) from e
        logger.warning(f"  Verification failed: {e}")
        analysis["verification"] = {"passed": False, "error": str(e)}
        return analysis


def find_latest_raw_file() -> Path | None:
    """Find the most recent raw collection file."""
    if not RAW_DIR.exists():
        return None
    files = sorted(RAW_DIR.glob("collected_*.json"), reverse=True)
    return files[0] if files else None


def load_existing_data(filename: str) -> list:
    """Load existing data from a JSON file."""
    filepath = DATA_DIR / filename
    if filepath.exists():
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_data(data: list, filename: str):
    """Save data to a JSON file."""
    filepath = DATA_DIR / filename
    filepath.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    logger.info(f"Saved {len(data)} items to {filepath}")


# ── Merge Functions ──────────────────────────────────────────────


def merge_news(existing_news: list, analysis: dict, raw_item: dict) -> list:
    """Merge a new news analysis into the news list."""
    entry = {
        "title": raw_item.get("title", ""),
        "source": raw_item.get("source", ""),
        "date": raw_item.get("date", ""),
        "source_url": raw_item.get("source_url", ""),
        "summary_ja": analysis.get("summary_ja", ""),
        "summary_en": analysis.get("summary_en", ""),
        "tags": analysis.get("tags", []),
        "bottlenecks": analysis.get("bottlenecks", []),
        "success_factors": analysis.get("success_factors", []),
        "ai_confidence": analysis.get("ai_confidence", 50),
        "analyzed_at": analysis.get("analyzed_at", "")
    }
    existing_news.append(entry)

    # Keep only last 30 days
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    existing_news = [n for n in existing_news if (n.get("date", "") >= cutoff or not n.get("date"))]

    return existing_news


def merge_project(existing_projects: list, analysis: dict, raw_item: dict) -> list:
    """Merge a new project from analysis into projects list if it's a new project."""
    project_info = analysis.get("project", {})
    if not project_info or not project_info.get("name"):
        return existing_projects

    # Check if project already exists
    name = project_info["name"]
    for existing in existing_projects:
        if existing.get("name", "").lower() == name.lower():
            return existing_projects  # Already exists, skip

    # Create new project entry
    new_project = {
        "id": name.lower().replace(" ", "-").replace("(", "").replace(")", "")[:30],
        "name": name,
        "name_ja": name,  # Will use AI-provided name
        "country": project_info.get("country", []),
        "country_ja": project_info.get("country", []),
        "region": project_info.get("region", "Other"),
        "flag": "🌍",
        "implementer": project_info.get("implementer", "Unknown"),
        "start_year": None,
        "end_year": None,
        "status": "active",
        "approach": project_info.get("approach", []),
        "approach_ja": project_info.get("approach", []),
        "target_crops": project_info.get("target_crops", []),
        "climate_relevance": project_info.get("climate_relevance", "medium"),
        "description_en": analysis.get("summary_en", ""),
        "description_ja": analysis.get("summary_ja", ""),
        "outcomes": analysis.get("outcomes", {}),
        "bottlenecks": analysis.get("bottlenecks", []),
        "success_factors": analysis.get("success_factors", []),
        "tags": analysis.get("tags", []),
        "source_url": raw_item.get("source_url", ""),
        "ai_confidence": analysis.get("ai_confidence", 50),
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "coordinates": None
    }

    existing_projects.append(new_project)
    logger.info(f"  New project discovered: {name}")
    return existing_projects


# ── Main ─────────────────────────────────────────────────────────

def main():
    """Main analysis pipeline."""
    logger.info("=" * 60)
    logger.info("SmallFarm Global — AI Analysis with Gemini")
    logger.info("=" * 60)

    # Find latest raw data
    raw_file = find_latest_raw_file()
    if not raw_file:
        logger.info("No raw data files found. Run collect.py first.")
        return

    logger.info(f"Processing: {raw_file.name}")
    raw_items = json.loads(raw_file.read_text(encoding="utf-8"))

    if not raw_items:
        logger.info("No items to analyze.")
        return

    # Load existing data
    existing_projects = load_existing_data("projects.json")
    existing_news = load_existing_data("news.json")
    existing_news_urls = {
        item.get("source_url")
        for item in existing_news
        if item.get("source_url")
    }
    raw_items = [
        item for item in raw_items
        if item.get("type") == "news"
    ]
    candidate_items = [
        item for item in raw_items
        if item.get("source_url")
        and item.get("source_url") not in existing_news_urls
    ][:MAX_ITEMS_PER_RUN]

    if not candidate_items:
        logger.info("No new news items to analyze.")
        return

    logger.info(f"Gemini budget: analyzing {len(candidate_items)} news item(s), max {MAX_ITEMS_PER_RUN} per run")

    # Setup Gemini only after there is confirmed news work to process.
    model = setup_gemini()

    # Analyze each item
    analyzed = 0
    relevant = 0
    rejected_low_confidence = 0

    for i, item in enumerate(candidate_items):
        logger.info(f"[{i+1}/{len(candidate_items)}] Analyzing news: {item.get('title', '')[:60]}...")

        try:
            result = analyze_article(model, item)
        except QuotaLimitError as e:
            logger.warning(f"Gemini quota/rate limit reached. Skipping remaining news analysis: {e}")
            break

        if not result:
            logger.warning(f"  Skipped (analysis failed)")
            continue

        analyzed += 1

        if not result.get("is_relevant", False):
            logger.info(f"  Not relevant (score: {result.get('relevance_score', 0)})")
            continue

        # Confidence threshold gate
        confidence = result.get("ai_confidence", 0)
        if confidence < CONFIDENCE_THRESHOLD:
            logger.info(f"  Rejected: confidence {confidence} < threshold {CONFIDENCE_THRESHOLD}")
            rejected_low_confidence += 1
            continue

        # Optional 2-pass verification
        if ENABLE_VERIFICATION:
            result = verify_analysis(model, item, result)
            # Re-check confidence after verification
            if result.get("ai_confidence", 0) < CONFIDENCE_THRESHOLD:
                logger.info(f"  Rejected after verification: confidence {result.get('ai_confidence')}")
                rejected_low_confidence += 1
                continue

        relevant += 1
        logger.info(f"  ✅ Accepted (confidence: {result.get('ai_confidence', 0)}, "
                    f"bottlenecks: {len(result.get('bottlenecks', []))}, "
                    f"success_factors: {len(result.get('success_factors', []))})")

        existing_news = merge_news(existing_news, result, item)

        # Check if a new project was discovered
        existing_projects = merge_project(existing_projects, result, item)

        # Rate limiting (longer delay with verification enabled)
        time.sleep(4 if ENABLE_VERIFICATION else 2)

    # Save updated data
    save_data(existing_projects, "projects.json")
    save_data(existing_news, "news.json")

    logger.info("=" * 60)
    logger.info(f"Analysis complete: {analyzed} analyzed, {relevant} accepted, {rejected_low_confidence} rejected (low confidence)")
    logger.info(f"Verification: {'enabled' if ENABLE_VERIFICATION else 'disabled'}, Confidence threshold: {CONFIDENCE_THRESHOLD}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
