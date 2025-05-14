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
def save_debug_info(driver, prefix="error"):
    try:
        screenshot_path = f"{prefix}_screenshot.png"
        page_source_path = f"{prefix}_page_source.html"
        current_url = "N/A"
        try: current_url = driver.current_url
        except Exception: pass 
        print(f"Saving debug info: URL: {current_url} (prefix: {prefix})")
        driver.save_screenshot(screenshot_path)
        print(f"Debug screenshot saved as: {screenshot_path}")
        with open(page_source_path, "w", encoding="utf-8") as f: f.write(driver.page_source)
        print(f"Debug page source saved as: {page_source_path}")
        
        env_file = os.getenv('GITHUB_ENV')
        if env_file:
            with open(env_file, "a") as f:
                if os.path.exists(screenshot_path): f.write(f"DEBUG_SCREENSHOT_{prefix.upper()}={screenshot_path}\n")
                if os.path.exists(page_source_path): f.write(f"DEBUG_PAGESOURCE_{prefix.upper()}={page_source_path}\n")
    except Exception as e_save: print(f"Could not save debug info: {e_save}")

# --- Robust element clicking function ---
def click_element_robustly(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((by, value)))
        element_text = "N/A"
        try: 
            element_text = element.text[:50] if element.text else element.get_attribute('outerHTML')[:70]
        except: pass
        print(f"Element ({by}='{value}') found. Text/HTML: '{element_text}...'. Attempting click.")
        
        try: 
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.3) 
            driver.execute_script("arguments[0].click();", element)
            print(f"Clicked element ({by}='{value}') via JS click successfully.")
            return True
        except Exception as e_js:
            print(f"JS click failed for ({by}='{value}'): {e_js}. Trying standard click.")
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
translation_cache = {} 
try:
    translator = GoogleTranslator(source='auto', target='zh-CN') 
except Exception as e:
    print(f"Error initializing translator: {e}. Translations will be skipped.")
    translator = None

def translate_to_chinese(text):
    global translator, translation_cache
    if not translator or not text: 
        return text

    text = text.strip() 
    if not text: 
        return text
    if text in translation_cache: 
        return translation_cache[text]
    
    try:
        translated_text = translator.translate(text)
        if translated_text:
            translation_cache[text] = translated_text.strip() 
            print(f"Translated '{text}' to '{translation_cache[text]}'")
            return translation_cache[text]
        else: 
            print(f"Warning: Translation returned empty for '{text}'. Using original.")
            translation_cache[text] = text 
            return text
    except Exception as e: 
        print(f"Warning: Translation failed for '{text}': {e}. Using original.")
        translation_cache[text] = text 
        return text
# --- End of translation function ---

