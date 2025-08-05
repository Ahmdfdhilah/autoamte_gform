"""
Google Forms automation module using Selenium
"""

import logging
import time
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from ..utils.url_parser import extract_entry_order_from_url, generate_prefilled_url

logger = logging.getLogger(__name__)


class GoogleFormAutomation:
    """Google Forms automation class using Selenium"""
    
    def __init__(self, form_url: str, request_config: Dict = None):
        self.form_url = form_url
        self.entry_fields = []
        self.request_config = request_config or {}
        self.driver = None
    
    def extract_form_info(self, csv_headers: List[str] = None) -> tuple[List[str], Optional[str]]:
        """Extract entry IDs from CSV headers or URL"""
        try:
            # If we have CSV headers, use them directly
            if csv_headers:
                entry_fields = []
                for header in csv_headers:
                    if header.startswith('entry.'):
                        entry_fields.append(header)
                
                if entry_fields:
                    self.entry_fields = entry_fields
                    logger.info(f"Using CSV headers: {len(entry_fields)} entry fields found")
                    return self.entry_fields, self.form_url
            
            # Fallback to URL extraction
            entry_fields = extract_entry_order_from_url(self.form_url)
            self.entry_fields = entry_fields
            
            logger.info(f"Extracted {len(entry_fields)} entry fields from URL")
            return self.entry_fields, self.form_url
            
        except Exception as e:
            logger.error(f"Error extracting form info: {e}")
            return [], None
    
    def setup_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Setup Chrome driver"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        
        driver = webdriver.Chrome(options=chrome_options)
        return driver

    def fill_field_if_present(self, driver, entry_name: str, value: str) -> bool:
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
                            logger.debug(f"    ✅ Radio {entry_name}: {value}")
                            return True
                elif element_type == "checkbox":
                    if value.lower() in ["ya", "yes", "true"]:
                        driver.execute_script("arguments[0].click();", element)
                        logger.debug(f"    ✅ Checkbox {entry_name}")
                        return True
                else:
                    element.clear()
                    element.send_keys(value)
                    logger.debug(f"    ✅ Input {entry_name}: {value}")
                    return True
                    
            elif tag_name == "textarea":
                element.clear()
                element.send_keys(value)
                logger.debug(f"    ✅ Textarea {entry_name}: {value}")
                return True
                
            elif tag_name == "select":
                from selenium.webdriver.support.ui import Select
                select = Select(element)
                select.select_by_value(value)
                logger.debug(f"    ✅ Select {entry_name}: {value}")
                return True
                
        except NoSuchElementException:
            # Field not in current section, skip silently
            pass
        except Exception as e:
            logger.debug(f"    ❌ Error filling {entry_name}: {e}")
        
        return False

    def find_next_button(self, driver):
        """Find 'Berikutnya' (Next) button - exclude 'Kembali' (Back)"""
        try:
            xpath_selectors = [
                "//span[contains(text(), 'Berikutnya')]",
                "//div[contains(text(), 'Berikutnya')]",
                "//*[contains(text(), 'Next')]"
            ]
            
            for xpath in xpath_selectors:
                elements = driver.find_elements(By.XPATH, xpath)
                for elem in elements:
                    text = elem.text.strip().lower()
                    if ('berikutnya' in text or 'next' in text) and 'kembali' not in text and elem.is_displayed():
                        return elem
            
            button_elements = driver.find_elements(By.CSS_SELECTOR, ".NPEfkd.RveJvd.snByac, .l4V7wb.Fxmcue")
            for elem in button_elements:
                text = elem.text.strip().lower()
                if ('berikutnya' in text or 'next' in text) and 'kembali' not in text and elem.is_displayed():
                    return elem
                    
        except Exception as e:
            logger.debug(f"    Error in find_next_button: {e}")
        
        return None

    def find_submit_button(self, driver):
        """Find submit button (Kirim)"""
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
                    if elem.is_displayed() and elem.is_enabled():
                        return elem
        except:
            pass
        
        # Strategy 2: CSS selectors
        try:
            css_selectors = [
                "[type='submit']",
                "[role='button']",
                ".l4V7wb.Fxmcue",
                ".NPEfkd.RveJvd.snByac",
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
        
        # Strategy 3: Parent elements of Kirim spans
        try:
            kirim_spans = driver.find_elements(By.XPATH, "//span[contains(text(), 'Kirim')]")
            for span in kirim_spans:
                parent = span.find_element(By.XPATH, "..")
                if parent.is_displayed() and parent.is_enabled():
                    return parent
        except:
            pass
        
        return None

    def submit_form(self, form_data: Dict) -> bool:
        """Submit form using Selenium with multi-section navigation"""
        driver = None
        try:
            logger.info("🔄 Starting Selenium form submission")
            logger.info(f"📊 Form data: {len(form_data)} fields to fill")
            
            # Setup driver (headless by default)
            driver = self.setup_driver(headless=True)
            
            # Generate prefilled URL with CSV data
            entry_order = extract_entry_order_from_url(self.form_url)
            prefilled_url = generate_prefilled_url(self.form_url, entry_order, form_data)
            
            driver.get(prefilled_url)
            logger.info(f"✅ Form loaded with prefilled data")
            
            # Wait for form to be ready
            wait = WebDriverWait(driver, 10)
            time.sleep(2)
            
            # Check if form is accepting responses
            page_source = driver.page_source.lower()
            if "no longer accepting" in page_source or "tidak menerima" in page_source:
                logger.error("❌ Form is no longer accepting responses")
                return False
            
            # Debug: Show what data was prefilled
            logger.info("📋 Data prefilled in URL:")
            for entry_name, value in list(form_data.items())[:5]:  # Show first 5 entries
                logger.info(f"  {entry_name}: {value}")
            if len(form_data) > 5:
                logger.info(f"  ... and {len(form_data) - 5} more entries")
            
            # Navigate through multi-section form (data already prefilled)
            section_num = 1
            max_sections = 20  # Safety limit
            
            while section_num <= max_sections:
                logger.info(f"📄 Navigating Section {section_num}")
                
                # Since data is prefilled, we just need to navigate
                
                # Look for next button
                next_button = self.find_next_button(driver)
                
                if next_button:
                    button_text = next_button.text.strip()
                    if 'berikutnya' in button_text.lower():
                        driver.execute_script("arguments[0].scrollIntoView();", next_button)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", next_button)
                        logger.info(f"  ➡️  Clicked Next button (Section {section_num})")
                        time.sleep(2)
                        section_num += 1
                    else:
                        break
                else:
                    # No next button, look for submit
                    logger.info("  🔍 Looking for submit button...")
                    submit_button = self.find_submit_button(driver)
                    
                    if submit_button:
                        logger.info(f"📤 Found submit button: '{submit_button.text}'")
                        driver.execute_script("arguments[0].scrollIntoView();", submit_button)
                        time.sleep(2)
                        driver.execute_script("arguments[0].click();", submit_button)
                        
                        # Wait for submission
                        time.sleep(5)
                        break
                    else:
                        logger.error("❌ No submit button found")
                        return False
            
            # Check submission results
            current_url = driver.current_url
            page_content = driver.page_source.lower()
            
            # Check for success indicators
            success_indicators = [
                "your response has been recorded",
                "thank you",
                "terima kasih",
                "response recorded",
                "submitted successfully"
            ]
            
            success_found = any(indicator in page_content for indicator in success_indicators)
            
            logger.info(f"📝 Data was prefilled from CSV")
            logger.info(f"📨 Final URL: {current_url}")
            
            if success_found:
                logger.info("✅ Form submitted successfully")
                return True
            else:
                logger.warning("⚠️ Submission status unclear, assuming success")
                return True
                
        except Exception as e:
            logger.error(f"❌ Selenium submission error: {e}")
            return False
            
        finally:
            if driver:
                driver.quit()