"""
SmallFarm Global — Data Collection Script
Collects papers from Semantic Scholar and news articles from RSS feeds.

Usage:
    python pipeline/collect.py

Environment variables:
    SEMANTIC_SCHOLAR_API_KEY: Semantic Scholar API key (optional)
"""

import os
import json
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
# pyrefly: ignore [missing-import]
import feedparser

# ── Configuration ────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

SEMANTIC_SCHOLAR_API_KEY = os.environ.get("SEMANTIC_SCHOLAR_API_KEY", "")
SEMANTIC_SCHOLAR_BASE = "https://api.semanticscholar.org/graph/v1"
MAX_PAPERS_PER_QUERY = int(os.environ.get("MAX_PAPERS_PER_QUERY", "5"))
MAX_PAPERS_PER_RUN = int(os.environ.get("MAX_PAPERS_PER_RUN", "12"))

# Search queries for Semantic Scholar
SEARCH_QUERIES = [
    "smallholder commercialization",
    "market-oriented agriculture developing countries",
    "smallholder horticulture empowerment",
    "SHEP approach JICA",
    "farmer market access developing",
    "climate smart agriculture smallholder",
    "seed quality developing countries",
    "agricultural value chain smallholder",
    "farmer field school",
    "agricultural extension market linkage",
]

# RSS Feed sources (verified working 2026-05-26)
RSS_FEEDS = [
    {
        "name": "ReliefWeb Agriculture",
        "url": "https://reliefweb.int/updates/rss.xml?search=smallholder+agriculture",
        "filter_keywords": ["smallholder", "farmer", "agriculture", "rural", "food security", "market", "crop"]
    },
    {
        "name": "Google News Smallholder",
        "url": "https://news.google.com/rss/search?q=smallholder+agriculture+developing+countries&hl=en",
        "filter_keywords": ["smallholder", "farmer", "agriculture", "rural", "food", "market", "crop", "JICA", "SHEP"]
    },
    {
        "name": "AllAfrica",
        "url": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf",
        "filter_keywords": ["smallholder", "farmer", "agriculture", "rural", "food security", "market", "crop", "horticulture"]
    },
    {
        "name": "ScienceDaily Agriculture",
        "url": "https://www.sciencedaily.com/rss/plants_animals/agriculture_and_food.xml",
        "filter_keywords": ["smallholder", "farmer", "crop", "agriculture", "food security", "developing", "rural"]
    },
]

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("collect")

def load_existing_urls() -> set:
    """Load all URLs from existing data files to avoid duplicates."""
    urls = set()
    for filename in ["projects.json", "news.json", "papers.json"]:
        filepath = DATA_DIR / filename
        if filepath.exists():
            try:
                data = json.loads(filepath.read_text(encoding="utf-8"))
                for item in data:
                    if "source_url" in item:
                        urls.add(item["source_url"])
            except (json.JSONDecodeError, KeyError):
                pass
    return urls


