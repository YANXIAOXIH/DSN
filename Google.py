from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException, NoSuchElementException
from deep_translator import GoogleTranslator
from selenium_stealth import stealth
import re
import os
import time
import traceback

# --- Function to save debugging information ---
# Call this function after critical steps or when errors occur to save
# the current browser screenshot and page source for easier debugging.
def save_debug_info(driver, prefix="error"):
    try:
        screenshot_path = f"{prefix}_screenshot.png"
        page_source_path = f"{prefix}_page_source.html"
        current_url = "N/A"
        try: current_url = driver.current_url
        except Exception: pass # Driver might be invalid at this point
        print(f"Saving debug info: URL: {current_url} (prefix: {prefix})")
        driver.save_screenshot(screenshot_path)
        print(f"Debug screenshot saved as: {screenshot_path}")
        with open(page_source_path, "w", encoding="utf-8") as f: f.write(driver.page_source)
        print(f"Debug page source saved as: {page_source_path}")
        
        # If running in a GitHub Actions environment, write debug file paths to GITHUB_ENV
        # This allows them to be easily uploaded as artifacts.
        env_file = os.getenv('GITHUB_ENV')
        if env_file:
            with open(env_file, "a") as f:
                if os.path.exists(screenshot_path): f.write(f"DEBUG_SCREENSHOT_{prefix.upper()}={screenshot_path}\n")
                if os.path.exists(page_source_path): f.write(f"DEBUG_PAGESOURCE_{prefix.upper()}={page_source_path}\n")
    except Exception as e_save: print(f"Could not save debug info: {e_save}")

# --- Robust element clicking function ---
# Attempts to click an element using multiple methods to improve success rate,
# including JavaScript click and standard click.
def click_element_robustly(driver, by, value, timeout=10):
    try:
        # Wait until the element is clickable
        element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
        element_text = "N/A"
        try: # Try to get element text or HTML snippet for logging purposes
            element_text = element.text[:50] if element.text else element.get_attribute('outerHTML')[:70]
        except: pass
        print(f"Element ({by}='{value}') found. Text/HTML: '{element_text}...'. Attempting click.")
        
        # Prefer JavaScript click first, as it can sometimes bypass overlays or issues with standard click
        try: 
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element) # Scroll element to center
            time.sleep(0.3) # Brief pause for scrolling to complete
            driver.execute_script("arguments[0].click();", element)
            print(f"Clicked element ({by}='{value}') via JS click successfully.")
            return True
        except Exception as e_js:
            print(f"JS click failed for ({by}='{value}'): {e_js}. Trying standard click.")
            # If JS click fails, attempt a standard click
            try:
                element.click()
                print(f"Clicked element ({by}='{value}') via standard click successfully.")
                return True
            except Exception as e_std:
                print(f"Standard click also failed for ({by}='{value}'): {e_std}")
                return False
    except TimeoutException: print(f"Element ({by}='{value}') not found/clickable within {timeout}s.")
    except StaleElementReferenceException: print(f"Element ({by}='{value}') became stale.")
    except Exception as e: print(f"Error clicking ({by}='{value}'): {e}")
    return False

# --- Translation function with caching ---
translation_cache = {} # Cache for translated texts to avoid redundant API calls
try:
    # Initialize Google Translator instance
    translator = GoogleTranslator(source='auto', target='zh-CN') # Auto-detect source, translate to Simplified Chinese
except Exception as e:
    print(f"Error initializing translator: {e}. Translations will be skipped.")
    translator = None

def translate_to_chinese(text):
    global translator, translation_cache
    if not translator or not text: # If translator not initialized or text is empty, return original
        return text

    text = text.strip() # Remove leading/trailing whitespace
    if not text: # If text is empty after stripping, return
        return text
    if text in translation_cache: # If translation exists in cache, return cached result
        return translation_cache[text]
    
    try:
        translated_text = translator.translate(text)
        if translated_text:
            translation_cache[text] = translated_text.strip() # Store translation in cache
            print(f"Translated '{text}' to '{translation_cache[text]}'")
            return translation_cache[text]
        else: # Translation returned empty
            print(f"Warning: Translation returned empty for '{text}'. Using original.")
            translation_cache[text] = text # Cache original as a failed translation marker
            return text
    except Exception as e: # Exception during translation
        print(f"Warning: Translation failed for '{text}': {e}. Using original.")
        translation_cache[text] = text # Cache original as a failed translation marker
        return text
# --- End of translation function ---

