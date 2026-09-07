"""
Google Maps business scraper built on Playwright.

Google changes its DOM structure periodically, so the CSS selectors below
are the ones that have worked most consistently as of 2026. If a run
suddenly returns 0 results, the first thing to check is whether Google
has renamed one of these classes/attributes -- open the page with
headless=False and inspect it.

Usage:
    from gmaps_scraper import GoogleMapsScraper
    scraper = GoogleMapsScraper(headless=True)
    results = scraper.search("restaurants in Lucknow", max_results=40)
    scraper.close()
"""

import time
import re
from playwright.sync_api import sync_playwright


class GoogleMapsScraper:
    def __init__(self, headless: bool = True, slow_mo: int = 0):
        self._playwright = sync_playwright().start()
        # Container-tested flags for Chromium in Linux (Docker / Streamlit Cloud)
        launch_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-extensions",
            "--no-first-run",
        ]
        try:
            self.browser = self._playwright.chromium.launch(
                headless=headless,
                slow_mo=slow_mo,
                args=launch_args,
            )
        except Exception:
            import subprocess, sys
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            self.browser = self._playwright.chromium.launch(
                headless=headless,
                slow_mo=slow_mo,
                args=launch_args,
            )
        self.context = self.browser.new_context(
            locale="en-US",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 900},
        )
        self.page = self.context.new_page()

    def close(self):
        self.context.close()
        self.browser.close()
        self._playwright.stop()

    def search(self, query: str, max_results: int = 40, scroll_pause: float = 1.5):
        """
        Search Google Maps for `query` (e.g. "dentists in Lucknow") and
        return a list of dicts with the fields we care about.
        """
        url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        self.page.goto(url, timeout=60000)
        self.page.wait_for_timeout(3000)

        # The scrollable results panel on the left side of the map
        feed_selector = 'div[role="feed"]'
        try:
            self.page.wait_for_selector(feed_selector, timeout=15000)
        except Exception:
            # No results feed found at all (query too narrow, or blocked)
            return []

        collected_links = set()
        stagnant_rounds = 0
        max_stagnant_rounds = 4

        while len(collected_links) < max_results and stagnant_rounds < max_stagnant_rounds:
            cards = self.page.query_selector_all(f'{feed_selector} a[href*="/maps/place/"]')
            before = len(collected_links)
            for c in cards:
                href = c.get_attribute("href")
                if href:
                    collected_links.add(href)
                if len(collected_links) >= max_results:
                    break

            if len(collected_links) == before:
                stagnant_rounds += 1
            else:
                stagnant_rounds = 0

            self.page.evaluate(
                f"""() => {{
                    const feed = document.querySelector('{feed_selector}');
                    if (feed) feed.scrollTop = feed.scrollHeight;
                }}"""
            )
            self.page.wait_for_timeout(int(scroll_pause * 1000))

        results = []
        for link in list(collected_links)[:max_results]:
            data = self._scrape_place(link)
            if data:
                results.append(data)

        return results

    def _scrape_place(self, place_url: str):
        try:
            self.page.goto(place_url, timeout=30000)
            self.page.wait_for_timeout(1500)

            name = self._safe_text('h1')
            if not name:
                return None

            category = self._safe_text('button[jsaction*="category"]')

            address = None
            phone = None
            website = None

            # Google renders each info row as a button with an aria-label
            # like "Address: 123 Main St" / "Phone: +91..." / website link
            info_buttons = self.page.query_selector_all('button[data-item-id], a[data-item-id]')
            for b in info_buttons:
                item_id = b.get_attribute("data-item-id") or ""
                text = (b.get_attribute("aria-label") or b.inner_text() or "").strip()
                if item_id.startswith("address"):
                    address = self._clean_label(text, "Address")
                elif item_id.startswith("phone"):
                    phone = self._clean_label(text, "Phone")
                elif item_id == "authority" or "website" in item_id:
                    website = b.get_attribute("href") or self._clean_label(text, "Website")

            rating, review_count = self._extract_rating()

            return {
                "name": name,
                "category": category,
                "address": address,
                "phone": phone,
                "website": website,
                "rating": rating,
                "review_count": review_count,
                "maps_url": place_url,
            }
        except Exception as e:
            print(f"  [warn] failed to scrape {place_url}: {e}")
            return None

    def _safe_text(self, selector):
        el = self.page.query_selector(selector)
        if el:
            return el.inner_text().strip()
        return None

    def _clean_label(self, text, prefix):
        if not text:
            return None
        return re.sub(rf"^{prefix}:?\s*", "", text, flags=re.IGNORECASE).strip()

    def _extract_rating(self):
        rating_el = self.page.query_selector('div.F7nice span[aria-hidden="true"]')
        rating = None
        if rating_el:
            try:
                rating = float(rating_el.inner_text().strip())
            except ValueError:
                rating = None

        review_count = None
        review_el = self.page.query_selector('div.F7nice span[aria-label*="review"]')
        if review_el:
            match = re.search(r"[\d,]+", review_el.inner_text())
            if match:
                review_count = int(match.group().replace(",", ""))

        return rating, review_count