def save_collected(items: list, date_str: str):
    """Save collected items to raw data directory."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    output_path = RAW_DIR / f"collected_{date_str}.json"
    output_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    logger.info(f"Saved {len(items)} items to {output_path}")


def load_existing_data(filename: str) -> list:
    """Load existing structured data from data/*.json."""
    filepath = DATA_DIR / filename
    if filepath.exists():
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def save_data(data: list, filename: str):
    """Save structured data to data/*.json."""
    filepath = DATA_DIR / filename
    filepath.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    logger.info(f"Saved {len(data)} items to {filepath}")


def trim_to_recent(items: list, days: int = 30) -> list:
    """Keep recent dated items plus undated items."""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    return [item for item in items if (item.get("date", "") >= cutoff or not item.get("date"))]


# ── Semantic Scholar Collection ──────────────────────────────────

def _paper_url(paper: dict) -> str:
    """Prefer DOI URLs, then Semantic Scholar URLs."""
    external_ids = paper.get("externalIds") or {}
    doi = external_ids.get("DOI")
    if doi:
        return f"https://doi.org/{doi}"
    return paper.get("url") or f"https://www.semanticscholar.org/paper/{paper.get('paperId', '')}"


def _paper_summary(paper: dict) -> str:
    """Use Semantic Scholar TLDR when available, otherwise shorten the abstract."""
    tldr = paper.get("tldr") or {}
    if tldr.get("text"):
        return tldr["text"]
    abstract = paper.get("abstract") or ""
    return abstract[:700] + ("..." if len(abstract) > 700 else "")


def _merge_semantic_papers(new_papers: list):
    """Merge Semantic Scholar papers directly into papers.json without Gemini calls."""
    existing = load_existing_data("papers.json")
    seen = {item.get("source_url") for item in existing if item.get("source_url")}

    added = 0
    for paper in new_papers:
        if paper.get("source_url") in seen:
            continue
        existing.append(paper)
        seen.add(paper.get("source_url"))
        added += 1

    existing = sorted(trim_to_recent(existing), key=lambda item: item.get("date", ""), reverse=True)
    save_data(existing, "papers.json")
    logger.info(f"Semantic Scholar merge: {added} new paper(s)")


def collect_semantic_scholar() -> list:
    """Collect recent papers from Semantic Scholar Academic Graph API."""
    logger.info("Starting Semantic Scholar collection...")
    items = []
    existing_urls = load_existing_urls()
    seen_urls = set(existing_urls)

    current_year = datetime.now().year
    headers = {"User-Agent": "SmallFarmGlobal/1.0"}
    if SEMANTIC_SCHOLAR_API_KEY:
        headers["x-api-key"] = SEMANTIC_SCHOLAR_API_KEY

    rate_limit_hits = 0
    for query in SEARCH_QUERIES:
        if len(items) >= MAX_PAPERS_PER_RUN:
            break

        try:
            params = {
                "query": query,
                "fields": "paperId,title,abstract,url,year,publicationDate,authors,citationCount,externalIds,venue,tldr,openAccessPdf",
                "year": f"{current_year - 1}-{current_year}",
                "limit": MAX_PAPERS_PER_QUERY,
            }

            resp = requests.get(
                f"{SEMANTIC_SCHOLAR_BASE}/paper/search",
                params=params,
                headers=headers,
                timeout=30
            )
            if resp.status_code == 429:
                rate_limit_hits += 1
                retry_after = int(resp.headers.get("Retry-After", "10"))
                logger.warning(f"  Semantic Scholar rate limit hit; waiting {retry_after}s")
                time.sleep(min(retry_after, 60))
                if rate_limit_hits >= 2:
                    logger.warning("  Stopping Semantic Scholar collection after repeated rate limits")
                    break
                continue

            resp.raise_for_status()
            rate_limit_hits = 0
            data = resp.json()

            query_added = 0
            for paper in data.get("data", []):
                url = _paper_url(paper)
                if not url or url in seen_urls:
                    continue

                date = paper.get("publicationDate") or (str(paper.get("year")) if paper.get("year") else "")
                if not date:
                    continue

                items.append({
                    "type": "paper",
                    "title": paper.get("title", "Untitled"),
                    "source": "Semantic Scholar",
                    "date": date,
                    "content": paper.get("abstract", ""),
                    "source_url": url,
                    "authors": [
                        author.get("name", "")
                        for author in (paper.get("authors") or [])[:5]
                    ],
                    "cited_by_count": paper.get("citationCount", 0),
                    "summary_en": _paper_summary(paper),
                    "summary_ja": "",
                    "tags": [query],
                    "bottlenecks": [],
                    "success_factors": [],
                    "ai_confidence": None,
                    "analyzed_at": "",
                    "venue": paper.get("venue", ""),
                    "open_access_pdf": (paper.get("openAccessPdf") or {}).get("url", ""),
                    "query": query,
                    "collected_at": datetime.now().isoformat()
                })
                seen_urls.add(url)
                query_added += 1

                if len(items) >= MAX_PAPERS_PER_RUN:
                    break

            logger.info(f"  Query '{query}': found {len(data.get('data', []))} papers, {query_added} new")

        except requests.RequestException as e:
            logger.warning(f"  Query '{query}' failed: {e}")
            continue

        time.sleep(1)

    logger.info(f"Semantic Scholar total: {len(items)} new papers")
    return items


# ── RSS Feed Collection ──────────────────────────────────────────

def collect_rss() -> list:
    """Collect news from RSS feeds."""
    logger.info("Starting RSS collection...")
    items = []
    existing_urls = load_existing_urls()

    for feed_config in RSS_FEEDS:
        try:
            logger.info(f"  Fetching {feed_config['name']}...")
            feed = feedparser.parse(feed_config["url"])

            feed_matched = 0
            feed_skipped_dup = 0
            feed_skipped_kw = 0
            feed_total = len(feed.entries[:20])

            if feed.bozo and feed_total == 0:
                logger.warning(f"  {feed_config['name']}: Parse error - {feed.bozo_exception}")
                continue

            for entry in feed.entries[:20]:  # Limit entries per feed
                url = entry.get("link", "")
                if not url or url in existing_urls:
                    feed_skipped_dup += 1
                    continue

                # Check keywords
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                if not any(kw.lower() in text for kw in feed_config["filter_keywords"]):
                    feed_skipped_kw += 1
                    continue

                # Parse date
                date = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    date = datetime(*entry.updated_parsed[:6]).strftime("%Y-%m-%d")

                items.append({
                    "type": "news",
                    "title": entry.get("title", "Untitled"),
                    "source": feed_config["name"],
                    "date": date,
                    "content": entry.get("summary", "") or entry.get("description", ""),
                    "source_url": url,
                    "collected_at": datetime.now().isoformat()
                })
                existing_urls.add(url)
                feed_matched += 1

            logger.info(f"  {feed_config['name']}: {feed_total} entries, "
                        f"{feed_matched} matched, {feed_skipped_dup} dup, {feed_skipped_kw} no-keyword")

        except Exception as e:
            logger.warning(f"  {feed_config['name']} failed: {e}")
            continue

    logger.info(f"RSS total: {len(items)} new articles")
    return items


# ── Main ─────────────────────────────────────────────────────────

def main():
    """Main collection pipeline."""
    logger.info("=" * 60)
    logger.info("SmallFarm Global — Daily Data Collection")
    logger.info("=" * 60)

    date_str = datetime.now().strftime("%Y-%m-%d")

    # Collect papers without Gemini, and send only news to raw Gemini analysis.
    papers = collect_semantic_scholar()
    if papers:
        _merge_semantic_papers(papers)

    news = collect_rss()

    logger.info(f"Total collected: {len(papers)} papers, {len(news)} news articles")

    if news:
        save_collected(news, date_str)
    else:
        logger.info("No new news items collected today.")

    logger.info("Collection complete!")


if __name__ == "__main__":
    main()
