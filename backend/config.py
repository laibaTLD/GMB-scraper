import os

# Scraper Settings
TARGET_COUNT = 1000
MIN_DELAY = 2
MAX_DELAY = 5
SCROLL_PAUSE_TIME = 2
MAX_RETRIES = 3

# User Agents for Rotation
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0 Safari/537.36'
]

# Chrome Options
HEADLESS_MODE = False  # Set to True for hidden scraping, False to see existing browser
# Note: Google Maps often detects headless mode easily. Keeping it visible is often safer for complex interactions.

# Output Directory
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
os.makedirs(OUTPUT_DIR, exist_ok=True)
