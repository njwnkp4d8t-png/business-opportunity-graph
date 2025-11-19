"""
Business Category Standardization and Data Quality Script

Purpose:
    This script standardizes the 2,934+ unique business categories in the California
    businesses dataset by mapping them to a canonical NAICS-like taxonomy. It uses
    a two-phase approach:
    1. Rule-based mapping for common/clear categories
    2. LLM classification (OpenAI) for ambiguous cases

    Additionally, it validates data quality to ensure compatibility with Neo4j graph
    database ingestion.

Input:
    ca_businesses_with_ai_franchise copy.json - Raw business data with noisy categories

Output:
    ca_businesses_standardized.json - Cleaned data with standardized categories
    category_mapping_report.json - Detailed mapping statistics and decisions

Author: Business Opportunity Graph Team
Date: 2025-11-18
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple, Optional
from collections import defaultdict, Counter
import re
import logging

# Optional: OpenAI for LLM classification of ambiguous categories
try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("WARNING: openai package not installed. LLM classification will be skipped.")
    print("Install with: pip install openai")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('category_standardization.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


# NAICS-inspired taxonomy structure
# Level 1: Major sectors
# Level 2: Subsectors
# Level 3: Industry groups
CANONICAL_TAXONOMY = {
    "Food & Beverage": {
        "Restaurants": ["restaurant", "cafe", "diner", "eatery", "bistro", "grill"],
        "Fast Food": ["fast food", "quick service", "burger", "pizza", "sandwich", "taco"],
        "Coffee & Tea": ["coffee", "tea", "espresso", "cafe", "coffeehouse"],
        "Bars & Nightlife": ["bar", "pub", "lounge", "nightclub", "brewery", "tavern"],
        "Bakery & Desserts": ["bakery", "pastry", "dessert", "ice cream", "donut", "cake"],
        "Specialty Food": ["deli", "grocery", "market", "butcher", "seafood", "organic"]
    },

    "Retail": {
        "Clothing & Apparel": ["clothing", "apparel", "fashion", "boutique", "shoes", "accessories"],
        "General Merchandise": ["department store", "variety store", "discount", "warehouse"],
        "Specialty Retail": ["gift", "toys", "books", "music", "electronics", "hobby"],
        "Home & Garden": ["furniture", "home decor", "garden", "hardware", "appliances"],
        "Automotive Retail": ["auto parts", "tire", "accessories", "motorcycle"]
    },

    "Personal Services": {
        "Health & Beauty": ["salon", "spa", "barber", "nail", "beauty", "massage", "cosmetic"],
        "Fitness & Recreation": ["gym", "fitness", "yoga", "pilates", "martial arts", "dance"],
        "Dry Cleaning & Laundry": ["dry clean", "laundry", "alterations"],
        "Pet Services": ["pet grooming", "veterinary", "pet store", "animal"]
    },

    "Professional Services": {
        "Financial Services": ["bank", "credit union", "insurance", "financial", "investment", "tax"],
        "Real Estate": ["real estate", "property management", "realty"],
        "Legal Services": ["attorney", "lawyer", "legal", "law office"],
        "Accounting": ["accounting", "cpa", "bookkeeping"],
        "Consulting": ["consulting", "consultant", "advisory"]
    },

    "Healthcare": {
        "Medical Offices": ["doctor", "physician", "clinic", "medical", "dentist", "dental"],
        "Pharmacy": ["pharmacy", "drugstore", "prescription"],
        "Specialized Healthcare": ["chiropractor", "optometry", "physical therapy", "acupuncture"],
        "Mental Health": ["counseling", "therapy", "psychologist", "psychiatrist"]
    },

    "Automotive Services": {
        "Repair & Maintenance": ["auto repair", "mechanic", "oil change", "brake", "muffler"],
        "Car Wash & Detailing": ["car wash", "detailing", "auto spa"],
        "Towing & Roadside": ["towing", "roadside", "wrecker"]
    },

    "Home Services": {
        "Construction & Contractors": ["construction", "contractor", "builder", "remodeling"],
        "Plumbing & HVAC": ["plumbing", "plumber", "hvac", "heating", "cooling", "air conditioning"],
        "Electrical": ["electrical", "electrician"],
        "Cleaning Services": ["cleaning", "janitorial", "maid", "housekeeping"],
        "Landscaping": ["landscaping", "lawn care", "tree service", "gardening"]
    },

    "Education & Childcare": {
        "Schools": ["school", "academy", "learning center", "education"],
        "Tutoring": ["tutoring", "tutor", "test prep"],
        "Childcare": ["daycare", "preschool", "child care", "nursery"]
    },

    "Entertainment & Recreation": {
        "Arts & Entertainment": ["theater", "cinema", "movie", "entertainment", "museum"],
        "Sports & Recreation": ["sports", "recreation", "bowling", "golf", "skating"],
        "Events & Venues": ["event", "venue", "banquet", "catering"]
    },

    "Lodging": {
        "Hotels & Motels": ["hotel", "motel", "inn", "lodge"],
        "Alternative Lodging": ["bed and breakfast", "hostel", "vacation rental"]
    },

    "Technology": {
        "IT Services": ["computer repair", "it services", "tech support", "software"],
        "Telecommunications": ["wireless", "phone", "mobile", "telecom"]
    },

    "Other Services": {
        "Business Services": ["printing", "shipping", "mailing", "packaging", "copy"],
        "Travel Services": ["travel agency", "travel", "tour"],
        "Miscellaneous": []  # Catch-all for unclassified
    }
}


class CategoryStandardizer:
    """
    Standardizes business categories using rule-based mapping and LLM classification.
    """

    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the standardizer.

        Args:
            openai_api_key: OpenAI API key for LLM classification (optional)
        """
        self.taxonomy = CANONICAL_TAXONOMY
        self.category_map = self._build_category_map()
        self.openai_api_key = openai_api_key

        if openai_api_key and OPENAI_AVAILABLE:
            openai.api_key = openai_api_key
            logger.info("OpenAI API key configured for LLM classification")
        elif openai_api_key and not OPENAI_AVAILABLE:
            logger.warning("OpenAI API key provided but openai package not installed")

        # LLM usage safeguards to avoid runaway cost:
        # - MAX_LLM_CATEGORIES: cap on how many unique categories
        #   will ever be sent to the LLM.
        # - LLM_BATCH_SIZE: how many categories per request.
        try:
            self.max_llm_categories = int(os.getenv("MAX_LLM_CATEGORIES", "250"))
        except ValueError:
            self.max_llm_categories = 250

        try:
            self.llm_batch_size = int(os.getenv("LLM_BATCH_SIZE", "20"))
        except ValueError:
            self.llm_batch_size = 20

        # Model name can be overridden via OPENAI_MODEL
        self.llm_model = os.getenv("OPENAI_MODEL", "gpt-4")

    def _build_category_map(self) -> Dict[str, Tuple[str, str]]:
        """
        Build a mapping from keywords to (sector, subsector) tuples.

        Returns:
            Dictionary mapping keywords to taxonomy paths
        """
        category_map = {}

        for sector, subsectors in self.taxonomy.items():
            for subsector, keywords in subsectors.items():
                for keyword in keywords:
                    category_map[keyword.lower()] = (sector, subsector)

        logger.info(f"Built category map with {len(category_map)} keyword mappings")
        return category_map

    def _normalize_category(self, category: str) -> str:
        """
        Normalize a category string for matching.

        Args:
            category: Raw category string

        Returns:
            Normalized category string
        """
        if not category:
            return ""

        # Convert to lowercase and remove extra whitespace
        normalized = category.lower().strip()

        # Remove common suffixes and prefixes
        normalized = re.sub(r'\s*(services?|store|shop|center|company|inc\.?|llc|corp\.?)\s*$', '', normalized)

        # Replace multiple spaces with single space
        normalized = re.sub(r'\s+', ' ', normalized)

        return normalized

    def _rule_based_classification(self, category: str) -> Optional[Tuple[str, str, float]]:
        """
        Classify category using rule-based keyword matching.

        Args:
            category: Category string to classify

        Returns:
            Tuple of (sector, subsector, confidence) or None if no match
        """
        normalized = self._normalize_category(category)

        if not normalized:
            return None

        # Direct keyword match
        for keyword, (sector, subsector) in self.category_map.items():
            if keyword in normalized:
                # Calculate confidence based on match quality
                if normalized == keyword:
                    confidence = 1.0  # Exact match
                elif normalized.startswith(keyword) or normalized.endswith(keyword):
                    confidence = 0.9  # Strong match
                else:
                    confidence = 0.8  # Partial match

                return (sector, subsector, confidence)

        return None

    def _llm_classification_batch(
        self, categories: List[str]
    ) -> Dict[str, Tuple[str, str, float]]:
        """
        Classify a batch of categories using OpenAI LLM.

        Returns a mapping:
            category -> (sector, subsector, confidence)

        Any category that cannot be reliably parsed or validated
        will be omitted from the returned mapping and should be
        treated as unclassified by the caller.
        """
        if not self.openai_api_key or not OPENAI_AVAILABLE:
            return {}

        if not categories:
            return {}

        # Build taxonomy description for prompt once
        taxonomy_desc = []
        for sector, subsectors in self.taxonomy.items():
            subsector_names = ", ".join(subsectors.keys())
            taxonomy_desc.append(f"{sector}: {subsector_names}")

        taxonomy_str = "\n".join(taxonomy_desc)

        # Construct prompt asking for a JSON array with one object per category.
        payload = {
            "taxonomy": taxonomy_str,
            "categories": categories,
        }

        system_msg = (
            "You are a business classification expert. "
            "You must classify each category into the provided taxonomy. "
            "Return ONLY a JSON array where each element has the form:\n"
            '{"category": "...", "sector": "...", "subsector": "...", "confidence": 0.0-1.0}'
        )

        user_msg = (
            "Classify the following business categories into the taxonomy.\n\n"
            "The taxonomy is:\n"
            f"{taxonomy_str}\n\n"
            "Categories (JSON):\n"
            f"{json.dumps(categories)}\n\n"
            "Rules:\n"
            "- sector and subsector must come from the taxonomy.\n"
            "- confidence must be between 0.0 and 1.0.\n"
            "- If you cannot confidently classify a category, use:\n"
            '  sector = "Other Services", subsector = "Miscellaneous", confidence = 0.5\n\n'
            "Return ONLY a JSON array as described."
        )

        try:
            response = openai.ChatCompletion.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.3,
                max_tokens=400,
            )

            result_text = response.choices[0].message.content.strip()

            try:
                parsed = json.loads(result_text)
            except json.JSONDecodeError:
                # Try to extract a JSON array from the response
                json_match = re.search(r"\[.*\]", result_text, re.DOTALL)
                if not json_match:
                    logger.warning(
                        "LLM returned non-JSON response for batch %s: %s",
                        categories,
                        result_text,
                    )
                    return {}
                try:
                    parsed = json.loads(json_match.group())
                except json.JSONDecodeError as exc:
                    logger.warning(
                        "LLM batch JSON parse failed for %s: %s", categories, exc
                    )
                    return {}

            if not isinstance(parsed, list):
                logger.warning(
                    "LLM batch result is not a list for categories %s: %s",
                    categories,
                    result_text,
                )
                return {}

            mapping: Dict[str, Tuple[str, str, float]] = {}

            for item in parsed:
                if not isinstance(item, dict):
                    continue

                cat = str(item.get("category", "")).strip()
                sector = item.get("sector")
                subsector = item.get("subsector")
                try:
                    confidence = float(item.get("confidence", 0.5))
                except (TypeError, ValueError):
                    confidence = 0.5

                if not cat:
                    continue

                # Validate against taxonomy
                if sector in self.taxonomy and subsector in self.taxonomy[sector]:
                    mapping[cat] = (sector, subsector, confidence)

            return mapping

        except Exception as e:
            logger.error(
                "LLM batch classification failed for categories %s: %s", categories, str(e)
            )
            return {}

    @staticmethod
    def _default_classification(category: str) -> Dict[str, Any]:
        """Fallback classification when neither rules nor LLM can help."""
        return {
            "original_category": category,
            "standardized_sector": "Other Services",
            "standardized_subsector": "Miscellaneous",
            "confidence": 0.0,
            "method": "unclassified",
        }

    def classify_categories_bulk(
        self, categories: List[str]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Classify a list of unique categories using a hybrid approach.

        - Always attempts rule-based classification first.
        - For categories that fail rules, uses the LLM in small batches,
          respecting MAX_LLM_CATEGORIES and LLM_BATCH_SIZE limits.
        - Any remaining or failed items fall back to the default
          "Other Services / Miscellaneous" bucket.
        """
        # Deduplicate while preserving order
        seen: Set[str] = set()
        unique_categories: List[str] = []
        for cat in categories:
            key = cat or "Unknown"
            if key not in seen:
                seen.add(key)
                unique_categories.append(key)

        mappings: Dict[str, Dict[str, Any]] = {}
        ambiguous: List[str] = []

        # First pass: rule-based classification
        for category in unique_categories:
            rule_result = self._rule_based_classification(category)
            if rule_result:
                sector, subsector, confidence = rule_result
                mappings[category] = {
                    "original_category": category,
                    "standardized_sector": sector,
                    "standardized_subsector": subsector,
                    "confidence": confidence,
                    "method": "rule_based",
                }
            else:
                ambiguous.append(category)

        # If LLM is not available or not configured, mark all ambiguous as unclassified
        if not (self.openai_api_key and OPENAI_AVAILABLE and self.max_llm_categories > 0):
            for category in ambiguous:
                mappings[category] = self._default_classification(category)
            return mappings

        # Respect global cap on how many unique categories we ever send to the LLM
        llm_targets = ambiguous[: self.max_llm_categories]
        skipped_for_cost = ambiguous[self.max_llm_categories :]

        if skipped_for_cost:
            logger.info(
                "Skipping LLM classification for %d categories due to MAX_LLM_CATEGORIES=%d",
                len(skipped_for_cost),
                self.max_llm_categories,
            )

        # Batch LLM calls
        for i in range(0, len(llm_targets), max(self.llm_batch_size, 1)):
            batch = llm_targets[i : i + max(self.llm_batch_size, 1)]
            llm_results = self._llm_classification_batch(batch)

            for category in batch:
                if category in llm_results:
                    sector, subsector, confidence = llm_results[category]
                    mappings[category] = {
                        "original_category": category,
                        "standardized_sector": sector,
                        "standardized_subsector": subsector,
                        "confidence": confidence,
                        "method": "llm",
                    }
                else:
                    mappings[category] = self._default_classification(category)

        # Any categories not processed by LLM (because of caps) default to unclassified
        for category in skipped_for_cost:
            mappings[category] = self._default_classification(category)

        return mappings


class DataQualityValidator:
    """
    Validates data quality for Neo4j compatibility.
    """

    def __init__(self):
        self.issues = defaultdict(list)
        self.stats = defaultdict(int)
        # Track business_ids we have already seen to guarantee uniqueness
        self.seen_business_ids: Set[str] = set()

    @staticmethod
    def _normalize_schema(record: dict) -> dict:
        """
        Normalize raw record keys into a consistent schema expected by the
        rest of the pipeline. This makes the script resilient to different
        export formats (e.g., name vs business_name, categories list vs
        single category string).
        """
        cleaned = record.copy()

        # 1) Business name: prefer explicit business_name
        if "business_name" not in cleaned and cleaned.get("name"):
            cleaned["business_name"] = cleaned["name"]

        # 2) Primary category: derive from categories list when needed
        if "category" not in cleaned:
            categories = cleaned.get("categories")
            if isinstance(categories, list) and categories:
                primary = str(categories[0]).strip()
                cleaned["category"] = primary or "Unknown"
                cleaned["categories_raw"] = categories
            elif isinstance(categories, str) and categories.strip():
                cleaned["category"] = categories.strip()

        # 3) ZIP code: normalise zip -> zip_code string
        if "zip_code" not in cleaned and cleaned.get("zip") is not None:
            cleaned["zip_code"] = str(cleaned["zip"]).strip()

        # 4) Business identifier: derive from source id if needed
        if "business_id" not in cleaned or not cleaned.get("business_id"):
            source_id = cleaned.get("business_id") or cleaned.get("id")
            if source_id is not None:
                cleaned["business_id"] = f"ca_biz_{source_id}"

        # 5) Franchise metadata (INDEPENDENT vs FRANCHISE)
        if "franchise" in cleaned and cleaned["franchise"] is not None:
            raw = str(cleaned["franchise"]).strip().upper()
            if raw in {"FRANCHISE", "CHAIN"}:
                cleaned["franchise_type"] = "FRANCHISE"
                cleaned["is_franchise"] = True
            elif raw in {"INDEPENDENT", "LOCAL"}:
                cleaned["franchise_type"] = "INDEPENDENT"
                cleaned["is_franchise"] = False
            else:
                cleaned["franchise_type"] = raw or "UNKNOWN"

        # 6) Rating normalisation
        if "avg_rating" in cleaned and cleaned["avg_rating"] is not None:
            try:
                rating = float(cleaned["avg_rating"])
                cleaned["avg_rating"] = rating if 0.0 <= rating <= 5.0 else None
            except (TypeError, ValueError):
                cleaned["avg_rating"] = None

        # 7) Block group normalisation (zero‑padded string for joins)
        if "blockgroup" in cleaned and cleaned["blockgroup"] is not None:
            bg = str(cleaned["blockgroup"]).strip()
            if bg.isdigit():
                cleaned["blockgroup"] = bg.zfill(6)

        return cleaned

    def validate_record(self, record: dict, index: int) -> dict:
        """
        Validate a single business record.

        Args:
            record: Business record dictionary
            index: Record index for error reporting

        Returns:
            Cleaned record
        """
        cleaned = self._normalize_schema(record)
        record_id = f"record_{index}"

        # Check for required fields
        required_fields = ["business_name", "category"]
        for field in required_fields:
            if not record.get(field):
                self.issues["missing_required_fields"].append((record_id, field))

        # Validate and clean business_name
        if "business_name" in cleaned:
            name = str(cleaned["business_name"]).strip()
            if not name:
                self.issues["empty_business_name"].append(record_id)
            elif len(name) > 200:
                self.issues["long_business_name"].append(record_id)
                cleaned["business_name"] = name[:200]
            else:
                cleaned["business_name"] = name

        # Validate category
        if "category" in cleaned:
            category = str(cleaned["category"]).strip()
            if not category:
                self.issues["empty_category"].append(record_id)
                cleaned["category"] = "Unknown"
            else:
                cleaned["category"] = category

        # Validate location data (important for Neo4j spatial queries)
        if "latitude" in cleaned and "longitude" in cleaned:
            try:
                lat = float(cleaned["latitude"])
                lon = float(cleaned["longitude"])

                # California bounds check (roughly)
                if not (32.5 <= lat <= 42.0 and -124.5 <= lon <= -114.0):
                    self.issues["invalid_coordinates"].append(record_id)
                    cleaned["has_valid_coordinates"] = False
                else:
                    cleaned["has_valid_coordinates"] = True

                cleaned["latitude"] = lat
                cleaned["longitude"] = lon

            except (ValueError, TypeError):
                self.issues["invalid_coordinates"].append(record_id)
                cleaned["latitude"] = None
                cleaned["longitude"] = None
                cleaned["has_valid_coordinates"] = False

        # If lat/lon are missing but we have a WKT geom string, attempt recovery
        if (cleaned.get("latitude") is None or cleaned.get("longitude") is None) and cleaned.get("geom"):
            geom = str(cleaned["geom"])
            match = re.search(r"POINT\s*\(([-\d\.]+)\s+([-\d\.]+)\)", geom)
            if match:
                try:
                    lon = float(match.group(1))
                    lat = float(match.group(2))
                    cleaned["longitude"] = lon
                    cleaned["latitude"] = lat
                    if 32.5 <= lat <= 42.0 and -124.5 <= lon <= -114.0:
                        cleaned["has_valid_coordinates"] = True
                except ValueError:
                    self.issues["invalid_geom_coordinates"].append(record_id)

        # Clean phone numbers
        if "phone" in cleaned and cleaned["phone"]:
            phone = re.sub(r"[^\d]", "", str(cleaned["phone"]))
            cleaned["phone"] = phone if len(phone) == 10 else None

        # Clean zip codes
        if "zip_code" in cleaned and cleaned["zip_code"]:
            zip_code = str(cleaned["zip_code"]).strip()
            if not re.match(r"^\d{5}(-\d{4})?$", zip_code):
                self.issues["invalid_zip_code"].append(record_id)
            else:
                # Normalise to 5‑digit base ZIP for territory joins
                cleaned["zip_code"] = zip_code[:5]

        # Ensure unique identifiers exist for Neo4j nodes
        if "business_id" not in cleaned or not cleaned["business_id"]:
            # Generate from available data
            cleaned["business_id"] = f"biz_{index}_{hash(cleaned.get('business_name', ''))}"

        # Enforce uniqueness of business_id across the dataset
        bid = str(cleaned["business_id"])
        if bid in self.seen_business_ids:
            self.issues["duplicate_business_id"].append((record_id, bid))
            cleaned["business_id_original"] = bid
            bid = f"{bid}_{index}"
            cleaned["business_id"] = bid
        self.seen_business_ids.add(bid)

        return cleaned

    def generate_report(self) -> dict:
        """
        Generate data quality report.

        Returns:
            Dictionary with quality metrics
        """
        total_issues = sum(len(issues) for issues in self.issues.values())

        return {
            "total_issues": total_issues,
            "issues_by_type": {k: len(v) for k, v in self.issues.items()},
            "detailed_issues": dict(self.issues)
        }


def load_data(file_path: str) -> List[dict]:
    """
    Load business data from JSON file.

    Args:
        file_path: Path to JSON file

    Returns:
        List of business records
    """
    logger.info(f"Loading data from {file_path}")

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if isinstance(data, list):
            logger.info(f"Loaded {len(data)} records")
            return data
        elif isinstance(data, dict) and "businesses" in data:
            logger.info(f"Loaded {len(data['businesses'])} records")
            return data["businesses"]
        else:
            logger.error("Unexpected JSON structure")
            return []

    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON: {str(e)}")
        return []


def analyze_categories(data: List[dict]) -> Dict[str, int]:
    """
    Analyze category distribution in the dataset.

    Args:
        data: List of business records

    Returns:
        Dictionary with category counts
    """
    logger.info("Analyzing category distribution")

    categories = [record.get("category", "Unknown") for record in data]
    category_counts = Counter(categories)

    logger.info(f"Found {len(category_counts)} unique categories")
    logger.info(f"Top 10 categories: {category_counts.most_common(10)}")

    return dict(category_counts)


def process_data(input_file: str, output_file: str, openai_api_key: Optional[str] = None):
    """
    Main processing function.

    Args:
        input_file: Path to input JSON file
        output_file: Path to output JSON file
        openai_api_key: Optional OpenAI API key for LLM classification
    """
    logger.info("=" * 80)
    logger.info("Business Category Standardization Process Starting")
    logger.info("=" * 80)

    # Load data
    data = load_data(input_file)
    if not data:
        logger.error("No data loaded. Exiting.")
        return

    # Initialize standardizer and validator
    standardizer = CategoryStandardizer(openai_api_key)
    validator = DataQualityValidator()

    # First pass: validate / clean all records
    logger.info("Validating and normalizing records...")
    cleaned_records: List[Dict[str, Any]] = []
    for index, record in enumerate(data):
        if index % 100 == 0:
            logger.info("Validated %d/%d records", index, len(data))
        cleaned_records.append(validator.validate_record(record, index))

    # Analyze categories (for logging / diagnostics only)
    analyze_categories(cleaned_records)

    # Build unique list of categories for classification
    unique_categories = sorted(
        {rec.get("category", "Unknown") for rec in cleaned_records}
    )
    logger.info("Classifying %d unique categories", len(unique_categories))

    category_mappings = standardizer.classify_categories_bulk(unique_categories)

    # Second pass: attach standardized category info
    logger.info("Attaching standardized categories to records...")
    standardized_data: List[Dict[str, Any]] = []

    for rec in cleaned_records:
        category = rec.get("category", "Unknown")
        classification = category_mappings.get(category) or CategoryStandardizer._default_classification(category)

        rec["category_original"] = category
        rec["category_sector"] = classification["standardized_sector"]
        rec["category_subsector"] = classification["standardized_subsector"]
        rec["category_confidence"] = classification["confidence"]
        rec["category_method"] = classification["method"]

        standardized_data.append(rec)

    logger.info(f"Completed processing {len(standardized_data)} records")

    # Generate reports
    quality_report = validator.generate_report()

    classification_report = {
        "total_unique_categories": len(category_mappings),
        "methods": {
            "rule_based": sum(1 for m in category_mappings.values() if m["method"] == "rule_based"),
            "llm": sum(1 for m in category_mappings.values() if m["method"] == "llm"),
            "unclassified": sum(1 for m in category_mappings.values() if m["method"] == "unclassified")
        },
        "confidence_distribution": {
            "high (>0.8)": sum(1 for m in category_mappings.values() if m["confidence"] > 0.8),
            "medium (0.5-0.8)": sum(1 for m in category_mappings.values() if 0.5 <= m["confidence"] <= 0.8),
            "low (<0.5)": sum(1 for m in category_mappings.values() if m["confidence"] < 0.5)
        },
        "sector_distribution": Counter(m["standardized_sector"] for m in category_mappings.values()),
        "category_mappings": category_mappings
    }

    # Save standardized data (slim planner-friendly view)
    logger.info(f"Saving standardized data to {output_file}")
    slim_fields = [
        # Identity / location
        "business_id",
        "business_name",
        "address",
        "city",
        "zip_code",
        "blockgroup",
        "latitude",
        "longitude",
        "has_valid_coordinates",
        # Franchise metadata
        "franchise",
        "franchise_type",
        "is_franchise",
        "confidence",
        "reasoning",
        # Categories
        "categories_raw",
        "category_original",
        "category_sector",
        "category_subsector",
        "category_confidence",
        "category_method",
        # Quality / scoring
        "avg_rating",
        # Optional link for UI
        "url",
    ]

    slim_records: List[Dict[str, Any]] = []
    for rec in standardized_data:
        slim = {key: rec.get(key) for key in slim_fields if key in rec}
        slim_records.append(slim)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(slim_records, f, indent=2, ensure_ascii=False)

    # Save reports
    report_file = output_file.replace('.json', '_mapping_report.json')
    logger.info(f"Saving mapping report to {report_file}")

    full_report = {
        "summary": {
            "total_records": len(standardized_data),
            "unique_categories": len(category_mappings),
            "data_quality_issues": quality_report["total_issues"]
        },
        "classification_report": {k: v for k, v in classification_report.items() if k != "category_mappings"},
        "quality_report": quality_report,
        "detailed_mappings": classification_report["category_mappings"]
    }

    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(full_report, f, indent=2, ensure_ascii=False)

    # Print summary
    logger.info("=" * 80)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 80)
    logger.info(f"Total records processed: {len(standardized_data)}")
    logger.info(f"Unique categories: {len(category_mappings)}")
    logger.info(f"Classification methods:")
    logger.info(f"  - Rule-based: {classification_report['methods']['rule_based']}")
    logger.info(f"  - LLM: {classification_report['methods']['llm']}")
    logger.info(f"  - Unclassified: {classification_report['methods']['unclassified']}")
    logger.info(f"Data quality issues: {quality_report['total_issues']}")
    logger.info(f"\nOutput files:")
    logger.info(f"  - Standardized data: {output_file}")
    logger.info(f"  - Mapping report: {report_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Configuration
    BASE_DIR = Path(__file__).parent.parent
    INPUT_FILE = BASE_DIR / "data" / "ca_businesses_with_ai_franchise copy.json"
    OUTPUT_FILE = BASE_DIR / "data" / "ca_businesses_standardized.json"

    # Get OpenAI API key from environment (optional)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

    if not INPUT_FILE.exists():
        logger.error(f"Input file not found: {INPUT_FILE}")
        sys.exit(1)

    # Run processing
    process_data(
        input_file=str(INPUT_FILE),
        output_file=str(OUTPUT_FILE),
        openai_api_key=OPENAI_API_KEY
    )
