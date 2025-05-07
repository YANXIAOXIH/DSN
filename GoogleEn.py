from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException, NoSuchElementException
from selenium_stealth import stealth
import re
import os
import time

# save_debug_info
def save_debug_info(driver, prefix="error"):
    try:
        screenshot_path = f"{prefix}_screenshot.png"
        page_source_path = f"{prefix}_page_source.html"
        
        current_url = "N/A"
        try:
            current_url = driver.current_url
        except Exception: pass
        print(f"Saving debug info for URL: {current_url} (prefix: {prefix})")

        driver.save_screenshot(screenshot_path)
        print(f"Debug screenshot saved as {screenshot_path}")
        with open(page_source_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        print(f"Debug page source saved as {page_source_path}")

        env_file = os.getenv('GITHUB_ENV')
        if env_file:
            with open(env_file, "a") as f:
                if os.path.exists(screenshot_path): f.write(f"DEBUG_SCREENSHOT_{prefix.upper()}={screenshot_path}\n")
                if os.path.exists(page_source_path): f.write(f"DEBUG_PAGESOURCE_{prefix.upper()}={page_source_path}\n")
    except Exception as e_save: print(f"Could not save debug info: {e_save}")


# click_element_robustly
def click_element_robustly(driver, by, value, timeout=10):
    """Tries to click an element, handling common exceptions."""
    try:
        element = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )
        element_text = "N/A"
        try: element_text = element.text[:50] if element.text else element.get_attribute('outerHTML')[:70]
        except: pass
        print(f"Element ({by}='{value}') found. Text/HTML: '{element_text}...'. Attempting click.")
        try: # 尝试JS点击优先，有时更稳定
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
            time.sleep(0.3)
            driver.execute_script("arguments[0].click();", element)
            print(f"Clicked element ({by}='{value}') via JS click.")
            return True
        except Exception as e_js:
            print(f"JS click failed for ({by}='{value}'): {e_js}. Trying standard click.")
            try:
                element.click()
                print(f"Clicked element ({by}='{value}') via standard click.")
                return True
            except Exception as e_std:
                print(f"Standard click also failed for ({by}='{value}'): {e_std}")
                return False
    except TimeoutException: print(f"Element ({by}='{value}') not found/clickable within {timeout}s.")
    except StaleElementReferenceException: print(f"Element ({by}='{value}') became stale.")
    except Exception as e: print(f"Error clicking ({by}='{value}'): {e}")
    return False
    
 #<-- Output filename changed
