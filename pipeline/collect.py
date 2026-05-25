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

# RSS Feed sources
RSS_FEEDS = [
    {
        "name": "JICA Topics",
        "url": "https://www.jica.go.jp/Resource/english/news/field/rss.xml",
        "filter_keywords": ["agriculture", "farmer", "rural", "SHEP", "horticulture"]
    },
    {
        "name": "FAO News",
        "url": "https://www.fao.org/rss/home/en/",
        "filter_keywords": ["smallholder", "farmer", "market", "horticulture"]
    },
    {
        "name": "World Bank Agriculture",
        "url": "https://blogs.worldbank.org/en/agfood/rss.xml",
        "filter_keywords": ["smallholder", "farmer", "agriculture"]
    },
    {
        "name": "IFAD News",
        "url": "https://www.ifad.org/en/rss",
        "filter_keywords": ["smallholder", "rural", "farmer", "market"]
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

            for entry in feed.entries[:20]:  # Limit entries per feed
                url = entry.get("link", "")
                if not url or url in existing_urls:
                    continue

                # Check keywords
                text = f"{entry.get('title', '')} {entry.get('summary', '')}".lower()
                if not any(kw.lower() in text for kw in feed_config["filter_keywords"]):
                    continue

                # Parse date
                date = ""
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    date = datetime(*entry.published_parsed[:6]).strftime("%Y-%m-%d")

                items.append({
                    "type": "news",
                    "title": entry.get("title", "Untitled"),
                    "source": feed_config["name"],
                    "date": date,
                    "content": entry.get("summary", ""),
                    "source_url": url,
                    "collected_at": datetime.now().isoformat()
                })
                existing_urls.add(url)

            logger.info(f"  {feed_config['name']}: collected entries")

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