# --- Main function to extract IP and Country ---
def extract_ip_country_dynamic(url, pattern, output_file="Google.txt"): 
    print("Setting up Chrome options...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu") 
    chrome_options.add_argument("--window-size=1920,1080") 
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36") 
    chrome_options.add_argument('--disable-blink-features=AutomationControlled') 
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
    chrome_options.add_experimental_option('useAutomationExtension', False) 

    print("Initializing Chrome WebDriver...")
    driver = None
    try:
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
        save_debug_info(driver, "initial_load") 

        print("Quickly trying to accept cookies if banner exists...")
        cookie_selectors = [ 
            (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"), 
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow all')]"), 
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]"), 
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]")    
        ]
        cookie_clicked = False
        for by_sel, selector in cookie_selectors:
             if click_element_robustly(driver, by_sel, selector, timeout=3): 
                  cookie_clicked = True
                  print(f"Potential cookie banner handled by {by_sel}='{selector}'.")
                  time.sleep(1) 
                  save_debug_info(driver, f"after_cookie_attempt_{by_sel}")
                  break 
        if not cookie_clicked:
            print("Cookie banner not found quickly or click failed, proceeding.")
            save_debug_info(driver, "no_cookie_click")

        # --- Click the "Google DNS" tab ---
        google_dns_tab_locator = (By.XPATH, "//a[normalize-space(.)='Google DNS' and contains(@href, '#google')]")
        print(f"Attempting to click 'Google DNS' tab with locator: {google_dns_tab_locator}...")
        if click_element_robustly(driver, google_dns_tab_locator[0], google_dns_tab_locator[1], timeout=10):
            print("'Google DNS' tab clicked successfully.")
            # Give some time for the tab switch and potential JS loading initiated by the click
            time.sleep(2) # Reduced from 5, as we'll have a more specific wait below
            save_debug_info(driver, "after_google_dns_tab_click")

            # --- Wait for DNS records content within the Google DNS tab to appear ---
            # We assume the content for Google DNS is within a div with id="google".
            # We will wait for a specific, known element *inside* this div to ensure data is loaded.
            # This XPath targets the green dot span before an IP, which is part of our regex.
            # This is a more reliable indicator that the A records table is populated.
            # The div with id="google" should be the parent or ancestor of these records.
            # IMPORTANT: The actual content might be in a different sub-container within div#google.
            # We are looking for an element that matches part of our regex *within* the #google div.
            
            # XPath for a A record entry (green dot + IP) *inside* the div with id="google"
            # This assumes the structure from your regex: a span with 'bg-green-400' followed by an IP.
            # We'll wait for the first such IP address to become visible.
            first_google_dns_ip_locator = (By.XPATH, "//div[@id='google']//span[contains(@class, 'bg-green-400')]/following-sibling::span[string-length(normalize-space(text())) > 0 and count(text()) > 0 and text()[contains(.,'.')]]")
            
            wait_time_content = 20 # Increased wait time for content loading
            print(f"Waiting for Google DNS A record content (e.g., first IP in div#google: '{first_google_dns_ip_locator[1]}') to be visible (up to {wait_time_content} seconds)...")
            try:
                 WebDriverWait(driver, wait_time_content).until(
                     EC.visibility_of_element_located(first_google_dns_ip_locator)
                 )
                 print("Google DNS A record content (first IP) is visible. Proceeding to fetch source.")
                 time.sleep(3) # Allow a bit more time for any final JS rendering after visibility
                 save_debug_info(driver, "google_dns_content_visible")
            except TimeoutException:
                print(f"Timeout waiting for Google DNS A record content (first IP) to be visible in div#google.")
                print("This might mean div#google is not the correct container, or content structure changed, or content did not load.")
                save_debug_info(driver, "timeout_waiting_google_dns_content")
                # We will still try to get the page source and match, in case some data is there.
        
        else: # Google DNS tab click failed
            print("'Google DNS' tab could not be clicked. Regex matching will likely fail or be incorrect.")
            save_debug_info(driver, "google_dns_tab_click_failed_critical")
            # If this click is essential, consider returning None or raising an error here.

       
        # --- Fetch final HTML and extract ---
        # This part executes regardless of whether the specific content wait succeeded,
        # to try and salvage data if possible, or to get the page source for debugging.
        print("Fetching final page source for regex matching...")
        html_content = driver.page_source
        with open("final_page_source_for_regex.html", "w", encoding='utf-8') as f: f.write(html_content)
        print("Saved final page source to final_page_source_for_regex.html")

        matches = pattern.findall(html_content) 
        
        if matches: 
            print(f"Regex found {len(matches)} potential matches.")
            unique_ip_country_pairs = set() 

            for ip, city, country_en_raw_from_regex in matches: 
                ip_clean = ip.strip() 
                country_en_raw = country_en_raw_from_regex.strip() 
                country_final = "" 

                country_en_upper = country_en_raw.upper() 
                if country_en_upper == "US" or country_en_raw.lower() == "united states":
                    country_final = "美国" 
                elif country_en_upper == "HK" or country_en_raw.lower() == "hong kong":
                    country_final = "香港" 
                
                if not country_final and country_en_raw:
                    translated_cn = translate_to_chinese(country_en_raw)
                    if translated_cn and translated_cn != country_en_raw:
                        country_final = translated_cn
                    else: 
                        country_final = country_en_raw 

                if country_final:
                    country_final = country_final.strip() 
                    original_country_for_log = country_final 
                    if country_final == "韩国，共和国": 
                        country_final = "韩国" 
                        print(f"Applying string fix: changing '{original_country_for_log}' to '{country_final}'")
                    elif country_final == "英国英国和北爱尔兰":  
                        country_final = "英国" 
                        print(f"Applying string fix: changing '{original_country_for_log}' to '{country_final}'")
                
                if ip_clean and country_final:
                    unique_ip_country_pairs.add((ip_clean, country_final))  
                else: 
                    print(f"Warning: Empty IP or undetermined/empty Final Country. IP:'{ip_clean}', Raw_EN_Country:'{country_en_raw}', Determined_Country:'{country_final}'")
            
            if unique_ip_country_pairs:
                print(f"Found {len(unique_ip_country_pairs)} unique (IP, Final Country) pairs after processing.")

                all_formatted_lines = [] 
                hk_formatted_lines = []  
                us_formatted_lines = []  

                sorted_ip_country_pairs = sorted(list(unique_ip_country_pairs), key=lambda x: tuple(map(int, x[0].split('.'))))

                for ip_addr, country_name in sorted_ip_country_pairs:
                    line_to_write = f"{ip_addr}#{country_name}.PUG" 
                    all_formatted_lines.append(line_to_write) 

                    if country_name == "香港": 
                        hk_formatted_lines.append(line_to_write)
                    elif country_name == "美国": 
                        us_formatted_lines.append(line_to_write)
                
                env_file = os.getenv('GITHUB_ENV') 

                with open(output_file, "w", encoding="utf-8") as f:
                    for line in all_formatted_lines:
                        f.write(f"{line}\n")
                print(f"All {len(all_formatted_lines)} unique results saved to {output_file}")
                if env_file: 
                    with open(env_file, "a") as f_env: f_env.write(f"Google_TXT_FILE={output_file}\n")

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
            
            else: 
                 print("No valid unique (IP, Final Country) pairs found after cleaning and translation.")
                 save_debug_info(driver, "no_valid_unique_ip_country_pairs")
        else: 
            print("No matches found by regex in the final page source.")
            save_debug_info(driver, "final_page_no_regex_match") 

        return matches if matches else None 

    except Exception as e: 
        print(f"An unhandled error occurred in Selenium operation: {e}")
        traceback.print_exc() 
        if driver: save_debug_info(driver, "unhandled_exception")
        return None
    finally: 
        if driver:
            print("Quitting WebDriver.")
            driver.quit()

