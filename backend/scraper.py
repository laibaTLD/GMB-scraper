import os
import re
import json
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import unquote, quote_plus

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from config import *
from extractor import parse_business_data, enrich_from_website


def build_maps_search_url(query, location=None):
    """Build a Google Maps search URL from form values (avoids geolocation default)."""
    query = (query or "").strip()
    location = (location or "").strip()
    search_term = f"{query} in {location}" if location else query
    return f"https://www.google.com/maps/search/{quote_plus(search_term)}"


def normalize_place_key(url):
    """Normalize Google Maps place URL for deduplication."""
    if not url:
        return url
    chij = re.search(r'(ChIJ[a-zA-Z0-9_-]+)', url)
    if chij:
        return chij.group(1)
    match = re.search(r'/maps/place/([^/@?]+)', url)
    if match:
        return unquote(match.group(1)).lower().replace('+', ' ')
    return url.split('?')[0]


def normalize_business_name(name):
    if not name or name == "N/A":
        return ""
    return re.sub(r'\s+', ' ', name.strip().lower())


def create_chrome_driver(allow_geolocation=False):
    options = webdriver.ChromeOptions()
    if HEADLESS_MODE:
        options.add_argument("--headless")
    options.page_load_strategy = 'eager'
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    if not allow_geolocation:
        options.add_experimental_option("prefs", {
            "profile.default_content_setting_values.geolocation": 2,
        })
    options.add_argument("--remote-allow-origins=*")
    options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver


def collect_place_urls_from_page(driver):
    """Collect all visible place URLs in one JS pass."""
    try:
        urls = driver.execute_script("""
            const links = document.querySelectorAll('a[href*="/maps/place/"]');
            return [...new Set([...links].map(a => a.href).filter(Boolean))];
        """)
        return urls or []
    except Exception:
        return []


def scroll_results_feed(driver):
    """Scroll the Maps results feed once."""
    driver.execute_script("""
        const feed = document.querySelector('div[role="feed"]');
        if (feed) {
            feed.scrollTop = feed.scrollHeight;
        } else {
            window.scrollTo(0, document.body.scrollHeight);
        }
    """)


