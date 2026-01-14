import time
import random
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from config import *
from extractor import parse_business_data, extract_email_from_website, extract_socials
from excel_handler import save_data_to_excel

class MapsScraper:
    def __init__(self):
        self.driver = None
        self.is_scraping = False
        self.results = []
        self.scraped_count = 0
        self.target_count = 0
        self.status_message = "Idle"
        self.output_file = None
        self.stop_event = threading.Event()

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        if HEADLESS_MODE:
            options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        # Anti-detection
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--remote-allow-origins=*")
        
        # User Agent (random)
        user_agent = random.choice(USER_AGENTS)
        options.add_argument(f'user-agent={user_agent}')

        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # Patch navigator.webdriver
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def start_scraping(self, query, location, limit=TARGET_COUNT):
        if self.is_scraping:
            return False, "Scraping already in progress"
        
        self.stop_event.clear()
        self.is_scraping = True
        self.results = []
        self.scraped_count = 0
        self.target_count = limit
        self.status_message = "Starting..."
        
        thread = threading.Thread(target=self._scrape_logic, args=(query, location))
        thread.start()
        return True, "Scraping started"

    def stop_scraping(self):
        self.stop_event.set()
        self.is_scraping = False
        self.status_message = "Stopping..."

    def _scrape_logic(self, query, location):
        import json
        
        # Recovery System Setup
        safe_filename = f"recovery_{query}_{location}".replace(" ", "_").replace("/", "").replace("\\", "")
        self.recovery_path = os.path.join(OUTPUT_DIR, f"{safe_filename}.json")
        
        # Load previous progress if available
        if os.path.exists(self.recovery_path):
            try:
                with open(self.recovery_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Verify it matches current intent
                    if data.get('query') == query and data.get('location') == location:
                        self.results = data.get('results', [])
                        self.scraped_count = len(self.results)
                        # Rebuild processed_urls set from results to ensure consistency
                        self.processed_urls = set(item['files_url'] for item in self.results if 'files_url' in item)
                        self.status_message = f"Resumed from recovery: {self.scraped_count} items loaded."
            except Exception as e:
                print(f"Failed to load recovery file: {e}")
                self.processed_urls = set()
        else:
            self.processed_urls = set()

        consecutive_scrolls_without_new = 0
        MAX_SCROLL_RETRIES = 20  # How many scrolls to try before giving up if no new items appear
        
        while self.scraped_count < self.target_count and not self.stop_event.is_set():
            
            # --- PHASE 1: Driver Lifecycle Management ---
            if self.driver is None:
                try:
                    self.setup_driver()
                    search_query = f"{query} in {location}"
                    self.status_message = f"Searching: {search_query}..."
                    
                    self.driver.get("https://www.google.com/maps")
                    wait = WebDriverWait(self.driver, 20)
                    search_box = wait.until(EC.presence_of_element_located((By.ID, "searchboxinput")))
                    search_box.clear()
                    search_box.send_keys(search_query)
                    search_box.send_keys(Keys.ENTER)
                    
                    # Wait for initial load
                    time.sleep(5)
                    
                    # Attempt to restore scroll position by just scrolling quickly
                    # If we have scraped 100 items, we likely need to scroll a bit to get back 
                    # to where we were, or just let the natural loop handle skipping.
                    self.status_message = "Restoring list position..."
                    
                except Exception as e:
                    self.status_message = f"Driver setup failed: {e}"
                    time.sleep(5)
                    continue

            # --- PHASE 2: Collection & Extraction ---
            try:
                # Find visible links
                links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/maps/place/"]')
                
                # Identify NEW links only
                batch_new_urls = []
                for link in links:
                    url = link.get_attribute('href')
                    if url and url not in self.processed_urls:
                        batch_new_urls.append(url)
                
                if batch_new_urls:
                    consecutive_scrolls_without_new = 0 # Reset counter
                    
                    # Process this batch
                    for url in batch_new_urls:
                        if self.stop_event.is_set(): break
                        
                        # Extraction
                        try:
                            self.status_message = f"Extracting [{self.scraped_count + 1}/{self.target_count}]: ..."
                            
                            self.driver.execute_script("window.open('');")
                            self.driver.switch_to.window(self.driver.window_handles[-1])
                            self.driver.get(url)
                            
                            # Wait depending on network
                            WebDriverWait(self.driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
                            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY)) 
                            
                            html = self.driver.page_source
                            data = parse_business_data(html, url)
                            
                            # Extract email/socials from website if available
                            should_visit_website = False
                            if data.get('website') != "N/A":
                                if data.get('email') == "N/A":
                                    should_visit_website = True
                                else:
                                    social_keys = ['facebook', 'instagram', 'twitter', 'linkedin', 'youtube', 'tiktok']
                                    if any(data.get(k) == "N/A" for k in social_keys):
                                        should_visit_website = True

                            if should_visit_website:
                                try:
                                    self.status_message = f"Extracting data from website..."
                                    self.driver.execute_script("window.open('');")
                                    self.driver.switch_to.window(self.driver.window_handles[-1])
                                    self.driver.get(data['website'])
                                    
                                    # Wait for page to load
                                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                                    time.sleep(2)
                                    
                                    website_html = self.driver.page_source
                                    from bs4 import BeautifulSoup
                                    soup = BeautifulSoup(website_html, 'html.parser')

                                    if data.get('email') == "N/A":
                                        website_email = extract_email_from_website(soup)
                                        if website_email:
                                            data['email'] = website_email

                                    website_socials = extract_socials(soup)
                                    for key, value in website_socials.items():
                                        if data.get(key) == "N/A" and value:
                                            data[key] = value
                                    
                                    self.driver.close()
                                    self.driver.switch_to.window(self.driver.window_handles[-1])
                                except Exception as e:
                                    print(f"Website extraction error: {e}")
                                    if len(self.driver.window_handles) > 2:
                                        self.driver.close()
                                        self.driver.switch_to.window(self.driver.window_handles[-1])
                            
                            if data['name'] != "N/A":
                                self.results.append(data)
                                self.processed_urls.add(url) # Mark as done
                                self.scraped_count += 1
                                
                                # --- Auto-Save Progress ---
                                with open(self.recovery_path, 'w', encoding='utf-8') as f:
                                    json.dump({
                                        'query': query,
                                        'location': location,
                                        'scraped_count': self.scraped_count,
                                        'results': self.results
                                    }, f, indent=2)
                            
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                            
                        except Exception as e:
                            print(f"Extraction error: {e}")
                            if len(self.driver.window_handles) > 1:
                                self.driver.close()
                                self.driver.switch_to.window(self.driver.window_handles[0])
                        
                        if self.scraped_count >= self.target_count:
                            break
                        
                else:
                    # No new URLs found in this view, SCROLL DOWN
                    consecutive_scrolls_without_new += 1
                    self.status_message = f"Scrolling... ({consecutive_scrolls_without_new}/{MAX_SCROLL_RETRIES})"
                    
                    try:
                        # Feed is often role='feed'
                        feed_div = self.driver.find_element(By.CSS_SELECTOR, "div[role='feed']")
                        self.driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", feed_div)
                    except:
                        # Fallback: try raw body scroll or key presses if div not found
                        try:
                             actions = webdriver.ActionChains(self.driver)
                             actions.send_keys(Keys.PAGE_DOWN).perform()
                        except:
                            pass

                    # End of list check
                    if "You've reached the end of the list" in self.driver.page_source:
                         self.status_message = "End of list reached."
                         break
                         
                    if consecutive_scrolls_without_new >= MAX_SCROLL_RETRIES:
                        self.status_message = "No new items found for too long. Stopping."
                        break
                        
                    time.sleep(SCROLL_PAUSE_TIME)
            
            except Exception as e:
                # If main loop crashes (e.g. browser closed manually), try to recover
                print(f"Scrape loop critical error: {e}")
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                self.driver = None # Force restart in next iteration
                time.sleep(5)

        # Final Export
        if self.results:
            self.status_message = "Exporting final data..."
            self.output_file = save_data_to_excel(self.results, OUTPUT_DIR)
            
            # Cleanup recovery file
            if os.path.exists(self.recovery_path):
                try:
                    os.remove(self.recovery_path)
                except:
                   pass
            
            self.status_message = "Complete!"
    
    def get_progress(self):
        return {
            "count": self.scraped_count,
            "target": self.target_count,
            "status": self.status_message,
            "is_active": self.is_scraping,
            "download_ready": self.output_file is not None
        }

    def get_download_path(self):
        return self.output_file

# Singleton or Global Instance
scraper_instance = MapsScraper()