# --- Main execution block ---
if __name__ == "__main__":
    url = "https://www.nslookup.io/domains/bpb.yousef.isegaro.com/dns-records/" 
    
    pattern = re.compile(
        r'<span class="mr-1.5 h-2 w-2 rounded-full bg-green-400"[^>]*></span>\s*([\d.]+)\s*</div>'
        r'.*?' 
        r'<div class="bg-slate-900 text-white[^"]*whitespace-nowrap"[^>]*>\s*'
        r'([^,]+?)'                 
        r'(?:\s*,\s*[^,]+?)*?'      
        r'\s*,\s*([^<]+?)'          
        r'\s*</div>', 
        re.DOTALL | re.IGNORECASE 
    )

    output_filename = "Google.txt" 

    print(f"Fetching and parsing URL: {url}")
    results = extract_ip_country_dynamic(url, pattern, output_file=output_filename)

    if results: 
        print(f"\n--- Regex initially found {len(results)} matches. Check output files for processed results. ---")
        if os.path.exists(output_filename):
            print(f"Main output file: {output_filename}")
        if os.path.exists("Google.Hk.txt"):
            print(f"Hong Kong output file: Google.Hk.txt")
        if os.path.exists("Google.US.txt"):
            print(f"US output file: Google.US.txt")
    else:
        print(f"\n--- No results found or an error occurred. Check logs, debug screenshots/HTML, and final_page_source_for_regex.html. ---")
