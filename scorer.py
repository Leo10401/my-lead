"""
Turns a scraped business + its website enrichment into per-service scores
and a single recommended service line for outreach.
"""

from config import (
    SCORING,
    APP_FRIENDLY_CATEGORIES,
    SYSTEM_SOFTWARE_CATEGORIES,
)


def score_lead(business: dict, web: dict) -> dict:
    category = (business.get("category") or "").lower()
    review_count = business.get("review_count") or 0

    scores = {
        "Website/SEO": 0,
        "Website Redesign": 0,
        "Android App": 0,
        "SEO": 0,
        "System Software": 0,
    }
    reasons = []

    if not web["has_website"]:
        scores["Website/SEO"] += SCORING["no_website"]
        reasons.append("No website found on Google Maps listing")
    else:
        if web["reachable"] and not web["mobile_friendly"]:
            scores["Website Redesign"] += SCORING["website_not_mobile_friendly"]
            reasons.append("Website is not mobile-friendly (no viewport tag)")

        if web["reachable"] and not web["is_https"]:
            scores["Website Redesign"] += SCORING["website_no_https"]
            reasons.append("Website does not use HTTPS")

        if web["reachable"] and not web["has_meta_description"]:
            scores["SEO"] += SCORING["website_no_meta_description"]
            reasons.append("Missing meta description")

        if web["reachable"] and not web["has_schema_markup"]:
            scores["SEO"] += SCORING["no_schema_markup"]
            reasons.append("No schema/structured data on site")

        if not web.get("reachable", True) and web.get("error"):
            scores["Website Redesign"] += SCORING["website_not_mobile_friendly"]
            reasons.append(f"Website unreachable: {web['error']}")

    is_app_friendly = any(cat in category for cat in APP_FRIENDLY_CATEGORIES)
    if is_app_friendly and not web.get("has_ordering_keywords", False):
        scores["Android App"] += SCORING["app_friendly_category_no_ordering_keywords"]
        reasons.append("Category typically needs bookings/ordering, none detected on site")

    is_system_software_candidate = any(cat in category for cat in SYSTEM_SOFTWARE_CATEGORIES)
    if is_system_software_candidate:
        scores["System Software"] += SCORING["system_software_category"]
        reasons.append("Business type often runs manual inventory/records")

    if review_count and review_count < 10:
        scores["SEO"] += SCORING["low_review_count_established"]
        reasons.append("Low review count suggests weak online visibility")

    total_score = sum(scores.values())
    top_segment = max(scores, key=scores.get) if total_score > 0 else "Low priority"

    return {
        "total_score": total_score,
        "recommended_service": top_segment,
        "segment_scores": scores,
        "reasons": "; ".join(reasons),
    }
