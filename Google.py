from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
    StaleElementReferenceException,
    NoSuchElementException
)
from deep_translator import GoogleTranslator
from selenium_stealth import stealth
import re
import os
import time
import traceback

# --- Function to save debugging information ---
# Called at critical steps or when errors occur to save screenshots and page source.
def save_debug_info(driver, prefix="error"):
    try:
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        screenshot_path = f"{prefix}_{timestamp}_screenshot.png"
        page_source_path = f"{prefix}_{timestamp}_page_source.html"
        current_url = "N/A"
        try:
            current_url = driver.current_url
        except Exception:
            pass  # Driver might be invalid

        print(f"Saving debug info: URL: {current_url} (prefix: {prefix})")
        driver.save_screenshot(screenshot_path)
        print(f"Debug screenshot saved as: {screenshot_path}")
        with open(page_source_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"Debug page source saved as: {page_source_path}")

        # If in GitHub Actions, write debug file paths to GITHUB_ENV for artifact upload
        env_file = os.getenv('GITHUB_ENV')
        if env_file:
            with open(env_file, "a") as f_env:
                if os.path.exists(screenshot_path):
                    f_env.write(f"DEBUG_SCREENSHOT_{prefix.upper()}={screenshot_path}\n")
                if os.path.exists(page_source_path):
                    f_env.write(f"DEBUG_PAGESOURCE_{prefix.upper()}={page_source_path}\n")
    except Exception as e_save:
        print(f"Could not save debug info: {e_save}")

# --- Robust element clicking function ---
# Tries multiple methods (including JS click) to click an element, improving success rate.
def click_element_robustly(driver, by, value, timeout=10):
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element_text_snippet = "N/A"
        try:
            element_text_snippet = element.text[:50] if element.text else element.get_attribute('outerHTML')[:70]
        except Exception:
            pass
        print(f"Element ({by}='{value}') found. Text/HTML: '{element_text_snippet}...'. Attempting click.")

        # Prefer JavaScript click first
        try:
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.3)  # Wait for scroll to complete
            driver.execute_script("arguments[0].click();", element)
            print(f"Clicked element ({by}='{value}') via JS click successfully.")
            return True
        except Exception as e_js:
            print(f"JS click failed for ({by}='{value}'): {e_js}. Trying standard click.")
            # Fallback to standard click
            try:
                element.click()
                print(f"Clicked element ({by}='{value}') via standard click successfully.")
                return True
            except Exception as e_std:
                print(f"Standard click also failed for ({by}='{value}'): {e_std}")
                return False
    except TimeoutException:
        print(f"Element ({by}='{value}') not found/clickable within {timeout}s.")
    except StaleElementReferenceException:
        print(f"Element ({by}='{value}') became stale.")
    except Exception as e:
        print(f"Error clicking element ({by}='{value}'): {e}")
    return False

# --- Translation function with caching ---
translation_cache = {}  # Cache for translated texts
try:
    # Initialize Google Translator (translates to Simplified Chinese)
    translator = GoogleTranslator(source='auto', target='zh-CN')
except Exception as e:
    print(f"Error initializing translator: {e}. Translations will be skipped.")
    translator = None

def translate_to_chinese(text_to_translate):
    global translator, translation_cache
    if not translator or not text_to_translate:
        return text_to_translate

    text_to_translate = text_to_translate.strip()
    if not text_to_translate: # Added check for empty string after strip
        return text_to_translate
    if text_to_translate in translation_cache:
        return translation_cache[text_to_translate]

    try:
        translated_text = translator.translate(text_to_translate)
        if translated_text:
            translation_cache[text_to_translate] = translated_text.strip()
            print(f"Translated '{text_to_translate}' to '{translation_cache[text_to_translate]}'")
            return translation_cache[text_to_translate]
        else:
            print(f"Warning: Translation returned empty for '{text_to_translate}'. Using original.")
            translation_cache[text_to_translate] = text_to_translate
            return text_to_translate
    except Exception as e:
        print(f"Warning: Translation failed for '{text_to_translate}': {e}. Using original.")
        translation_cache[text_to_translate] = text_to_translate
        return text_to_translate
# --- End of translation function ---