# --- Main function to extract IP and Country ---
def extract_ip_country_dynamic(url, pattern, output_file="Google.txt"): 
    print("Setting up Chrome options...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") # Use the new headless mode
    chrome_options.add_argument("--no-sandbox") # Often required in Docker or Linux CI environments
    chrome_options.add_argument("--disable-dev-shm-usage") # Overcomes limited resource problems in Docker
    chrome_options.add_argument("--disable-gpu") # Generally recommended for headless mode
    chrome_options.add_argument("--window-size=1920,1080") # Set window size; some sites need it for responsive layout
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36") # Set User-Agent
    chrome_options.add_argument('--disable-blink-features=AutomationControlled') # Disable WebDriver automation detection features
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) # Exclude automation-related switches
    chrome_options.add_experimental_option('useAutomationExtension', False) # Do not use automation extension

    print("Initializing Chrome WebDriver...")
    driver = None
    try:
        # Note: If chromedriver is not in system PATH, specify its path via Service
        # from selenium.webdriver.chrome.service import Service as ChromeService
        # service = ChromeService(executable_path='/path/to/chromedriver')
        # driver = webdriver.Chrome(service=service, options=chrome_options)
        driver = webdriver.Chrome(options=chrome_options)
        
        print("Applying selenium-stealth patches for anti-detection...")
        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True)
        print("Selenium-stealth applied.")
        
        print(f"Navigating to URL: {url}")
        driver.get(url)
        print("Initial page loaded.")
        save_debug_info(driver, "initial_load") # Save page state after initial load

        # --- Attempt to quickly handle Cookie pop-up (if present) ---
        print("Quickly trying to accept cookies if banner exists...")
        cookie_selectors = [ # Define various possible selectors for cookie consent buttons
            (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"), # Standard CookieBot ID
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow all')]"), # Generic "allow all"
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]"), # Generic "accept all"
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]")    # Generic "agree"
        ]
        cookie_clicked = False
        for by_sel, selector in cookie_selectors:
             if click_element_robustly(driver, by_sel, selector, timeout=3): # Short timeout attempt
                  cookie_clicked = True
                  print(f"Potential cookie banner handled by {by_sel}='{selector}'.")
                  time.sleep(1) # Wait for cookie banner to disappear
                  save_debug_info(driver, f"after_cookie_attempt_{by_sel}")
                  break # One successful click is enough
        if not cookie_clicked:
            print("Cookie banner not found quickly or click failed, proceeding.")
            save_debug_info(driver, "no_cookie_click")

        # --- Click the "Google DNS" tab ---
        # Locator for "Google DNS" tab, href attribute added for more precision
        google_dns_tab_locator = (By.XPATH, "//a[normalize-space(.)='Google DNS' and contains(@href, '#google')]")
        print(f"Attempting to click 'Google DNS' tab with locator: {google_dns_tab_locator}...") # 打印新的定位器
        if click_element_robustly(driver, google_dns_tab_locator[0], google_dns_tab_locator[1], timeout=10):
            print("'Google DNS' tab clicked successfully.")
            # Critical step: Wait for tab content to load. If content isn't loaded here,
            # subsequent regex matching will fail.
            # Consider WebDriverWait for specific content instead of fixed time.sleep.
            time.sleep(5) # Wait for tab content to load
            save_debug_info(driver, "after_google_dns_tab_click")
        else:
            print("'Google DNS' tab could not be clicked. Trying to proceed...")
            # If this step fails, subsequent data retrieval might be incorrect.
            # Error handling might need to be more sophisticated.
            save_debug_info(driver, "google_dns_tab_click_failed")

        # --- Wait for DNS records container to appear and render ---
        # Using the ID of the tab content as container locator, generally more stable
        records_container_locator = (By.ID, "google")
        wait_time = 20 # Max time to wait for container to appear
        print(f"Waiting for DNS records container (ID: '{records_container_locator[1]}') to be present (up to {wait_time} seconds)...")
        try:
             WebDriverWait(driver, wait_time).until(EC.visibility_of_element_located(records_container_locator))
             print("DNS records container is visible. Giving JS some time to render content...")
             # Even if container is present, internal data might be loaded asynchronously by JS,
             # so an additional wait is often necessary.
             time.sleep(5) 
             save_debug_info(driver, "dns_container_present_and_waited")
        except TimeoutException:
            print(f"Timeout waiting for DNS records container (ID: '{records_container_locator[1]}').")
            save_debug_info(driver, "timeout_waiting_dns_container")
            # Even on timeout, attempt to get current page source for matching,
            # as some data might have loaded.
       
        # --- Fetch final HTML and extract ---
        print("Fetching final page source for regex matching...")
        html_content = driver.page_source
        # Save the final HTML source for local debugging of regex or page structure analysis
        with open("final_page_source_for_regex.html", "w", encoding='utf-8') as f: f.write(html_content)
        print("Saved final page source to final_page_source_for_regex.html")

        # Use the compiled regex pattern to find all matches in the HTML content
        matches = pattern.findall(html_content) # 'pattern' is passed from the main function
        
        if matches: # If matches are found
            print(f"Regex initially found {len(matches)} potential matches.")
            unique_ip_country_pairs = set() # To store unique (IP, Country) pairs

            # Regex is expected to return 3 capture groups: ip, city, country_en_raw_from_regex
            for ip, city, country_en_raw_from_regex in matches: 
                ip_clean = ip.strip() # Clean the IP address string
                country_en_raw = country_en_raw_from_regex.strip() # Raw country identifier from regex
                country_final = "" # Final determined country name (in Chinese)

                # --- Step 1: Prioritize direct mapping for common country codes/names for higher accuracy ---
                # Convert raw country identifier to uppercase for easier comparison
                country_en_upper = country_en_raw.upper() 
                if country_en_upper == "US" or country_en_raw.lower() == "united states":
                    country_final = "美国" # "United States" in Chinese
                elif country_en_upper == "HK" or country_en_raw.lower() == "hong kong":
                    country_final = "香港" # "Hong Kong" in Chinese
                # More direct mappings can be added here, e.g.:
                # elif country_en_upper == "JP" or "JAPAN" in country_en_raw.upper():
                # country_final = "日本" # "Japan" in Chinese
                # elif country_en_upper == "GB" or "UNITED KINGDOM" in country_en_raw.upper():
                # country_final = "英国" # "United Kingdom" in Chinese
                
                # --- Step 2: If country not determined by direct mapping and raw identifier is not empty, try translation ---
                if not country_final and country_en_raw:
                    translated_cn = translate_to_chinese(country_en_raw)
                    # If translation is valid (non-empty and different from original,
                    # to avoid cases where translation service returns original for Chinese text)
                    if translated_cn and translated_cn != country_en_raw:
                        country_final = translated_cn
                    else: # Translation failed, returned original, or was empty; fallback to original English name
                        country_final = country_en_raw 

                # --- Step 3: Apply specific string fixes to the determined country_final ---
                if country_final:
                    country_final = country_final.strip() # Ensure final country name is clean
                    original_country_for_log = country_final # For logging pre-fix name
                    # Specific country name correction rules
                    if country_final == "韩国，共和国": # "Korea, Republic of"
                        country_final = "韩国" # "Korea"
                        print(f"Applying string fix: changing '{original_country_for_log}' to '{country_final}'")
                    elif country_final == "英国英国和北爱尔兰": # "United KingdomGreat Britain and Northern Ireland"
                        country_final = "英国" # "United Kingdom"
                        print(f"Applying string fix: changing '{original_country_for_log}' to '{country_final}'")
                    # Other correction rules can be added here
                
                # If IP and final country name are valid, add to set (automatic deduplication)
                if ip_clean and country_final:
                    unique_ip_country_pairs.add((ip_clean, country_final)) 
                else: # Log entries that couldn't be processed successfully
                    print(f"Warning: Empty IP or undetermined/empty Final Country. IP:'{ip_clean}', Raw_EN_Country:'{country_en_raw}', Determined_Country:'{country_final}'")
            
            # --- Processing and writing to files ---
            if unique_ip_country_pairs:
                print(f"Found {len(unique_ip_country_pairs)} unique (IP, Final Country) pairs after processing.")

                all_formatted_lines = [] # Stores all formatted lines
                hk_formatted_lines = []  # Stores formatted lines for Hong Kong
                us_formatted_lines = []  # Stores formatted lines for the US

                # Sort by IP address to ensure consistent output order
                sorted_ip_country_pairs = sorted(list(unique_ip_country_pairs), key=lambda x: tuple(map(int, x[0].split('.'))))

                # Iterate through sorted IP-country pairs for formatting and categorization
                for ip_addr, country_name in sorted_ip_country_pairs:
                    line_to_write = f"{ip_addr}#{country_name}.PUG" # Define output format
                    all_formatted_lines.append(line_to_write) # Add to main list

                    # Categorize into specific lists based on country name
                    if country_name == "香港": # "Hong Kong"
                        hk_formatted_lines.append(line_to_write)
                    elif country_name == "美国": # "United States"
                        us_formatted_lines.append(line_to_write)
                
                env_file = os.getenv('GITHUB_ENV') # Get GITHUB_ENV file path

                # Write the main file with all results (Google.txt)
                with open(output_file, "w", encoding="utf-8") as f:
                    for line in all_formatted_lines:
                        f.write(f"{line}\n")
                print(f"All {len(all_formatted_lines)} unique results saved to {output_file}")
                if env_file: # If in GitHub Actions environment
                    with open(env_file, "a") as f_env: f_env.write(f"Google_TXT_FILE={output_file}\n")

                # Write Hong Kong specific file (Google.Hk.txt)
                hk_output_file = "Google.Hk.txt"
                if hk_formatted_lines:
                    with open(hk_output_file, "w", encoding="utf-8") as f:
                        for line in hk_formatted_lines:
                            f.write(f"{line}\n")
                    print(f"Hong Kong specific results ({len(hk_formatted_lines)} lines) saved to {hk_output_file}")
                    if env_file:
                        with open(env_file, "a") as f_env: f_env.write(f"Google_HK_TXT_FILE={hk_output_file}\n")
                else:
                    print(f"No Hong Kong specific results found, {hk_output_file} not created.")

                # Write US specific file (Google.US.txt)
                us_output_file = "Google.US.txt"
                if us_formatted_lines:
                    with open(us_output_file, "w", encoding="utf-8") as f:
                        for line in us_formatted_lines:
                            f.write(f"{line}\n")
                    print(f"US specific results ({len(us_formatted_lines)} lines) saved to {us_output_file}")
                    if env_file:
                        with open(env_file, "a") as f_env: f_env.write(f"Google_US_TXT_FILE={us_output_file}\n")
                else:
                    print(f"No US specific results found, {us_output_file} not created.")
            
            else: # If unique_ip_country_pairs is empty
                 print("No valid unique (IP, Final Country) pairs found after cleaning and translation.")
                 save_debug_info(driver, "no_valid_unique_ip_country_pairs")
        else: # If regex found no matches
            print("No matches found by regex in the final page source.")
            save_debug_info(driver, "final_page_no_regex_match") # This debug info is very important

        return matches if matches else None # Return original match list or None

    except Exception as e: # Catch other unhandled exceptions in Selenium operation
        print(f"An unhandled error occurred in Selenium operation: {e}")
        traceback.print_exc() # Print full error stack trace
        if driver: save_debug_info(driver, "unhandled_exception")
        return None
    finally: # Always try to quit WebDriver, regardless of success or failure
        if driver:
            print("Quitting WebDriver.")
            driver.quit()

