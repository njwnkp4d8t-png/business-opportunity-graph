"""
Territory-level aggregation helper for standardized business data.

Purpose
-------
Takes the output of ``standardize_business_categories.py`` and
aggregates it into territory-level metrics that are easier to use
inside the franchise territory planner (e.g., ZIP, block group,
or city summaries).

Input
-----
Expected input is a JSON array where each element is a "cleaned"
business record with at least the following fields (all produced by
``standardize_business_categories.py``):

    business_id                : unique identifier
    business_name              : cleaned name
    category_sector            : canonical sector
    category_subsector         : canonical subsector
    category_confidence        : float [0.0, 1.0]
    category_method            : 'rule_based' | 'llm' | 'unclassified'
    has_valid_coordinates      : optional bool
    zip_code                   : normalized 5-digit ZIP (optional)
    blockgroup                 : normalized block group string (optional)
    city                       : city name (optional)
    franchise_type             : 'FRANCHISE' | 'INDEPENDENT' | 'UNKNOWN'
    is_franchise               : optional bool
    avg_rating                 : optional float [0.0, 5.0]

Output
------
JSON file containing:

    {
      "group_by": "<field>",
      "summary": {... overall stats ...},
      "territories": [
        {
          "territory_id": "<value of group field>",
          "business_count": int,
          "franchise_count": int,
          "independent_count": int,
          "unknown_franchise_count": int,
          "pct_franchise": float | null,
          "pct_independent": float | null,
          "has_valid_coordinates_count": int,
          "pct_valid_coordinates": float | null,
          "avg_rating_mean": float | null,
          "classification_confidence_mean": float | null,
          "classification_method_counts": {...},
          "top_sectors": [{"name": str, "count": int}],
          "top_subsectors": [{"name": str, "count": int}]
        },
        ...
      ]
    }

Usage
-----
From the project root:

    python -m scripts.aggregate_territory_metrics \
        --input data/ca_businesses_standardized.json \
        --group-by zip_code
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List


logger = logging.getLogger(__name__)


def _safe_mean(total: float, count: int) -> float | None:
    if count <= 0:
        return None
    return total / count


def _top_n(counter: Counter, n: int) -> List[Dict[str, Any]]:
    """
    Return the top-n items from a Counter as a list of
    ``{"name": <key>, "count": <value>}`` dictionaries.

    Guards against non-positive ``n`` and empty counters.
    """
    if n <= 0 or not counter:
        return []
    return [{"name": name, "count": count} for name, count in counter.most_common(n)]


def aggregate_territories(
    records: List[Dict[str, Any]],
    group_by: str = "zip_code",
    top_n: int = 5,
) -> Dict[str, Any]:
    """
    Aggregate standardized business records into territory-level metrics.

    Parameters
    ----------
    records:
        List of cleaned business records (dicts).
    group_by:
        Field name to group by (e.g. 'zip_code', 'blockgroup', 'city').
    top_n:
        Number of top sectors/subsectors to include per territory.
        Values <= 0 disable the "top lists".
    """

    territories: Dict[str, Dict[str, Any]] = {}

    # Normalise top_n to be non-negative
    if top_n < 0:
        top_n = 0

    for rec in records:
        key_raw = rec.get(group_by)
        key = str(key_raw).strip() if key_raw not in (None, "") else "UNKNOWN"

        t = territories.get(key)
        if not t:
            t = {
                "territory_id": key,
                "business_count": 0,
                "franchise_count": 0,
                "independent_count": 0,
                "unknown_franchise_count": 0,
                "has_valid_coordinates_count": 0,
                "avg_rating_sum": 0.0,
                "avg_rating_n": 0,
                "class_conf_sum": 0.0,
                "class_conf_n": 0,
                "classification_method_counts": Counter(),
                "sector_counts": Counter(),
                "subsector_counts": Counter(),
            }
            territories[key] = t

        t["business_count"] += 1

        # Franchise breakdown
        is_franchise = rec.get("is_franchise")
        if is_franchise is True:
            t["franchise_count"] += 1
        elif is_franchise is False:
            t["independent_count"] += 1
        else:
            t["unknown_franchise_count"] += 1

        # Coordinates
        if rec.get("has_valid_coordinates") is True:
            t["has_valid_coordinates_count"] += 1

        # Rating
        rating = rec.get("avg_rating")
        if isinstance(rating, (int, float)):
            t["avg_rating_sum"] += float(rating)
            t["avg_rating_n"] += 1

        # Classification confidence
        conf = rec.get("category_confidence")
        if isinstance(conf, (int, float)):
            t["class_conf_sum"] += float(conf)
            t["class_conf_n"] += 1

        # Classification method
        method = (rec.get("category_method") or "unclassified").strip()
        t["classification_method_counts"][method] += 1

        # Sector/subsector distributions
        sector = rec.get("category_sector") or "Unknown"
        subsector = rec.get("category_subsector") or "Unknown"
        t["sector_counts"][sector] += 1
        t["subsector_counts"][subsector] += 1

    # Build output structure
    territory_list: List[Dict[str, Any]] = []
    total_businesses = 0

    for key, t in sorted(territories.items(), key=lambda kv: kv[0]):
        business_count = t["business_count"]
        total_businesses += business_count

        franchise_count = t["franchise_count"]
        independent_count = t["independent_count"]
        unknown_franchise_count = t["unknown_franchise_count"]

        pct_franchise = (
            franchise_count / business_count if business_count else None
        )
        pct_independent = (
            independent_count / business_count if business_count else None
        )

        has_valid_coords = t["has_valid_coordinates_count"]
        pct_valid_coords = (
            has_valid_coords / business_count if business_count else None
        )

        territory_list.append(
            {
                "territory_id": key,
                "business_count": business_count,
                "franchise_count": franchise_count,
                "independent_count": independent_count,
                "unknown_franchise_count": unknown_franchise_count,
                "pct_franchise": pct_franchise,
                "pct_independent": pct_independent,
                "has_valid_coordinates_count": has_valid_coords,
                "pct_valid_coordinates": pct_valid_coords,
                "avg_rating_mean": _safe_mean(t["avg_rating_sum"], t["avg_rating_n"]),
                "classification_confidence_mean": _safe_mean(
                    t["class_conf_sum"], t["class_conf_n"]
                ),
                "classification_method_counts": dict(
                    t["classification_method_counts"]
                ),
                "top_sectors": _top_n(t["sector_counts"], top_n),
                "top_subsectors": _top_n(t["subsector_counts"], top_n),
            }
        )

    summary = {
        "group_by": group_by,
        "territory_count": len(territories),
        "total_businesses": total_businesses,
    }

    return {
        "group_by": group_by,
        "summary": summary,
        "territories": territory_list,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Aggregate standardized businesses into territory-level metrics."
    )
    parser.add_argument(
        "--input",
        type=str,
        default=str(Path("data") / "ca_businesses_standardized.json"),
        help="Path to standardized business JSON (default: data/ca_businesses_standardized.json)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output JSON path (default: data/ca_businesses_standardized_by_<group>.json)",
    )
    parser.add_argument(
        "--group-by",
        type=str,
        default="zip_code",
        choices=["zip_code", "blockgroup", "city"],
        help="Field to group by (default: zip_code)",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=5,
        help="Number of top sectors/subsectors per territory (default: 5)",
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )

    input_path = Path(args.input)
    if not input_path.exists():
        logger.error("Input file not found: %s", input_path)
        raise SystemExit(1)

    logger.info("Loading standardized data from %s", input_path)
    try:
        with input_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse JSON from %s: %s", input_path, exc)
        raise SystemExit(1)
    except OSError as exc:
        logger.error("Failed to read %s: %s", input_path, exc)
        raise SystemExit(1)

    if not isinstance(data, list):
        logger.error("Expected a JSON array of records; got %s", type(data))
        raise SystemExit(1)

    logger.info(
        "Aggregating %d records by %s", len(data), args.group_by
    )
    result = aggregate_territories(
        records=data, group_by=args.group_by, top_n=args.top_n
    )

    if args.output:
        output_path = Path(args.output)
    else:
        output_name = (
            f"ca_businesses_standardized_by_{args.group_by}.json"
        )
        output_path = Path("data") / output_name

    output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Writing territory metrics to %s", output_path)
    try:
        with output_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except OSError as exc:
        logger.error("Failed to write %s: %s", output_path, exc)
        raise SystemExit(1)

    logger.info("Aggregation complete: %d territories", result["summary"]["territory_count"])


if __name__ == "__main__":
    main()