# --- Main function to extract IP and Country information ---
def extract_ip_country_dynamic(url, target_pattern, output_file="Google.txt"):
    print("Setting up Chrome options...")
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
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

        # Attempt to quickly handle Cookie pop-up
        print("Quickly trying to accept cookies if banner exists...")
        cookie_selectors = [
            (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"),
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'allow all')]"),
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'accept all')]"),
            (By.XPATH, "//button[contains(translate(normalize-space(.), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'agree')]")
        ]
        cookie_clicked = False
        for by_sel, selector_val in cookie_selectors:
            if click_element_robustly(driver, by_sel, selector_val, timeout=3):
                cookie_clicked = True
                print(f"Potential cookie banner handled by {by_sel}='{selector_val}'.")
                time.sleep(1) # Wait for banner to disappear
                save_debug_info(driver, f"after_cookie_attempt_{by_sel}")
                break
        if not cookie_clicked:
            print("Cookie banner not found quickly or click failed, proceeding.")
            save_debug_info(driver, "no_cookie_click")

        # Click the "Google DNS" tab
        google_dns_tab_locator = (By.XPATH, "//a[normalize-space(.)='Google DNS' and contains(@href, '#google')]")
        print(f"Attempting to click 'Google DNS' tab with locator: {google_dns_tab_locator}...")
        if click_element_robustly(driver, google_dns_tab_locator[0], google_dns_tab_locator[1], timeout=10):
            print("'Google DNS' tab clicked successfully.")
            time.sleep(2) # Brief wait for tab switch and initial JS loading
            save_debug_info(driver, "after_google_dns_tab_click")

            # Define XPath for the container of Google DNS results (identified by its specific paragraph)
            google_dns_content_container_xpath = "//div[contains(@class, 'bg-white') and .//p[contains(text(), 'The Google DNS server responded')]]"
            # Define XPath for the first A record IP address span *within* that container
            # This ensures we wait for actual content to load, not just the container.
            first_google_dns_ip_locator = (
                By.XPATH,
                f"{google_dns_content_container_xpath}//h2[normalize-space()='A records']/following-sibling::div[1]"
                f"//table/tbody/tr[1]/td[2]/span[1][string-length(normalize-space(text())) > 0 and contains(text(), '.')]"
            )

            wait_time_content = 25 # Max time to wait for content
            print(f"Waiting for Google DNS A record content (e.g., first IP: '{first_google_dns_ip_locator[1]}') "
                  f"to be visible (up to {wait_time_content} seconds)...")
            try:
                 WebDriverWait(driver, wait_time_content).until(
                     EC.visibility_of_element_located(first_google_dns_ip_locator)
                 )
                 print("Google DNS A record content (first IP) is visible. Proceeding to fetch source.")
                 time.sleep(3) # Allow a bit more time for any final JS rendering
                 save_debug_info(driver, "google_dns_content_visible")
            except TimeoutException:
                print(f"Timeout waiting for Google DNS A record content (first IP) to be visible.")
                print("HTML structure for Google DNS A records might have changed, or content did not load as expected.")
                save_debug_info(driver, "timeout_waiting_google_dns_content")
        
        else: # Google DNS tab click failed
            print("'Google DNS' tab could not be clicked. Regex matching will likely fail or be incorrect.")
            save_debug_info(driver, "google_dns_tab_click_failed_critical")
            # Consider returning None or raising an error if this click is essential.

        # Fetch final HTML and extract using the provided regex pattern
        print("Fetching final page source for regex matching...")
        html_content = driver.page_source
        with open("final_page_source_for_regex.html", "w", encoding='utf-8') as f:
            f.write(html_content)
        print("Saved final page source to final_page_source_for_regex.html")

        matches = target_pattern.findall(html_content)
        
        if matches:
            print(f"Regex found {len(matches)} potential matches using the target pattern.")
            unique_ip_country_pairs = set()

            # Process each regex match (expected: ip, city, raw_country_name_en)
            for ip_addr, city, country_en_raw in matches:
                ip_clean = ip_addr.strip()
                country_en_raw_clean = country_en_raw.strip()
                country_final_chinese = "" # This will store the processed Chinese country name

                # --- Step 1: Direct mapping for common country codes/names for accuracy ---
                country_en_upper = country_en_raw_clean.upper()
                if country_en_upper == "US" or "UNITED STATES" in country_en_upper:
                    country_final_chinese = "美国" # "United States"
                elif country_en_upper == "HK" or "HONG KONG" in country_en_upper:
                    country_final_chinese = "香港" # "Hong Kong"
                # Add other direct mappings if needed, e.g., JP, GB

                # --- Step 2: If not directly mapped, try translation for other cases ---
                if not country_final_chinese and country_en_raw_clean:
                    translated_cn = translate_to_chinese(country_en_raw_clean)
                    # Use translated if it's different from original and not empty
                    if translated_cn and translated_cn != country_en_raw_clean:
                        country_final_chinese = translated_cn
                    else: # Translation failed, returned original, or was empty; fallback to original English name
                        country_final_chinese = country_en_raw_clean

                # --- Step 3: Apply specific string fixes/simplifications to the determined Chinese country name ---
                if country_final_chinese:
                    country_final_chinese = country_final_chinese.strip()
                    original_country_for_log = country_final_chinese
                    
                    if country_final_chinese == "韩国，共和国": # "Korea, Republic of"
                        country_final_chinese = "韩国" # "Korea"
                        print(f"Applying string fix: changing '{original_country_for_log}' to '{country_final_chinese}'")
                    elif "UNITED KINGDOM" in original_country_for_log.upper() or "英国英国" in original_country_for_log:
                        country_final_chinese = "英国" # "United Kingdom"
                        print(f"Applying string fix: changing '{original_country_for_log}' to '{country_final_chinese}'")
                    elif country_final_chinese == "阿拉伯联合酋长国": # "United Arab Emirates"
                        country_final_chinese = "阿联酋" # Simplified to "UAE" (in Chinese)
                        print(f"Applying simplification: changing '{original_country_for_log}' to '{country_final_chinese}'")
                    # Add more specific fixes or simplifications as needed
                
                if ip_clean and country_final_chinese:
                    unique_ip_country_pairs.add((ip_clean, country_final_chinese))
                else:
                    print(f"Warning: Empty IP or undetermined/empty Final Country. "
                          f"IP:'{ip_clean}', Raw_EN_Country:'{country_en_raw_clean}', "
                          f"Determined_CN_Country:'{country_final_chinese}'")
            
            # --- Processing and writing results to files ---
            if unique_ip_country_pairs:
                print(f"Found {len(unique_ip_country_pairs)} unique (IP, Final Country) pairs after processing.")

                all_formatted_lines = []
                hk_formatted_lines = []
                us_formatted_lines = []

                # Sort all pairs by IP address for consistent output
                sorted_ip_country_pairs = sorted(
                    list(unique_ip_country_pairs),
                    key=lambda x: tuple(map(int, x[0].split('.')))
                )

                for ip_val, country_name_cn in sorted_ip_country_pairs:
                    line_to_write = f"{ip_val}#{country_name_cn}.PUG"
                    all_formatted_lines.append(line_to_write)

                    if country_name_cn == "香港": # "Hong Kong"
                        hk_formatted_lines.append(line_to_write)
                    elif country_name_cn == "美国": # "United States"
                        us_formatted_lines.append(line_to_write)
                
                env_file_path = os.getenv('GITHUB_ENV')

                # Write the main file with all results
                with open(output_file, "w", encoding="utf-8") as f_main:
                    for line in all_formatted_lines:
                        f_main.write(f"{line}\n")
                print(f"All {len(all_formatted_lines)} unique results saved to {output_file}")
                if env_file_path:
                    with open(env_file_path, "a") as f_env_main:
                        f_env_main.write(f"Google_TXT_FILE={output_file}\n")

                # Write Hong Kong specific file
                hk_output_filename = "Google.Hk.txt"
                if hk_formatted_lines:
                    with open(hk_output_filename, "w", encoding="utf-8") as f_hk:
                        for line in hk_formatted_lines:
                            f_hk.write(f"{line}\n")
                    print(f"Hong Kong specific results ({len(hk_formatted_lines)} lines) saved to {hk_output_filename}")
                    if env_file_path:
                        with open(env_file_path, "a") as f_env_hk:
                            f_env_hk.write(f"Google_HK_TXT_FILE={hk_output_filename}\n")
                else:
                    print(f"No Hong Kong specific results found, {hk_output_filename} not created.")

                # Write US specific file
                us_output_filename = "Google.US.txt"
                if us_formatted_lines:
                    with open(us_output_filename, "w", encoding="utf-8") as f_us:
                        for line in us_formatted_lines:
                            f_us.write(f"{line}\n")
                    print(f"US specific results ({len(us_formatted_lines)} lines) saved to {us_output_filename}")
                    if env_file_path:
                        with open(env_file_path, "a") as f_env_us:
                            f_env_us.write(f"Google_US_TXT_FILE={us_output_filename}\n")
                else:
                    print(f"No US specific results found, {us_output_filename} not created.")
            
            else: # unique_ip_country_pairs is empty
                 print("No valid unique (IP, Final Country) pairs found after cleaning and translation.")
                 save_debug_info(driver, "no_valid_unique_ip_country_pairs")
        else: # matches is empty
            print(f"No matches found by the target regex in the final page source.")
            save_debug_info(driver, "final_page_no_target_regex_match")

        return matches if matches else None # Return original regex matches list or None

    except Exception as e_main:
        print(f"An unhandled error occurred in Selenium operation: {e_main}")
        traceback.print_exc() # Print full error stack trace
        if driver:
            save_debug_info(driver, "unhandled_exception")
        return None
    finally:
        if driver:
            print("Quitting WebDriver.")
            driver.quit()

