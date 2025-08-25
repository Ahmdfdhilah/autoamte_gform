"""
Google Forms automation module using Selenium - Fixed for concurrency issues
"""

import logging
import time
import os
import tempfile
import uuid
import shutil
import atexit
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from ..utils.url_parser import extract_entry_order_from_url, generate_prefilled_url
from ..utils.field_analyzer import (
    analyze_field_types_from_url,
    generate_prefilled_url_with_types,
)
import pandas as pd

logger = logging.getLogger(__name__)


class GoogleFormAutomation:
    """Google Forms automation class using Selenium with improved concurrency handling"""

    def __init__(self, form_url: str, request_config: Dict = None):
        self.form_url = form_url
        self.entry_fields = []
        self.field_types = {}
        self.request_config = request_config or {}
        self.driver = None
        self.headless_mode = True  # Default to headless
        self.temp_dirs = []  # Track temp directories for cleanup
        self._register_cleanup()

    def _register_cleanup(self):
        """Register cleanup function to run on exit"""
        atexit.register(self._cleanup_temp_dirs)

    def _cleanup_temp_dirs(self):
        """Clean up temporary directories"""
        for temp_dir in self.temp_dirs:
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"🧹 Cleaned up temp directory: {temp_dir}")
            except Exception as e:
                logger.debug(f"Failed to cleanup temp directory {temp_dir}: {e}")

    def set_headless_mode(self, headless: bool):
        """Set headless mode for browser automation"""
        self.headless_mode = headless

    def extract_form_info(
        self, csv_headers: List[str] = None
    ) -> tuple[List[str], Optional[str]]:
        """Extract entry IDs from CSV headers or URL with field type analysis"""
        try:
            # If we have CSV headers, use them directly
            if csv_headers:
                entry_fields = []
                for header in csv_headers:
                    if header.startswith("entry."):
                        entry_fields.append(header)

                if entry_fields:
                    self.entry_fields = entry_fields
                    logger.info(
                        f"Using CSV headers: {len(entry_fields)} entry fields found"
                    )
                    # Analyze field types from URL for proper field handling
                    logger.info(f"🔍 Analyzing field types from form URL...")
                    try:
                        self.field_types = analyze_field_types_from_url(self.form_url)
                        logger.info(
                            f"Analyzed {len(self.field_types)} field types from URL"
                        )
                    except Exception as e:
                        logger.warning(f"Could not analyze field types: {e}")
                        self.field_types = {}
                    return self.entry_fields, self.form_url

            # Fallback to URL extraction
            entry_fields = extract_entry_order_from_url(self.form_url)
            self.entry_fields = entry_fields

            # Analyze field types from URL
            try:
                self.field_types = analyze_field_types_from_url(self.form_url)
                logger.info(f"Analyzed {len(self.field_types)} field types from URL")
            except Exception as e:
                logger.warning(f"Could not analyze field types: {e}")
                self.field_types = {}

            logger.info(f"Extracted {len(entry_fields)} entry fields from URL")
            return self.entry_fields, self.form_url

        except Exception as e:
            logger.error(f"Error extracting form info: {e}")
            return [], None

    def create_unique_temp_dir(self) -> str:
        """Create a unique temporary directory for Chrome user data"""
        # Use process ID and a unique ID for better collision avoidance
        pid = os.getpid()
        unique_id = str(uuid.uuid4())

        # Check for a dedicated temp directory from an environment variable first
        # This is the best practice for a server environment
        temp_base = os.getenv("CHROME_TEMP_DIR", tempfile.gettempdir())

        user_data_dir = os.path.join(temp_base, f"chrome_user_{pid}_{unique_id}")

        try:
            os.makedirs(user_data_dir, exist_ok=True)  # Use exist_ok=True to be safe
            self.temp_dirs.append(user_data_dir)
            logger.debug(f"✅ Successfully created unique temp dir: {user_data_dir}")
            return user_data_dir
        except Exception as e:
            logger.error(
                f"❌ CRITICAL: Failed to create temp directory at {user_data_dir}: {e}"
            )
            # If we can't create a temp directory, we should not proceed with user-data-dir
            return None

    def setup_driver(self, headless: bool = True) -> webdriver.Chrome:
        """Setup Chrome driver with improved concurrency handling"""
        chrome_options = Options()

        # Create unique user data directory with better collision avoidance
        try:
            user_data_dir = self.create_unique_temp_dir()
            if user_data_dir:
                chrome_options.add_argument(f"--user-data-dir={user_data_dir}")
                logger.debug(f"📁 Using unique temp dir: {user_data_dir}")
            else:
                logger.warning(
                    "⚠️ Could not create a unique temp directory. Proceeding without --user-data-dir."
                )
        except Exception as e:
            logger.warning(
                f"Failed to create temp dir: {e}, proceeding without --user-data-dir"
            )

        # Core headless and sandbox options
        if headless:
            chrome_options.add_argument(
                "--headless=new"
            )  # Gunakan mode headless baru yang lebih stabil
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument('--lang=id-ID')  # Force Indonesian

        # Window and display options
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--start-maximized")

        # User agent to avoid detection
        chrome_options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36"
        )

        # Enhanced stability options for concurrent usage
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-client-side-phishing-detection")
        chrome_options.add_argument("--disable-crash-reporter")
        chrome_options.add_argument("--disable-oopr-debug-crash-dump")
        chrome_options.add_argument("--no-crash-upload")
        chrome_options.add_argument("--disable-low-res-tiling")

        # Memory optimization
        chrome_options.add_argument("--memory-pressure-off")
        chrome_options.add_argument("--max_old_space_size=4096")

        # Better concurrency handling
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--metrics-recording-only")
        chrome_options.add_argument("--no-first-run")
        chrome_options.add_argument("--disable-gpu-sandbox")

        # Use random port to avoid conflicts between concurrent instances
        import random

        debug_port = random.randint(9222, 9922)
        chrome_options.add_argument(f"--remote-debugging-port={debug_port}")

        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=TranslateUI")
        chrome_options.add_argument("--disable-ipc-flooding-protection")

        # Additional concurrency improvements
        chrome_options.add_argument("--disable-shared-memory")
        chrome_options.add_argument("--disable-software-rasterizer")
        chrome_options.add_argument("--disable-threaded-compositing")
        chrome_options.add_argument("--disable-threaded-scrolling")

        # Additional Chrome flags to prevent warnings and conflicts
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")

        # Logging options to reduce console noise
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])

        # Prefs to disable various Chrome features that might cause warnings
        prefs = {
            "profile.default_content_setting_values": {
                "notifications": 2,
                "geolocation": 2,
            },
            "profile.default_content_settings.popups": 0,
            "profile.managed_default_content_settings.images": 2,
            "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,
        }
        chrome_options.add_experimental_option("prefs", prefs)

        # Service configuration
        # Hapus executable_path agar Selenium mencarinya secara otomatis
        service = Service()

        try:
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            headless_msg = "headless" if headless else "visible"
            logger.info(
                f"✅ Chrome driver initialized successfully ({headless_msg}, port: {debug_port})"
            )
            return driver

        except Exception as e:
            logger.error(f"❌ Failed to initialize Chrome driver: {e}")
            if "user data directory is already in use" in str(e):
                logger.error("💡 Concurrency issue detected.")
                try:
                    import subprocess

                    subprocess.run(["pkill", "-f", "chrome"], capture_output=True)
                    logger.info("🔄 Attempted to kill orphaned Chrome processes")
                except:
                    pass
            logger.info(
                "💡 Make sure chromedriver is in your PATH or specify the full path"
            )
            raise

    def cleanup_driver(self, driver):
        """Properly cleanup driver and temp directories"""
        if driver:
            try:
                driver.quit()
                logger.debug("🚪 Browser closed")
            except Exception as e:
                logger.debug(f"Error closing browser: {e}")

        # Clean up temp directories immediately
        self._cleanup_temp_dirs()
        self.temp_dirs.clear()

    def fill_field_if_present(self, driver, entry_name: str, value: str) -> bool:
        """Fill field if present in current section with intelligent field matching"""
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
                # Try to select by value first, then by visible text
                try:
                    select.select_by_value(value)
                    logger.debug(f"    ✅ Select {entry_name}: {value} (by value)")
                    return True
                except:
                    # Try to find option by partial text match
                    options = select.options
                    for option in options:
                        if (
                            value.lower() in option.text.lower()
                            or option.text.lower() in value.lower()
                        ):
                            select.select_by_visible_text(option.text)
                            logger.debug(
                                f"    ✅ Select {entry_name}: {option.text} (matched {value})"
                            )
                            return True

        except NoSuchElementException:
            # Field not in current section, try intelligent fallback
            # Look for similar field names or try to match with visible selects
            try:
                visible_selects = driver.find_elements(By.CSS_SELECTOR, "select")
                for sel in visible_selects:
                    options = sel.find_elements(By.TAG_NAME, "option")
                    for opt in options:
                        if (
                            value.lower() in opt.text.lower()
                            or opt.text.lower() in value.lower()
                        ):
                            logger.debug(
                                f"    💡 Found match in unlabeled select: '{opt.text}' for '{value}'"
                            )
                            sel.click()
                            opt.click()
                            logger.debug(f"    ✅ Selected: {opt.text}")
                            return True
            except Exception as e:
                logger.debug(
                    f"    ❌ Intelligent fallback failed for {entry_name}: {e}"
                )
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
                "//*[contains(text(), 'Next')]",
            ]

            for xpath in xpath_selectors:
                elements = driver.find_elements(By.XPATH, xpath)
                for elem in elements:
                    text = elem.text.strip().lower()
                    if (
                        ("berikutnya" in text or "next" in text)
                        and "kembali" not in text
                        and elem.is_displayed()
                    ):
                        return elem

            button_elements = driver.find_elements(
                By.CSS_SELECTOR, ".NPEfkd.RveJvd.snByac, .l4V7wb.Fxmcue"
            )
            for elem in button_elements:
                text = elem.text.strip().lower()
                if (
                    ("berikutnya" in text or "next" in text)
                    and "kembali" not in text
                    and elem.is_displayed()
                ):
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
                "//div[contains(text(), 'Kirim')]",
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
                "span[role='button']",
            ]

            for selector in css_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    text = elem.text.lower()
                    if ("kirim" in text or "submit" in text) and elem.is_displayed():
                        return elem
        except:
            pass

        # Strategy 3: Parent elements of Kirim spans
        try:
            kirim_spans = driver.find_elements(
                By.XPATH, "//span[contains(text(), 'Kirim')]"
            )
            for span in kirim_spans:
                parent = span.find_element(By.XPATH, "..")
                if parent.is_displayed() and parent.is_enabled():
                    return parent
        except:
            pass

        return None

    def submit_form(self, form_data: Dict) -> bool:
        """Submit form using Selenium with advanced multi-section navigation and improved error handling"""
        driver = None
        try:
            logger.info("🔄 Starting advanced Selenium form submission")
            logger.info(f"📊 Form data: {len(form_data)} fields to fill")

            # Clean form data: normalize multiple spaces to single space and strip
            cleaned_form_data = {}
            for key, value in form_data.items():
                if pd.notna(value) and str(value).strip():
                    cleaned_value = " ".join(str(value).strip().split())

                    # Remove .0 from float numbers (e.g., 9.0 -> 9, but keep 9.5 as 9.5)
                    try:
                        # Check if it's a number that ends with .0
                        if (
                            "." in cleaned_value
                            and cleaned_value.replace(".", "")
                            .replace("-", "")
                            .isdigit()
                        ):
                            float_val = float(cleaned_value)
                            if float_val.is_integer():
                                cleaned_value = str(int(float_val))
                    except ValueError:
                        # Not a number, keep as is
                        pass

                    cleaned_form_data[key] = cleaned_value

            logger.info(
                f"📊 Cleaned form data: {len(cleaned_form_data)} non-empty fields"
            )

            # Setup driver with current headless setting
            driver = self.setup_driver(headless=self.headless_mode)
            headless_msg = "headless" if self.headless_mode else "visible browser"
            logger.info(f"🌐 Chrome driver initialized ({headless_msg})")

            # Generate prefilled URL with field type awareness
            entry_order = extract_entry_order_from_url(self.form_url)
            if self.field_types:
                prefilled_url = generate_prefilled_url_with_types(
                    self.form_url, entry_order, cleaned_form_data, self.field_types
                )
                logger.info("✅ Using advanced URL generation with field types")
                logger.info(prefilled_url)
            else:
                prefilled_url = generate_prefilled_url(
                    self.form_url, entry_order, cleaned_form_data
                )
                logger.info("✅ Using standard URL generation")

            logger.debug(
                f"📋 Generated prefilled URL (truncated): {prefilled_url[:150]}..."
            )

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

            # Get page title for debugging
            title = driver.title
            logger.info(f"📄 Page title: {title}")

            # Show field type analysis if available
            if self.field_types:
                type_counts = {}
                for info in self.field_types.values():
                    field_type = info["type"]
                    type_counts[field_type] = type_counts.get(field_type, 0) + 1

                logger.info("📊 Field types found:")
                for field_type, count in type_counts.items():
                    logger.info(f"  - {field_type}: {count} fields")

            # Navigate through multi-section form with enhanced error handling
            section_num = 1
            max_sections = 20  # Safety limit

            logger.info(f"🔍 Data is prefilled, now navigating through sections...")

            while section_num <= max_sections:
                logger.info(f"\n📄 Navigating Section {section_num}")

                # Check how many fields are visible in current section
                current_inputs = driver.find_elements(
                    By.CSS_SELECTOR, "input[name^='entry.']"
                )
                current_textareas = driver.find_elements(
                    By.CSS_SELECTOR, "textarea[name^='entry.']"
                )
                current_selects = driver.find_elements(
                    By.CSS_SELECTOR, "select[name^='entry.']"
                )

                # Count fields that actually have values
                filled_count = sum(
                    [
                        len(
                            [
                                inp
                                for inp in current_inputs
                                if inp.get_attribute("value")
                            ]
                        ),
                        len(
                            [
                                ta
                                for ta in current_textareas
                                if ta.get_attribute("value")
                            ]
                        ),
                        len(
                            [
                                sel
                                for sel in current_selects
                                if sel.get_attribute("value")
                            ]
                        ),
                    ]
                )

                total_current_fields = (
                    len(current_inputs) + len(current_textareas) + len(current_selects)
                )
                logger.info(
                    f"  📊 Current section: {total_current_fields} fields ({filled_count} filled)"
                )

                # Check for missing fields that should be here but aren't visible
                section_entries = (
                    [inp.get_attribute("name") for inp in current_inputs]
                    + [ta.get_attribute("name") for ta in current_textareas]
                    + [sel.get_attribute("name") for sel in current_selects]
                )

                expected_data_here = {
                    k: v for k, v in cleaned_form_data.items() if k in section_entries
                }
                if expected_data_here:
                    logger.debug(
                        f"  💡 Expected data for this section: {list(expected_data_here.keys())[:5]}..."
                    )

                # Look for missing fields and try manual filling
                missing_fields = {}
                for entry_key, value in cleaned_form_data.items():
                    if entry_key not in section_entries:
                        base_entry = entry_key.replace("_sentinel", "")
                        sentinel_exists = any(
                            base_entry + "_sentinel" in name for name in section_entries
                        )
                        if sentinel_exists:
                            missing_fields[entry_key] = value

                if missing_fields:
                    logger.info(
                        f"  ⚠️  Found {len(missing_fields)} missing fields, attempting manual fill..."
                    )

                    filled_manually = 0
                    for entry_key, value in missing_fields.items():
                        if self.fill_field_if_present(driver, entry_key, value):
                            filled_manually += 1

                    if filled_manually > 0:
                        logger.info(
                            f"  ✅ Manually filled {filled_manually} additional fields"
                        )

                # Look for next button
                next_button = self.find_next_button(driver)

                if next_button:
                    button_text = next_button.text.strip()
                    logger.info(f"  ➡️  Found 'Berikutnya' button: '{button_text}'")

                    if "berikutnya" in button_text.lower():
                        driver.execute_script(
                            "arguments[0].scrollIntoView();", next_button
                        )
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", next_button)
                        logger.info("  ✅ Clicked Next button")
                        time.sleep(2)
                        section_num += 1
                    else:
                        logger.info(
                            f"  ⚠️  Button text '{button_text}' is not 'Berikutnya', looking for submit..."
                        )
                        break
                else:
                    # No next button, look for submit
                    logger.info("  🔍 Looking for submit button...")
                    submit_button = self.find_submit_button(driver)

                    if submit_button:
                        logger.info(
                            f"📤 Found submit button: '{submit_button.text}' | Tag: {submit_button.tag_name}"
                        )
                        driver.execute_script(
                            "arguments[0].scrollIntoView();", submit_button
                        )
                        time.sleep(2)

                        logger.info("📤 Submitting form...")
                        driver.execute_script("arguments[0].click();", submit_button)

                        # Wait for submission
                        logger.info("⏳ Waiting for submission response...")
                        time.sleep(5)
                        break
                    else:
                        logger.error("❌ No submit button found after all strategies!")
                        return False

            # Safety check for infinite loop
            if section_num > max_sections:
                logger.warning(
                    f"⚠️  Reached maximum sections ({max_sections}), stopping to prevent infinite loop"
                )

            logger.info(
                f"📝 Form navigation completed through {section_num - 1} sections"
            )

            # Check submission results
            current_url = driver.current_url
            page_title = driver.title
            page_content = driver.page_source.lower()

            logger.info(f"📨 After submission:")
            logger.info(f"  Current URL: {current_url}")
            logger.info(f"  Page title: {page_title}")

            # Check for success indicators
            success_indicators = [
                "your response has been recorded",
                "thank you",
                "terima kasih",
                "response recorded",
                "submitted successfully",
            ]

            success_found = any(
                indicator in page_content for indicator in success_indicators
            )

            # Check for error indicators
            error_indicators = ["required", "error", "invalid", "wajib", "gagal"]

            error_found = any(
                indicator in page_content for indicator in error_indicators
            )

            logger.info(f"  ✅ Success indicators: {success_found}")
            logger.info(f"  ❌ Error indicators: {error_found}")

            if success_found:
                logger.info("🎉 Form submitted successfully!")
                logger.info("👀 Check your Google Sheets for the data")
                return True
            elif error_found:
                logger.warning("⚠️  Errors detected in submission")
                return False
            else:
                logger.info("❓ Submission status unclear")
                logger.info("💾 Check Google Sheets manually")
                return True

        except Exception as e:
            logger.error(f"❌ Selenium submission error: {e}")

            # Enhanced error handling for common concurrency issues
            if "session not created" in str(e):
                logger.error(
                    "🔧 Session creation failed - this might be a concurrency issue"
                )
                logger.error("💡 Try running instances with a delay between them")

            return False

        finally:
            # Enhanced cleanup
            self.cleanup_driver(driver)
