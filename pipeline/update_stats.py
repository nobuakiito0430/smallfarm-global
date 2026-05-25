"""
SmallFarm Global — Statistics Update Script
Recomputes stats.json from current project/news/paper data.

Usage:
    python pipeline/update_stats.py
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("update_stats")


def load_json(filename: str) -> list:
    """Load a JSON file from the data directory."""
    filepath = DATA_DIR / filename
    if filepath.exists():
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
    return []


def compute_stats(projects: list, news: list, papers: list) -> dict:
    """Compute aggregate statistics from project data."""
    # Count unique countries
    countries = set()
    for p in projects:
        for c in (p.get("country") or []):
            if c != "Multiple":
                countries.add(c)

    # Total beneficiaries
    total_beneficiaries = sum(
        p.get("outcomes", {}).get("beneficiaries_total", 0)
        for p in projects
    )

    # Average income change
    income_values = [
        p["outcomes"]["income_change_pct"]
        for p in projects
        if p.get("outcomes", {}).get("income_change_pct")
    ]
    avg_income = round(sum(income_values) / len(income_values)) if income_values else 0

    # Region distribution
    regions = Counter(p.get("region", "Other") for p in projects)

    # Implementer distribution
    implementers = Counter(p.get("implementer", "Unknown") for p in projects)

    # Bottleneck frequency
    bottleneck_freq = Counter()
    for p in projects:
        for b in (p.get("bottlenecks") or []):
            bottleneck_freq[b.get("category", "unknown")] += 1

    # Success factor frequency
    success_freq = Counter()
    for p in projects:
        for s in (p.get("success_factors") or []):
            success_freq[s.get("category", "unknown")] += 1

    # Approach distribution
    approach_freq = Counter()
    for p in projects:
        for a in (p.get("approach") or []):
            approach_freq[a] += 1

    # Timeline (last 5 updates)
    sorted_projects = sorted(
        [p for p in projects if p.get("last_updated")],
        key=lambda x: x["last_updated"],
        reverse=True
    )
    timeline = []
    for p in sorted_projects[:5]:
        timeline.append({
            "date": p["last_updated"],
            "title": f"{p['name']} データ更新",
            "description": (p.get("description_ja") or p.get("description_en") or "")[:80] + "...",
            "type": "update"
        })

    # Display-friendly beneficiaries
    if total_beneficiaries >= 100000000:
        display = f"{total_beneficiaries / 100000000:.1f}億"
    elif total_beneficiaries >= 10000:
        display = f"{total_beneficiaries / 10000:.0f}万"
    else:
        display = str(total_beneficiaries)

    return {
        "total_projects": len(projects),
        "total_countries": len(countries),
        "total_beneficiaries": total_beneficiaries,
        "total_beneficiaries_display": display,
        "avg_income_change_pct": avg_income,
        "total_papers": len(papers),
        "total_news": len(news),
        "last_updated": datetime.now().strftime("%Y-%m-%d"),
        "regions": dict(regions.most_common()),
        "implementers": dict(implementers.most_common()),
        "bottleneck_frequency": dict(bottleneck_freq.most_common()),
        "success_factor_frequency": dict(success_freq.most_common()),
        "approaches": dict(approach_freq.most_common()),
        "timeline": timeline
    }


def main():
    """Main statistics update."""
    logger.info("=" * 60)
    logger.info("SmallFarm Global — Statistics Update")
    logger.info("=" * 60)

    projects = load_json("projects.json")
    news = load_json("news.json")
    papers = load_json("papers.json")

    logger.info(f"Projects: {len(projects)}, News: {len(news)}, Papers: {len(papers)}")

    stats = compute_stats(projects, news, papers)

    output_path = DATA_DIR / "stats.json"
    output_path.write_text(
        json.dumps(stats, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    logger.info(f"Stats updated: {output_path}")
    logger.info(f"  Projects: {stats['total_projects']}")
    logger.info(f"  Countries: {stats['total_countries']}")
    logger.info(f"  Beneficiaries: {stats['total_beneficiaries_display']}")
    logger.info(f"  Avg income change: +{stats['avg_income_change_pct']}%")
    logger.info("Statistics update complete!")


if __name__ == "__main__":
    main()