# --- Main execution block ---
if __name__ == "__main__":
    TARGET_URL = "https://www.nslookup.io/domains/bpb.yousef.isegaro.com/dns-records/"
    
    # NEW Regex specifically for the Google DNS tab's A record structure on nslookup.io
    # This pattern expects to find an IP in a span, followed by a hidden row (tr class="hidden")
    # containing the location information within an <a> tag.
    GOOGLE_DNS_PATTERN = re.compile(
        r'<tr class="group">\s*'  # Start of an A record row (IP row)
        # Capture IP (Group 1) from its span; preceding img tag is optional
        r'.*?<td class="py-1">\s*(?:<img[^>]*>\s*)?<span>([\d.]+)</span>'
        r'.*?</tr>\s*'  # End of IP row
        # Start of the hidden location row and its inner div
        r'<tr class="hidden">\s*<td colspan="3">\s*<div[^>]*>\s*'
        # Location link (href can be variable, so we match broadly)
        r'.*?<a href="https://www.google.com/maps/search/[^"]*"[^>]*>'
        r'\s*([^<,]+?)\s*,'  # Capture City (Group 2) - non-greedy
        # Optional State/Region (non-capturing, non-greedy) - handles cases with or without state
        r'(?:[^,]+?,\s*)?'
        # Capture Country (Group 3) - non-greedy, up to the next HTML tag
        r'\s*([^<]+?)\s*'
        r'</a>'  # End of location link
        # The rest of the hidden row can vary, so match generally until its end
        r'.*?</tr>',
        re.DOTALL | re.IGNORECASE  # DOTALL makes . match newlines, IGNORECASE for case-insensitivity
    )

    MAIN_OUTPUT_FILENAME = "Google.txt"

    print(f"Fetching and parsing URL: {TARGET_URL}")
    # Pass the NEW Google DNS specific pattern to the extraction function
    extraction_results = extract_ip_country_dynamic(
        TARGET_URL,
        GOOGLE_DNS_PATTERN,
        output_file=MAIN_OUTPUT_FILENAME
    )

    # Script execution summary
    if extraction_results:
        print(f"\n--- Regex initially found {len(extraction_results)} matches. "
              f"Check output files for processed results. ---")
        if os.path.exists(MAIN_OUTPUT_FILENAME):
            print(f"Main output file: {MAIN_OUTPUT_FILENAME}")
        if os.path.exists("Google.Hk.txt"):
            print(f"Hong Kong output file: Google.Hk.txt")
        if os.path.exists("Google.US.txt"):
            print(f"US output file: Google.US.txt")
    else:
        print(f"\n--- No results found or an error occurred. "
              f"Check logs, debug screenshots/HTML, and final_page_source_for_regex.html. ---")
