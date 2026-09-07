# Devtacet Lead Pipeline

Scrapes Google Maps for businesses in a given city/niche, checks each one's
own website for gaps, and scores/segments every lead by which of your
service lines fits best: **website, website redesign, Android app, SEO, or
system software**.

## Setup (run this on your own machine, not in a sandbox)

```bash
pip install -r requirements.txt
playwright install chromium
```

## Run it

```bash
python main.py --niches "restaurants,dentists,gyms,salons" --city "Lucknow" --max-results 25 --output leads.csv
```

- `--niches` — comma-separated business types to search for
- `--city` — city to search in
- `--max-results` — how many listings to pull per niche (start small, e.g. 15-25, while testing)
- `--output` — CSV file path
- `--show-browser` — run with a visible Chromium window instead of headless, useful when debugging selectors

## What you get

A CSV sorted by `lead_score` (hottest leads first), with columns:

| Column | Meaning |
|---|---|
| `name`, `category`, `address`, `phone`, `website`, `rating`, `review_count` | Raw Google Maps data |
| `has_website`, `site_reachable`, `mobile_friendly`, `is_https`, `has_meta_description`, `has_schema_markup` | Website audit results |
| `recommended_service` | The single best-fit service line to pitch |
| `lead_score` | Overall opportunity score (higher = more gaps = better prospect) |
| `score_reasons` | Human-readable reasons behind the score, for your outreach message |

## Tuning

Open `config.py` to adjust:
- `APP_FRIENDLY_CATEGORIES` / `SYSTEM_SOFTWARE_CATEGORIES` — which business types map to which service
- `SCORING` — point values per gap, so you can weight things like "no website" more heavily than "no HTTPS"
- `ONLINE_ORDERING_KEYWORDS` — phrases that mean a business already has booking/ordering, so you don't pitch an app to someone who already has one

## Known limitations

- **Google's DOM changes.** The CSS selectors in `gmaps_scraper.py` are based on Google Maps' current layout. If scraping suddenly returns 0 results, run with `--show-browser` and inspect the page — a selector probably needs updating.
- **Rate limiting / blocking.** Don't hammer Google with huge `--max-results` values or run this continuously; add delays if you see CAPTCHAs. This is meant as a prospecting aid, not a production data pipeline, and scraping Google Maps may be against its Terms of Service — use responsibly and at reasonable volume.
- **Website checks are heuristic.** `enrich.py` does a lightweight audit (viewport tag, HTTPS, meta description, schema markup) rather than a full Lighthouse-style scan. It's meant to triage hundreds of leads quickly, not replace an actual audit before you pitch.
"# my-lead" 