def extract_ip_country_dynamic(url, pattern, output_file="GoogleEn.txt"):
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
        print("Applying selenium-stealth modifications...")
        stealth(driver, languages=["en-US", "en"], vendor="Google Inc.", platform="Win32", webgl_vendor="Intel Inc.", renderer="Intel Iris OpenGL Engine", fix_hairline=True)
        print("Selenium-stealth applied.")
        
        print(f"Navigating to URL: {url}")
        driver.get(url)
        print("Initial page loaded.")
        save_debug_info(driver, "initial_load") 

        # --- 尝试快速处理 Cookie (如果存在) ---
        # 非阻塞式尝试，如果失败就继续
        print("Quickly trying to accept cookies if banner exists...")
        cookie_selector_id = (By.ID, "CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll")
        if click_element_robustly(driver, cookie_selector_id[0], cookie_selector_id[1], timeout=3): # 短超时
             print("Potential cookie banner handled by ID.")
             time.sleep(1) # 短暂等待
             save_debug_info(driver, "after_cookie_attempt")
        else:
             print("Cookie banner ID not found quickly or click failed, proceeding anyway.")
             # 可以再尝试一个基于文本的快速查找
             cookie_selector_xpath = (By.XPATH, "//button[normalize-space(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'))='allow all']")
             if click_element_robustly(driver, cookie_selector_xpath[0], cookie_selector_xpath[1], timeout=2):
                 print("Potential cookie banner handled by text.")
                 time.sleep(1)
                 save_debug_info(driver, "after_cookie_attempt_text")
             else:
                 print("Cookie banner text not found quickly, proceeding.")
                 save_debug_info(driver, "no_cookie_click")


        # --- 点击 "Google DNS" 选项卡 ---
        google_dns_tab_locator = (By.XPATH, "//a[normalize-space(.)='Google DNS']")
        print(f"Attempting to click 'Google DNS' tab...")
        if click_element_robustly(driver, google_dns_tab_locator[0], google_dns_tab_locator[1], timeout=10):
            print("'Google DNS' tab clicked successfully.")
            time.sleep(5) # *** 增加等待时间，让JS加载Google DNS数据 ***
            save_debug_info(driver, "after_google_dns_tab_click")
        else:
            print("'Google DNS' tab could not be clicked. Trying to proceed, results might be inaccurate.")
            save_debug_info(driver, "google_dns_tab_click_failed")
            # 可以考虑在此处失败，因为数据源不确定
            # return None

        # --- 等待 DNS 记录容器出现 (而不是具体行可见) ---
        # 等待包含所有记录的主要div加载完成
        records_container_locator = (By.XPATH, "//div[contains(@class,'bg-white')]/div[contains(@class,'flex')]/div[contains(@class,'shrink')]") # 定位到包含A记录的那个div
        wait_time = 20
        print(f"Waiting for DNS records container to be present (up to {wait_time} seconds)...")
        try:
             WebDriverWait(driver, wait_time).until(
                 EC.presence_of_element_located(records_container_locator)
             )
             print("DNS records container is present in DOM.")
             # 现在我们知道容器存在了，再给JS一点时间渲染内部内容
             print("Giving JS 5 seconds to render content...")
             time.sleep(5) 
             save_debug_info(driver, "dns_container_present_and_waited")

        except TimeoutException:
            print(f"Timeout waiting for DNS records container (locator: {records_container_locator}). Page might not have loaded correctly.")
            save_debug_info(driver, "timeout_waiting_dns_container")
            # 即使容器没找到，也尝试抓取源码
       
        # --- 获取最终 HTML 并提取 ---
        print("Fetching final page source for regex matching...")
        html_content = driver.page_source
        # 为了调试，可以保存最终的HTML
        with open("final_page_source_for_regex.html", "w", encoding='utf-8') as f:
             f.write(html_content)
        print("Saved final page source to final_page_source_for_regex.html")

        matches = pattern.findall(html_content)
        
        if matches:
            print(f"Regex found {len(matches)} potential matches.")
            unique_results = set()
            for ip, city, country in matches:
                ip_clean = ip.strip()
                country_clean = country.strip().replace(' ', '_') # 替换国家名中的空格
                if ip_clean and country_clean: # 确保提取到了有效信息
                    unique_results.add(f"{ip_clean}#{country_clean}")
                else:
                    print(f"Warning: Empty IP or Country found - IP:'{ip}', City:'{city}', Country:'{country}'")

            if unique_results:
                print(f"Found {len(unique_results)} unique IP#Country pairs.")
                with open(output_file, "w", encoding="utf-8") as f:
                    # 按IP地址排序输出
                    sorted_results = sorted(list(unique_results), key=lambda x: tuple(map(int, x.split('#')[0].split('.'))))
                    for line in sorted_results:
                        f.write(f"{line}\n")
                print(f"Unique results saved to {output_file}")
                
                # 设置 GITHUB_ENV
                env_file = os.getenv('GITHUB_ENV')
                if env_file:
                    with open(env_file, "a") as f:
                        f.write(f"Google_TXT_FILE={output_file}\n")
            else:
                 print("No valid unique results after cleaning.")
                 save_debug_info(driver, "no_valid_unique_results")

        else:
            print("No matches found by regex in the final page source.")
            save_debug_info(driver, "final_page_no_regex_match") # 这个截图很重要

        # 返回找到的原始匹配项数量或None
        return matches if matches else None # 返回原始匹配用于主程序判断

    except Exception as e:
        print(f"An unhandled error occurred in Selenium operation: {e}")
        import traceback
        traceback.print_exc() # 打印详细错误堆栈
        if driver:
            save_debug_info(driver, "unhandled_exception")
        return None
    finally:
        if driver:
            print("Quitting WebDriver.")
            driver.quit()

if __name__ == "__main__":
    url = "https://www.nslookup.io/domains/bpb.yousef.isegaro.com/dns-records/"
    
    # 优化正则表达式，使其对A记录块内的换行和空格更宽容
    # 关键是匹配 record-A div, 然后在里面找 IP 和 Location link
    pattern = re.compile(
        r'<span>\s*([\d.]+)\s*</span>'  # Capture IP inside span
        r'.*?'                          # Match until...
        r'</tr>\s*<tr class="hidden">'  # ...end of IP row and start of hidden row
        r'.*?<th[^>]*>\s*Location\s*</th>' # Find "Location" header
        r'\s*<td[^>]*>\s*<a[^>]*>'         # Find table cell and start of link
        r'\s*([^<,]+?)\s*,'           # Capture City (Group 2) - non-greedy
        r'\s*[^,]+?,'                 # Match State/Region (non-capturing, non-greedy)
        r'\s*([^<]+?)\s*'             # Capture Country (Group 3) - non-greedy
        r'</a>',                      # Match closing </a> tag
        re.DOTALL | re.IGNORECASE      
    )

    output_filename = "GoogleEn.txt" # <-- Changed filename

    print(f"Fetching and parsing URL: {url}")
    results = extract_ip_country_dynamic(url, pattern, output_file=output_filename)

    if results:
        print(f"\n--- Regex initially found {len(results)} matches. Check {output_filename} for unique results. ---")
    else:
        print(f"\n--- No results found or an error occurred. Check logs and artifacts. ---")