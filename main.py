"""
End-to-end lead pipeline:

  1. Scrape Google Maps for one or more niches in a city
  2. Dedupe by phone number
  3. Enrich each lead's website (or flag "no website")
  4. Score + segment by which Devtacet service line fits best
  5. Write everything to a CSV, sorted by score (hottest leads first)

Usage:
    python main.py --niches "restaurants,dentists,gyms" --city "Lucknow" \
                    --max-results 25 --output leads.csv

Notes:
  - Scraping Google Maps may violate Google's Terms of Service. Use
    reasonable rate limits, don't run this at huge scale, and treat it
    as a manual prospecting aid, not a production data pipeline.
  - This needs a real network connection to google.com and to each
    lead's own website, so it will not run inside a sandboxed
    environment with restricted egress. Run it on your own machine.
"""

import argparse
import csv
import time

from gmaps_scraper import GoogleMapsScraper
from enrich import analyze_website
from scorer import score_lead


def dedupe(businesses):
    seen_phones = set()
    seen_names = set()
    unique = []
    for b in businesses:
        phone = (b.get("phone") or "").strip()
        name = (b.get("name") or "").strip().lower()
        key = phone if phone else name
        if key in seen_phones or key in seen_names:
            continue
        if phone:
            seen_phones.add(phone)
        seen_names.add(name)
        unique.append(b)
    return unique


def run_pipeline(niches, city, max_results_per_niche, headless=True, delay_between_sites=1.0):
    scraper = GoogleMapsScraper(headless=headless)
    all_businesses = []

    try:
        for niche in niches:
            query = f"{niche.strip()} in {city.strip()}"
            print(f"[scrape] {query}")
            results = scraper.search(query, max_results=max_results_per_niche)
            print(f"  -> found {len(results)} listings")
            all_businesses.extend(results)
    finally:
        scraper.close()

    all_businesses = dedupe(all_businesses)
    print(f"[dedupe] {len(all_businesses)} unique leads")

    enriched_rows = []
    for i, business in enumerate(all_businesses, 1):
        website = business.get("website")
        print(f"[enrich {i}/{len(all_businesses)}] {business.get('name')} -> {website or 'no website'}")
        web = analyze_website(website)
        score_result = score_lead(business, web)

        row = {
            **business,
            "has_website": web["has_website"],
            "site_reachable": web["reachable"],
            "mobile_friendly": web["mobile_friendly"],
            "is_https": web["is_https"],
            "has_meta_description": web["has_meta_description"],
            "has_schema_markup": web["has_schema_markup"],
            "recommended_service": score_result["recommended_service"],
            "lead_score": score_result["total_score"],
            "score_reasons": score_result["reasons"],
        }
        enriched_rows.append(row)

        if website:
            time.sleep(delay_between_sites)

    enriched_rows.sort(key=lambda r: r["lead_score"], reverse=True)
    return enriched_rows


def write_csv(rows, output_path):
    if not rows:
        print("No rows to write.")
        return
    fieldnames = list(rows[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[done] wrote {len(rows)} leads to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Devtacet Google Maps lead pipeline")
    parser.add_argument("--niches", required=True, help="Comma-separated business types, e.g. 'restaurants,dentists,gyms'")
    parser.add_argument("--city", required=True, help="City to search in, e.g. 'Lucknow'")
    parser.add_argument("--max-results", type=int, default=25, help="Max listings to scrape per niche")
    parser.add_argument("--output", default="leads.csv", help="Output CSV path")
    parser.add_argument("--show-browser", action="store_true", help="Run with a visible browser window (useful for debugging)")
    args = parser.parse_args()

    niches = [n for n in args.niches.split(",") if n.strip()]
    rows = run_pipeline(
        niches=niches,
        city=args.city,
        max_results_per_niche=args.max_results,
        headless=not args.show_browser,
    )
    write_csv(rows, args.output)


if __name__ == "__main__":
    main()