def wait_for_new_urls(driver, previous_count, timeout=SCROLL_PAUSE_TIME + 2):
    """Wait until new place links appear or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if len(collect_place_urls_from_page(driver)) > previous_count:
            return True
        time.sleep(0.15)
    return False


def is_end_of_results(page_source):
    end_indicators = [
        "You've reached the end of the list",
        "You've reached the end",
        "No more results",
        "End of results",
    ]
    return any(indicator in page_source for indicator in end_indicators)


def extract_place_data(url, user_agent, stop_event, scraping_mode='detailed'):
    """Worker: extract one business profile in its own browser session."""
    if stop_event.is_set():
        return None

    simple_mode = scraping_mode == 'simple'
    driver = None
    try:
        driver = create_chrome_driver(allow_geolocation=False)
        driver.get(url)

        wait = WebDriverWait(driver, PLACE_WAIT_TIMEOUT)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        wait.until(lambda d: (
            d.find_elements(By.CSS_SELECTOR, 'button[data-item-id*="phone"]')
            or d.find_elements(By.CSS_SELECTOR, 'button[data-item-id="address"]')
            or d.find_elements(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
            or d.find_element(By.TAG_NAME, "h1")
        ))

        if not simple_mode and MIN_DELAY > 0:
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        data = parse_business_data(driver.page_source, url, maps_only=simple_mode)
        if data.get('name') == "N/A":
            return None

        if not simple_mode:
            data = enrich_from_website(data, user_agent, WEBSITE_FETCH_TIMEOUT)
        return data
    except Exception as e:
        print(f"Extraction error for {url}: {e}")
        return None
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass


class MapsScraper:
    def __init__(self):
        self.driver = None
        self.is_scraping = False
        self.results = []
        self.scraped_count = 0
        self.target_count = 0
        self.status_message = "Idle"
        self.stop_event = threading.Event()
        self._results_lock = threading.Lock()
        self.processed_keys = set()
        self.scraped_names = set()
        self.scraping_mode = 'detailed'

    def setup_driver(self, allow_geolocation=False):
        self.driver = create_chrome_driver(allow_geolocation=allow_geolocation)

    def start_scraping(self, query, location, limit=TARGET_COUNT, scraping_mode='detailed'):
        if self.is_scraping:
            if hasattr(self, '_scrape_thread') and not self._scrape_thread.is_alive():
                self.is_scraping = False
                self.status_message = "Idle"
            else:
                return False, "Scraping already in progress"

        if scraping_mode not in ('simple', 'detailed'):
            scraping_mode = 'detailed'

        self.stop_event.clear()
        self.is_scraping = True
        self.results = []
        self.scraped_count = 0
        self.target_count = limit
        self.processed_keys = set()
        self.scraped_names = set()
        self.scraping_mode = scraping_mode
        mode_label = 'Simple' if scraping_mode == 'simple' else 'Detailed'
        self.status_message = f"Starting ({mode_label} mode)..."

        self._scrape_thread = threading.Thread(target=self._scrape_logic, args=(query, location))
        self._scrape_thread.start()
        return True, "Scraping started"

    def stop_scraping(self):
        self.stop_event.set()
        self.status_message = "Stopping..."

    def _scrape_logic(self, query, location):
        try:
            self._run_scrape_loop(query, location)
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None
            self.is_scraping = False

    def _load_recovery(self, query, location):
        safe_filename = f"recovery_{query}_{location}".replace(" ", "_").replace("/", "").replace("\\", "")
        self.recovery_path = os.path.join(OUTPUT_DIR, f"{safe_filename}.json")

        if not os.path.exists(self.recovery_path):
            return

        try:
            with open(self.recovery_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if data.get('query') != query or data.get('location') != location:
                return

            self.results = data.get('results', [])
            self.scraped_count = len(self.results)
            for item in self.results:
                if item.get('files_url'):
                    self.processed_keys.add(normalize_place_key(item['files_url']))
                name_key = normalize_business_name(item.get('name'))
                if name_key:
                    self.scraped_names.add(name_key)
            self.status_message = f"Resumed from recovery: {self.scraped_count} items loaded."
        except Exception as e:
            print(f"Failed to load recovery file: {e}")

    def _save_recovery(self, query, location):
        try:
            with open(self.recovery_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'query': query,
                    'location': location,
                    'scraped_count': self.scraped_count,
                    'results': self.results,
                }, f, indent=2)
        except Exception as e:
            print(f"Recovery save error: {e}")

    def _try_add_result(self, data, query, location):
        with self._results_lock:
            if self.scraped_count >= self.target_count:
                return False
            name_key = normalize_business_name(data.get('name'))
            if name_key and name_key in self.scraped_names:
                return False

            self.results.append(data)
            self.scraped_count += 1
            place_key = normalize_place_key(data.get('files_url', ''))
            if place_key:
                self.processed_keys.add(place_key)
            if name_key:
                self.scraped_names.add(name_key)

            if self.scraped_count % RECOVERY_SAVE_INTERVAL == 0:
                self._save_recovery(query, location)
            return True

    def _open_search_results(self, query, location):
        search_query = f"{query} in {location}" if location else query
        search_url = build_maps_search_url(query, location)
        self.status_message = f"Searching: {search_query}..."

        self.driver.get(search_url)
        wait = WebDriverWait(self.driver, 25)
        wait.until(EC.presence_of_element_located((
            By.CSS_SELECTOR,
            'div[role="feed"], a[href*="/maps/place/"], div[role="main"]'
        )))
        self.status_message = f"Loaded results for: {search_query}"

    def _collect_urls(self, target_remaining):
        """Scroll and collect unique place URLs until enough or end of list."""
        collected = []
        seen_keys = set(self.processed_keys)
        consecutive_empty = 0

        while len(collected) < target_remaining and not self.stop_event.is_set():
            urls = collect_place_urls_from_page(self.driver)
            previous_total = len(urls)

            for url in urls:
                place_key = normalize_place_key(url)
                if place_key in seen_keys:
                    continue
                seen_keys.add(place_key)
                collected.append(url)
                if len(collected) >= target_remaining:
                    break

            if len(collected) >= target_remaining:
                break

            if is_end_of_results(self.driver.page_source):
                self.status_message = "End of list reached."
                break

            consecutive_empty += 1
            self.status_message = (
                f"Scrolling... ({consecutive_empty}/{MAX_SCROLL_RETRIES}) - "
                f"Queued {len(collected)}/{target_remaining}"
            )

            scroll_results_feed(self.driver)
            got_new = wait_for_new_urls(self.driver, previous_total)

            if got_new:
                consecutive_empty = 0
            elif consecutive_empty >= MAX_SCROLL_RETRIES:
                self.status_message = (
                    f"No new items found. Collected {len(collected)} URLs."
                )
                break

        return collected

    def _process_urls_parallel(self, urls, query, location):
        """Extract businesses concurrently."""
        if not urls or self.stop_event.is_set():
            return

        with self._results_lock:
            for url in urls:
                self.processed_keys.add(normalize_place_key(url))

        workers = min(CONCURRENT_WORKERS, len(urls))
        user_agent = random.choice(USER_AGENTS)
        completed = 0

        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {
                executor.submit(
                    extract_place_data, url, user_agent, self.stop_event, self.scraping_mode
                ): url
                for url in urls
            }

            for future in as_completed(futures):
                if self.stop_event.is_set():
                    break

                url = futures[future]

                try:
                    data = future.result()
                except Exception as e:
                    print(f"Worker failed for {url}: {e}")
                    data = None

                if not data:
                    continue

                if not self._try_add_result(data, query, location):
                    continue

                completed += 1
                self.status_message = (
                    f"Extracting [{self.scraped_count}/{self.target_count}] "
                    f"({completed}/{len(urls)} in batch)..."
                )

    def _run_scrape_loop(self, query, location):
        query = (query or "").strip()
        location = (location or "").strip()

        self._load_recovery(query, location)

        while self.scraped_count < self.target_count and not self.stop_event.is_set():
            if self.driver is None:
                try:
                    self.setup_driver(allow_geolocation=not location)
                    self._open_search_results(query, location)
                except Exception as e:
                    self.status_message = f"Driver setup failed: {e}"
                    time.sleep(3)
                    continue

            try:
                remaining = self.target_count - self.scraped_count
                batch_urls = self._collect_urls(remaining)

                if not batch_urls:
                    break

                self.status_message = f"Processing {len(batch_urls)} businesses in parallel..."
                self._process_urls_parallel(batch_urls, query, location)

                if self.scraped_count >= self.target_count:
                    break

                if is_end_of_results(self.driver.page_source):
                    break

            except Exception as e:
                print(f"Scrape loop critical error: {e}")
                if self.driver:
                    try:
                        self.driver.quit()
                    except Exception:
                        pass
                self.driver = None
                time.sleep(3)

        if os.path.exists(self.recovery_path):
            try:
                os.remove(self.recovery_path)
            except Exception:
                pass

        if self.results:
            if self.stop_event.is_set():
                self.status_message = (
                    f"Stopped at {self.scraped_count}/{self.target_count}. Ready to download."
                )
            else:
                self.status_message = "Complete! Click Download to save your file."
        elif self.stop_event.is_set():
            self.status_message = f"Stopped at {self.scraped_count}/{self.target_count}."
        else:
            self.status_message = "No results found for this search."

    def get_progress(self):
        return {
            "count": self.scraped_count,
            "target": self.target_count,
            "status": self.status_message,
            "is_active": self.is_scraping,
            "download_ready": not self.is_scraping and len(self.results) > 0,
        }


scraper_instance = MapsScraper()
