"""
Configuration & Constants for Phong Vu Inventory Intelligence.
Extracted from phongvu.vn client-side environment & Next.js runtime.
"""

# Base URLs
PHONGVU_BASE_URL = "https://phongvu.vn"
TEKO_DISCOVERY_URL = "https://discovery.tekoapis.com/api/v1"
TEKO_DISCOVERY_V2_URL = "https://discovery.tekoapis.com/api/v2"
TEKO_LISTING_URL = "https://listing.tekoapis.com/api/"
TEKO_SEARCH_URL = "https://search.tekoapis.com/api"
TEKO_PPM_URL = "https://ppm.tekoapis.com/api/"
TEKO_LOCATION_URL = "https://location.tekoapis.com/api/v1"
TEKO_CART_URL = "https://carts-consumer.tekoapis.com/"
TEKO_CONSUMER_BFF_URL = "https://consumer-bff.tekoapis.com/"

# Authentication / Client Tokens (Publicly exposed in client bundle)
SEARCH_API_ACCESS_TOKEN = "QUEYCPKVSKIDYGUCWPVBSCEWSCEZ6A"
LOYALTY_CLIENT_ID = "490459935105093632"
TRACKER_APP_ID = "55e8a572-14a1-4fc5-adf9-112692c593c8"

# Next.js Build ID (Current runtime - update if 404 on _next/data)
CURRENT_BUILD_ID = "ho0A4eRsdUQzuDNcy_KDm"

# Standard HTTP Headers
HEADERS_COMMON = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Origin": "https://phongvu.vn",
    "Referer": "https://phongvu.vn/",
}
