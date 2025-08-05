#!/usr/bin/env python3
"""
Selenium Debug untuk Google Forms submission
Visual debugging dengan browser untuk melihat apa yang terjadi
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import logging

from config import FORM_URL

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def setup_driver(headless=False):
    """Setup Chrome driver dengan options"""
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    
    # User agent yang sama dengan requests
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def selenium_form_test():
    """Test form submission dengan Selenium"""
    driver = None
    try:
        print("🚀 Starting Selenium Debug Test")
        print("=" * 50)
        
        # Setup driver (headless=False untuk melihat browser)
        driver = setup_driver(headless=False)
        print("✅ Chrome driver initialized")
        
        # Load form
        print(f"📱 Loading form: {FORM_URL[:100]}...")
        driver.get(FORM_URL)
        print("✅ Form loaded successfully")
        
        # Wait for form to be fully loaded
        wait = WebDriverWait(driver, 10)
        
       
        
        # Get page title
        title = driver.title
        print(f"📄 Page title: {title}")
        
        # Check if form is accepting responses
        page_source = driver.page_source.lower()
        if "no longer accepting" in page_source or "tidak menerima" in page_source:
            print("❌ Form is no longer accepting responses!")
            return False
        
        # Find all input elements
        inputs = driver.find_elements(By.CSS_SELECTOR, "input[name^='entry.']")
        textareas = driver.find_elements(By.CSS_SELECTOR, "textarea[name^='entry.']")
        selects = driver.find_elements(By.CSS_SELECTOR, "select[name^='entry.']")
        
        print(f"📋 Found form elements:")
        print(f"  - Input fields: {len(inputs)}")
        print(f"  - Textarea fields: {len(textareas)}")
        print(f"  - Select fields: {len(selects)}")
        
        # Complete test data from prefilled URL
        test_data = {
            "entry.574418038": "Ya",
            "entry.491424067": "Tidak", 
            "entry.1076213498": "6",
            "entry.2114887994": "Ya",
            "entry.540416168": "2",
            "entry.283916026": "Selenium Test Debug",
            "entry.1459672174": "081234567890",
            "entry.812632673": "Teknik Lingkungan",
            "entry.448756363": "Laki-laki",
            "entry.1637082189": "Keselarasan dengan nilai dalam diri",
            "entry.1368563016": "Twitter",
            "entry.538933348": "Ya",
            "entry.654411692": "DSA",
            "entry.1473767745": "Ya", 
            "entry.138067838": "DSAD",
            "entry.1766530136": "Ya",
            "entry.1226795643": "6. ENVIRONMENTAL ADVISOR / PENASIHAT LINGKUNGAN",
            "entry.934212234": "Memahami prinsip-prinsip Keselamatan dan Kesehatan Kerja (K3)",
            "entry.418468244": "GHRM sangat penting untuk masa depan",
            "entry.1578935184": "Green skills sangat mempengaruhi",
            "entry.366578558": "IPB perlu program lebih baik"
        }
        
        # Navigate through multi-section form
        section_num = 1
        total_filled = 0
        max_sections = 20  # Safety limit to prevent infinite loop
        
        while section_num <= max_sections:
            print(f"\n📄 Processing Section {section_num}")
            
            # Find current section's fields and fill them
            section_filled = 0
            
            for entry_name, value in test_data.items():
                if fill_field_if_present(driver, entry_name, value):
                    section_filled += 1
                    total_filled += 1
            
            print(f"  ✅ Filled {section_filled} fields in this section")
            
            # Processing current section
            
            # Debug: Show all buttons on current page
            all_page_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Berikutnya') or contains(text(), 'Kembali') or contains(text(), 'Kirim') or contains(text(), 'Submit')]")
            print(f"  🔍 All buttons found: {[btn.text.strip() for btn in all_page_buttons if btn.is_displayed()]}")
            
            # Look for "Berikutnya" (Next) button
            next_button = find_next_button(driver)
            
            if next_button:
                button_text = next_button.text.strip()
                print(f"  ➡️  Found 'Berikutnya' button: '{button_text}'")
                
                # Double check it's really "Berikutnya"
                if 'berikutnya' in button_text.lower():
                    driver.execute_script("arguments[0].scrollIntoView();", next_button)
                    time.sleep(1)
                    driver.execute_script("arguments[0].click();", next_button)
                    print("  ✅ Clicked Next button")
                    
                    # Wait for next section to load
                    time.sleep(2)
                    section_num += 1
                else:
                    print(f"  ⚠️  Button text '{button_text}' is not 'Berikutnya', looking for submit...")
                    break
                
            else:
                # No next button found, look for submit button
                print("  🔍 Looking for submit button...")
                
                # Debug: Show all buttons on page
                all_buttons = driver.find_elements(By.XPATH, "//*[contains(text(), 'Kirim') or contains(text(), 'Submit') or @role='button' or @type='submit']")
                print(f"  🔍 Found {len(all_buttons)} potential buttons:")
                for i, btn in enumerate(all_buttons):
                    try:
                        print(f"    {i+1}. Text: '{btn.text.strip()}' | Tag: {btn.tag_name} | Visible: {btn.is_displayed()}")
                    except:
                        print(f"    {i+1}. Error reading button info")
                
                submit_button = find_submit_button(driver)
                
                if submit_button:
                    print(f"  📤 Found submit button: '{submit_button.text}' | Tag: {submit_button.tag_name}")
                    driver.execute_script("arguments[0].scrollIntoView();", submit_button)
                    time.sleep(2)
                    
                    print("📤 Submitting form...")
                    driver.execute_script("arguments[0].click();", submit_button)
                    
                    # Wait for submission
                    print("⏳ Waiting for submission response...")
                    time.sleep(5)
                    break
                else:
                    print("  ❌ No submit button found after all strategies!")
                    print("  📸 Taking screenshot for debugging...")
                    driver.save_screenshot("no_submit_button_found.png")
                    break
        
        # Safety check for infinite loop
        if section_num > max_sections:
            print(f"\n⚠️  Reached maximum sections ({max_sections}), stopping to prevent infinite loop")
            driver.save_screenshot("max_sections_reached.png")
        
        print(f"\n📝 Total fields filled: {total_filled}")
        
        # Check submission results
        current_url = driver.current_url
        page_title = driver.title
        page_content = driver.page_source.lower()
        
        print(f"\n📨 After submission:")
        print(f"  Current URL: {current_url}")
        print(f"  Page title: {page_title}")
        
        # Check for success indicators
        success_indicators = [
            "your response has been recorded",
            "thank you",
            "terima kasih",
            "response recorded",
            "submitted successfully"
        ]
        
        success_found = any(indicator in page_content for indicator in success_indicators)
        
        # Check for error indicators  
        error_indicators = [
            "required",
            "error", 
            "invalid",
            "wajib",
            "gagal"
        ]
        
        error_found = any(indicator in page_content for indicator in error_indicators)
        
        print(f"  ✅ Success indicators: {success_found}")
        print(f"  ❌ Error indicators: {error_found}")
        
        # Take final screenshot
        driver.save_screenshot("form_submitted.png")
        print("📸 Final screenshot saved: form_submitted.png")
        
        if success_found:
            print("\n🎉 Form submitted successfully!")
            print("👀 Check your Google Sheets for the data")
            return True
        elif error_found:
            print("\n⚠️  Errors detected in submission")
            return False
        else:
            print("\n❓ Submission status unclear")
            print("💾 Check screenshots and Google Sheets manually")
            return True
        
    except Exception as e:
        print(f"❌ Selenium test failed: {e}")
        if driver:
            driver.save_screenshot("error_screenshot.png")
            print("📸 Error screenshot saved")
        return False
        
    finally:
        # Keep browser open for inspection
        print("\n🔍 Browser will stay open for 30 seconds for inspection...")
        time.sleep(30)
        
        if driver:
            driver.quit()
            print("🚪 Browser closed")

def fill_field_if_present(driver, entry_name, value):
    """Fill field if present in current section"""
    try:
        element = driver.find_element(By.NAME, entry_name)
        
        tag_name = element.tag_name.lower()
        element_type = element.get_attribute("type")
        
        if tag_name == "input":
            if element_type == "radio":
                radios = driver.find_elements(By.NAME, entry_name)
                for radio in radios:
                    radio_value = radio.get_attribute("value")
                    if radio_value == value:
                        driver.execute_script("arguments[0].click();", radio)
                        print(f"    ✅ Radio {entry_name}: {value}")
                        return True
            elif element_type == "checkbox":
                if value.lower() in ["ya", "yes", "true"]:
                    driver.execute_script("arguments[0].click();", element)
                    print(f"    ✅ Checkbox {entry_name}")
                    return True
            else:
                element.clear()
                element.send_keys(value)
                print(f"    ✅ Input {entry_name}: {value}")
                return True
                
        elif tag_name == "textarea":
            element.clear()
            element.send_keys(value)
            print(f"    ✅ Textarea {entry_name}: {value}")
            return True
            
        elif tag_name == "select":
            from selenium.webdriver.support.ui import Select
            select = Select(element)
            select.select_by_value(value)
            print(f"    ✅ Select {entry_name}: {value}")
            return True
            
    except NoSuchElementException:
        # Field not in current section, skip silently
        pass
    except Exception as e:
        print(f"    ❌ Error filling {entry_name}: {e}")
    
    return False

def find_next_button(driver):
    """Find 'Berikutnya' (Next) button - exclude 'Kembali' (Back)"""
    try:
        # Look specifically for "Berikutnya" text, not "Kembali"
        xpath_selectors = [
            "//span[contains(text(), 'Berikutnya')]",
            "//div[contains(text(), 'Berikutnya')]",
            "//*[contains(text(), 'Next')]"
        ]
        
        for xpath in xpath_selectors:
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements:
                text = elem.text.strip().lower()
                # Make sure it's "Berikutnya", not "Kembali"
                if ('berikutnya' in text or 'next' in text) and 'kembali' not in text and elem.is_displayed():
                    return elem
        
        # If no specific text match, look for elements with button-like classes
        # but check their text content
        button_elements = driver.find_elements(By.CSS_SELECTOR, ".NPEfkd.RveJvd.snByac, .l4V7wb.Fxmcue")
        for elem in button_elements:
            text = elem.text.strip().lower()
            if ('berikutnya' in text or 'next' in text) and 'kembali' not in text and elem.is_displayed():
                return elem
                
    except Exception as e:
        print(f"    Error in find_next_button: {e}")
    
    return None

def find_submit_button(driver):
    """Find submit button (Kirim) with better detection"""
    # Try multiple strategies to find submit button
    
    # Strategy 1: XPath with text content
    try:
        xpath_selectors = [
            "//*[contains(text(), 'Kirim')]",
            "//*[contains(text(), 'Submit')]",
            "//span[contains(text(), 'Kirim')]",
            "//span[contains(text(), 'Submit')]",
            "//div[contains(text(), 'Kirim')]"
        ]
        
        for xpath in xpath_selectors:
            elements = driver.find_elements(By.XPATH, xpath)
            for elem in elements:
                # Check if it's clickable and looks like a button
                if elem.is_displayed() and elem.is_enabled():
                    return elem
    except:
        pass
    
    # Strategy 2: CSS selectors for button structures
    try:
        css_selectors = [
            "[type='submit']",
            "[role='button']",
            ".l4V7wb.Fxmcue",  # From your HTML structure
            ".NPEfkd.RveJvd.snByac",  # From your HTML structure
            "div[role='button']",
            "span[role='button']"
        ]
        
        for selector in css_selectors:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            for elem in elements:
                text = elem.text.lower()
                if ('kirim' in text or 'submit' in text) and elem.is_displayed():
                    return elem
    except:
        pass
    
    # Strategy 3: Look for parent elements of spans containing "Kirim"
    try:
        kirim_spans = driver.find_elements(By.XPATH, "//span[contains(text(), 'Kirim')]")
        for span in kirim_spans:
            # Get parent elements that might be clickable
            parent = span.find_element(By.XPATH, "..")
            if parent.is_displayed() and parent.is_enabled():
                # Check if parent looks like a button
                parent_classes = parent.get_attribute("class")
                if parent_classes and ("button" in parent_classes.lower() or "btn" in parent_classes.lower()):
                    return parent
                
                # Try grandparent
                try:
                    grandparent = parent.find_element(By.XPATH, "..")
                    if grandparent.is_displayed() and grandparent.is_enabled():
                        return grandparent
                except:
                    pass
                    
                return parent  # Return parent as fallback
    except:
        pass
    
    # Strategy 4: Find all clickable elements and check text
    try:
        all_clickable = driver.find_elements(By.XPATH, "//*[@role='button'] | //button | //input[@type='submit'] | //div[contains(@class, 'button')] | //span[contains(@class, 'button')]")
        for elem in all_clickable:
            if elem.is_displayed() and elem.is_enabled():
                text = elem.text.lower()
                if 'kirim' in text or 'submit' in text:
                    return elem
    except:
        pass
    
    print("  ⚠️  No submit button found with any strategy!")
    return None

if __name__ == "__main__":
    success = selenium_form_test()
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test completed with issues!")
    
    print("\n📋 Check the following:")
    print("1. Screenshots: form_loaded.png, form_filled.png, form_submitted.png")
    print("2. Google Sheets for new data")
    print("3. Any error messages in console")