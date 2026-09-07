"""
Central config for the lead scraper.
Tweak SEGMENT_RULES to match how Devtacet actually wants to prioritize leads.
"""

# Categories that usually run manual bookings/orders and are good Android app targets
APP_FRIENDLY_CATEGORIES = [
    "restaurant", "cafe", "coffee shop", "bakery", "salon", "spa",
    "gym", "fitness", "clinic", "dentist", "diagnostic", "pharmacy",
    "grocery", "supermarket", "tuition", "coaching", "hotel", "hostel",
]

# Categories that often need custom internal tools (inventory, records, scheduling)
SYSTEM_SOFTWARE_CATEGORIES = [
    "clinic", "hospital", "pharmacy", "distributor", "wholesaler",
    "manufacturer", "warehouse", "logistics", "school", "college",
    "diagnostic", "laboratory", "real estate", "dealer",
]

# Point values -- tune these once you see how they distribute on real data
SCORING = {
    "no_website": 40,
    "website_not_mobile_friendly": 25,
    "website_no_https": 10,
    "website_no_meta_description": 10,
    "no_schema_markup": 15,
    "app_friendly_category_no_ordering_keywords": 20,
    "system_software_category": 15,
    "low_review_count_established": 10,  # business is old/known but has <10 reviews -> weak online presence
}

# Keywords on a business's own website that suggest they already handle online
# ordering/booking -- if these ARE found, we do NOT award the app-opportunity points
ONLINE_ORDERING_KEYWORDS = [
    "order online", "book now", "book appointment", "add to cart",
    "download our app", "app store", "play store", "reserve a table",
]

REQUEST_TIMEOUT_SECONDS = 10
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