# --- Main execution block ---
if __name__ == "__main__":
    url = "https://www.nslookup.io/domains/bpb.yousef.isegaro.com/dns-records/" # Target URL
    
    # Regular expression to extract information from the Google DNS A records section of nslookup.io
    # Designed to capture:
    # 1. IP Address (IPv4)
    # 2. City Name (Regex capture group 2)
    # 3. Raw Country Identifier (Country_EN) - Regex capture group 3 (usually country code or full English name)
    # This regex is highly dependent on the HTML structure; updates may be needed if the site changes.
    pattern = re.compile(
        # Capture Group 1: IP Address (e.g., "8.8.8.8")
        # Looks for IP address after a span with class "...bg-green-400..." (typically a status indicator)
        r'<span class="mr-1.5 h-2 w-2 rounded-full bg-green-400"[^>]*></span>\s*([\d.]+)\s*</div>'
        
        # Non-greedy match, skips HTML content between IP and location info block
        # This part relies on IP and location info being relatively ordered and close in HTML
        r'.*?' 
        
        # Start of location info block (typically a tooltip-style div)
        r'<div class="bg-slate-900 text-white[^"]*whitespace-nowrap"[^>]*>\s*'
        # Capture Group 2: City Name (content before the first comma)
        r'([^,]+?)'                 
        # Optional non-capturing group for middle parts (e.g., state), non-greedy match
        r'(?:\s*,\s*[^,]+?)*?'      
        # Capture Group 3: Raw Country Identifier (content after the last comma, before HTML tag, e.g., "US" or "Japan")
        r'\s*,\s*([^<]+?)'          
        r'\s*</div>', # End of location info block
        re.DOTALL | re.IGNORECASE # DOTALL makes . match newlines, IGNORECASE ignores case
    )

    output_filename = "Google.txt" # Main output filename

    print(f"Fetching and parsing URL: {url}")
    results = extract_ip_country_dynamic(url, pattern, output_file=output_filename)

    # Summary information after script execution
    if results: # 'results' is the raw list of matches returned by regex.findall
        print(f"\n--- Regex initially found {len(results)} matches. Check output files for processed results. ---")
        # Check if files were created and provide a hint
        if os.path.exists(output_filename):
            print(f"Main output file: {output_filename}")
        if os.path.exists("Google.Hk.txt"):
            print(f"Hong Kong output file: Google.Hk.txt")
        if os.path.exists("Google.US.txt"):
            print(f"US output file: Google.US.txt")
    else:
        print(f"\n--- No results found or an error occurred. Check logs, debug screenshots/HTML, and final_page_source_for_regex.html. ---")
