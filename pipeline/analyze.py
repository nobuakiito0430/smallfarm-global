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
from datetime import datetime
from pathlib import Path

import google.generativeai as genai

from prompts import format_analysis_prompt

# ── Configuration ────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODEL_NAME = "gemini-1.5-flash"
MAX_ITEMS_PER_RUN = 30  # Stay within free tier limits
RETRY_DELAY = 5  # seconds between retries

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("analyze")

# ── Gemini Setup ─────────────────────────────────────────────────

def setup_gemini():
    """Initialize Gemini API client."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    genai.configure(api_key=GEMINI_API_KEY)
    return genai.GenerativeModel(MODEL_NAME)


# ── Analysis Functions ───────────────────────────────────────────

def analyze_article(model, article: dict) -> dict | None:
    """Analyze a single article with Gemini API."""
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
            text = response.text.strip()

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'```(?:json)?\s*\n?([\s\S]*?)\n?```', text)
            if json_match:
                text = json_match.group(1).strip()

            # Try to parse JSON
            result = json.loads(text)
            result["ai_confidence"] = result.get("relevance_score", 50)
            result["analyzed_at"] = datetime.now().isoformat()
            return result

        except json.JSONDecodeError as e:
            logger.warning(f"  JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(RETRY_DELAY)
        except Exception as e:
            logger.warning(f"  API error (attempt {attempt + 1}): {e}")
            if attempt < 2:
                time.sleep(RETRY_DELAY * (attempt + 1))

    return None


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

def merge_paper(existing_papers: list, analysis: dict, raw_item: dict) -> list:
    """Merge a new paper analysis into the papers list."""
    entry = {
        "title": raw_item.get("title", ""),
        "source": raw_item.get("source", ""),
        "date": raw_item.get("date", ""),
        "source_url": raw_item.get("source_url", ""),
        "authors": raw_item.get("authors", []),
        "cited_by_count": raw_item.get("cited_by_count", 0),
        "summary_ja": analysis.get("summary_ja", ""),
        "summary_en": analysis.get("summary_en", ""),
        "tags": analysis.get("tags", []),
        "bottlenecks": analysis.get("bottlenecks", []),
        "success_factors": analysis.get("success_factors", []),
        "ai_confidence": analysis.get("ai_confidence", 50),
        "analyzed_at": analysis.get("analyzed_at", "")
    }
    existing_papers.append(entry)

    # Keep only last 30 days
    cutoff = (datetime.now() - __import__("datetime").timedelta(days=30)).strftime("%Y-%m-%d")
    existing_papers = [p for p in existing_papers if (p.get("date", "") >= cutoff or not p.get("date"))]

    return existing_papers


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
    cutoff = (datetime.now() - __import__("datetime").timedelta(days=30)).strftime("%Y-%m-%d")
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

    # Setup Gemini
    model = setup_gemini()

    # Load existing data
    existing_projects = load_existing_data("projects.json")
    existing_papers = load_existing_data("papers.json")
    existing_news = load_existing_data("news.json")

    # Analyze each item
    analyzed = 0
    relevant = 0

    for i, item in enumerate(raw_items[:MAX_ITEMS_PER_RUN]):
        logger.info(f"[{i+1}/{min(len(raw_items), MAX_ITEMS_PER_RUN)}] Analyzing: {item.get('title', '')[:60]}...")

        result = analyze_article(model, item)
        if not result:
            logger.warning(f"  Skipped (analysis failed)")
            continue

        analyzed += 1

        if not result.get("is_relevant", False):
            logger.info(f"  Not relevant (score: {result.get('relevance_score', 0)})")
            continue

        relevant += 1
        logger.info(f"  Relevant! (score: {result.get('relevance_score', 0)}, confidence: {result.get('ai_confidence', 0)})")

        # Merge into appropriate data files
        if item.get("type") == "paper":
            existing_papers = merge_paper(existing_papers, result, item)
        else:
            existing_news = merge_news(existing_news, result, item)

        # Check if a new project was discovered
        existing_projects = merge_project(existing_projects, result, item)

        # Rate limiting
        time.sleep(2)

    # Save updated data
    save_data(existing_projects, "projects.json")
    save_data(existing_papers, "papers.json")
    save_data(existing_news, "news.json")

    logger.info("=" * 60)
    logger.info(f"Analysis complete: {analyzed} analyzed, {relevant} relevant")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
