"""
SmallFarm Global — Data Collection Script
Collects articles and papers from OpenAlex API and RSS feeds.

Usage:
    python pipeline/collect.py

Environment variables:
    OPENALEX_EMAIL: Email for OpenAlex polite pool (optional but recommended)
"""

import os
import json
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path

import requests
# pyrefly: ignore [missing-import]
import feedparser

# ── Configuration ────────────────────────────────────────────────

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"

OPENALEX_EMAIL = os.environ.get("OPENALEX_EMAIL", "")
OPENALEX_BASE = "https://api.openalex.org"

# Search queries for OpenAlex
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

# RSS Feed sources (verified working 2026-05)
RSS_FEEDS = [
    {
        "name": "ReliefWeb Agriculture",
        "url": "https://reliefweb.int/updates/rss.xml?search=smallholder+agriculture",
        "filter_keywords": ["smallholder", "farmer", "agriculture", "rural", "food security", "market", "crop"]
    },
    {
        "name": "Devex Development",
        "url": "https://www.devex.com/news/search.rss?query=smallholder+agriculture",
        "filter_keywords": ["smallholder", "farmer", "agriculture", "JICA", "SHEP", "horticulture", "market access", "food"]
    },
    {
        "name": "CGIAR Research",
        "url": "https://cgspace.cgiar.org/search?query=smallholder+commercialization&rpp=10&format=rss",
        "filter_keywords": ["smallholder", "farmer", "commercialization", "market", "value chain", "agriculture"]
    },
    {
        "name": "JICA News",
        "url": "https://www.jica.go.jp/english/news/field/rss.xml",
        "filter_keywords": ["agriculture", "farmer", "rural", "SHEP", "horticulture", "food"]
    },
]

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("collect")

# ── Utility Functions ────────────────────────────────────────────

def url_hash(url: str) -> str:
    """Generate a short hash from a URL for deduplication."""
    return hashlib.md5(url.encode()).hexdigest()[:12]


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


# ── OpenAlex Collection ──────────────────────────────────────────

def collect_openalex() -> list:
    """Collect recent papers from OpenAlex API."""
    logger.info("Starting OpenAlex collection...")
    items = []
    existing_urls = load_existing_urls()

    since_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    headers = {}
    if OPENALEX_EMAIL:
        headers["User-Agent"] = f"SmallFarmGlobal/1.0 (mailto:{OPENALEX_EMAIL})"

    for query in SEARCH_QUERIES:
        try:
            params = {
                "search": query,
                "filter": f"from_publication_date:{since_date}",
                "sort": "publication_date:desc",
                "per_page": 5,  # Limit per query to stay within rate limits
            }
            if OPENALEX_EMAIL:
                params["mailto"] = OPENALEX_EMAIL

            resp = requests.get(
                f"{OPENALEX_BASE}/works",
                params=params,
                headers=headers,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()

            for work in data.get("results", []):
                url = work.get("doi") or work.get("id", "")
                if url in existing_urls:
                    continue

                # Extract abstract
                abstract = ""
                if work.get("abstract_inverted_index"):
                    # Reconstruct abstract from inverted index
                    inv = work["abstract_inverted_index"]
                    word_positions = []
                    for word, positions in inv.items():
                        for pos in positions:
                            word_positions.append((pos, word))
                    word_positions.sort()
                    abstract = " ".join(w for _, w in word_positions)

                items.append({
                    "type": "paper",
                    "title": work.get("title", "Untitled"),
                    "source": "OpenAlex",
                    "date": work.get("publication_date", ""),
                    "content": abstract,
                    "source_url": url,
                    "authors": [
                        a.get("author", {}).get("display_name", "")
                        for a in (work.get("authorships") or [])[:5]
                    ],
                    "cited_by_count": work.get("cited_by_count", 0),
                    "query": query,
                    "collected_at": datetime.now().isoformat()
                })
                existing_urls.add(url)

            logger.info(f"  Query '{query}': found {len(data.get('results', []))} papers")

        except requests.RequestException as e:
            logger.warning(f"  Query '{query}' failed: {e}")
            continue

    logger.info(f"OpenAlex total: {len(items)} new papers")
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

    # Collect from all sources
    papers = collect_openalex()
    news = collect_rss()

    all_items = papers + news
    logger.info(f"Total collected: {len(all_items)} items ({len(papers)} papers, {len(news)} news)")

    if all_items:
        save_collected(all_items, date_str)
    else:
        logger.info("No new items collected today.")

    logger.info("Collection complete!")


if __name__ == "__main__":
    main()
