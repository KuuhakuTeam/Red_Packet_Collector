"""Module for handling web elements with robust handling of stale elements and popups"""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
from config import TIMEOUTS

class WebElementHandler:
    """Class to manage web elements with robust detection and state verification"""
    
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        self.default_timeout = TIMEOUTS["element_wait"]

    def wait_for_element_present(self, by, selector, timeout=None):
        """Waits until an element is present in the DOM
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            timeout: Custom timeout in seconds
            
        Returns:
            WebElement or None if not found
        """
        timeout = timeout or self.default_timeout
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, selector))
            )
        except TimeoutException:
            self.logger.warning(f"Element not found (present): {selector}")
            return None

    def wait_for_element_visible(self, by, selector, timeout=None):
        """Waits until an element is visible on the page
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            timeout: Custom timeout in seconds
            
        Returns:
            WebElement or None if not found
        """
        timeout = timeout or self.default_timeout
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, selector))
            )
        except TimeoutException:
            self.logger.warning(f"Element not found (visible): {selector}")
            return None

    def wait_for_element_clickable(self, by, selector, timeout=None):
        """Waits until an element is clickable
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            timeout: Custom timeout in seconds
            
        Returns:
            WebElement or None if not found
        """
        timeout = timeout or self.default_timeout
        try:
            return WebDriverWait(self.driver, timeout).until(
                EC.element_to_be_clickable((by, selector))
            )
        except TimeoutException:
            self.logger.warning(f"Element not found (clickable): {selector}")
            return None

    def find_elements(self, by, selector):
        """Finds all elements matching the selector
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            
        Returns:
            list: List of WebElements found
        """
        try:
            elements = self.driver.find_elements(by, selector)
            if not elements:
                self.logger.warning(f"No elements found: {selector}")
            return elements
        except Exception as e:
            self.logger.error(f"Error finding elements: {e}")
            return []    
        
    def click_element(self, element, description="", use_js=False, try_scroll=True):
        """Tries to click an element with multiple strategies and stale element handling
        
        Args:
            element: WebElement to click
            description: Element description for logging
            use_js: Whether to use JavaScript click
            try_scroll: Whether to try scrolling to element
            
        Returns:
            bool: Whether click was successful
        """
        try:
            new_element = element
            if not self.element_exists(element):
                self.logger.info(f"Element {description} is stale, trying to recover...")
                try:
                    by = None
                    selector = None
                    
                    element_id = element.get_attribute("id")
                    if element_id:
                        by = By.ID
                        selector = element_id
                    
                    if not by:
                        class_name = element.get_attribute("class")
                        if class_name:
                            by = By.CLASS_NAME
                            selector = class_name.split()[0]
                    
                    if by and selector:
                        new_element = self.ensure_valid_element(by, selector, element, description)
                    
                    if not new_element:
                        new_element = self.find_similar_element(element, description)

                    if not new_element:
                        return False
                        
                    element = new_element

                except Exception as e:
                    self.logger.warning(f"Could not recover element: {e}")
                    return False

            if try_scroll:
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});",
                        element
                    )
                    time.sleep(0.1)
                except Exception:
                    pass

            for attempt in range(3):
                try:
                    if use_js or attempt > 0:
                        self.driver.execute_script("arguments[0].click();", element)
                    else:
                        self.driver.execute_script("""
                            const element = arguments[0];
                            const rect = element.getBoundingClientRect();
                            const elements = document.elementsFromPoint(
                                rect.x + rect.width/2,
                                rect.y + rect.height/2
                            );
                            for (const e of elements) {
                                if (e !== element && e.style.pointerEvents !== 'none') {
                                    e.style.pointerEvents = 'none';
                                }
                            }
                        """, element)
                        element.click()
                    return True

                except ElementClickInterceptedException:
                    try:
                        self.driver.execute_script("""
                            const element = arguments[0];
                            const events = ['mousedown', 'mouseup', 'click'];
                            events.forEach(eventName => {
                                element.dispatchEvent(new MouseEvent(eventName, {
                                    view: window,
                                    bubbles: true,
                                    cancelable: true,
                                    buttons: 1
                                }));
                            });
                        """, element)
                        return True
                    except Exception:
                        time.sleep(0.2)
                        continue

                except Exception as e:
                    if "stale element reference" in str(e):
                        time.sleep(0.2)
                        if not self.element_exists(element):
                            break
                    else:
                        break

            return False

        except Exception as e:
            self.logger.warning(f"Error clicking {description}: {e}")
            return False

    def wait_and_click(self, by, selector, description="", timeout=None, use_js=False):
        """Waits for an element and tries to click it
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            description: Element description for logging
            timeout: Custom timeout in seconds
            use_js: Whether to use JavaScript click
            
        Returns:
            bool: Whether click was successful
        """
        element = self.wait_for_element_clickable(by, selector, timeout)
        if element:
            return self.click_element(element, description, use_js)
        return False

    def fill_field(self, by, selector, text, clear=True):
        """Fills a text field with verification and multiple attempts
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            text: Text to enter
            clear: Whether to clear field first
            
        Returns:
            bool: Whether field was filled successfully
        """
        try:
            element = self.wait_for_element_visible(by, selector)
            if not element or not self.element_exists(element):
                element = self.ensure_valid_element(by, selector, element, selector)
                if not element:
                    self.logger.warning(f"Field not found or no longer exists: {selector}")
                    return False

            if not element.is_enabled():
                self.logger.warning(f"Field is disabled: {selector}")
                try:
                    self.driver.execute_script("""
                        arguments[0].removeAttribute('disabled');
                        arguments[0].removeAttribute('readonly');
                    """, element)
                except Exception as e:
                    self.logger.warning(f"Could not enable field: {e}")
                    return False

            try:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'instant', block: 'center'});", element)
                self.driver.execute_script("arguments[0].focus();", element)
                time.sleep(0.1)
            except Exception as e:
                self.logger.warning(f"Error focusing/scrolling field: {e}")

            if clear:
                try:
                    if element.is_enabled() and element.is_displayed():
                        element.clear()
                        element.send_keys("")
                    else:
                        raise Exception("Field not interactive for clear(). Trying via JS.")
                except Exception as e:
                    self.logger.warning(f"Error clearing field: {e} (trying via JS)")
                    try:
                        self.driver.execute_script("arguments[0].value = '';", element)
                    except Exception as e2:
                        self.logger.warning(f"Error clearing field via JS: {e2}")

            attempts = 3
            while attempts > 0:
                try:
                    element.send_keys(text)
                    current_value = element.get_attribute("value")
                    if current_value == text:
                        return True

                    self.driver.execute_script(
                        "arguments[0].value = arguments[1];",
                        element,
                        text
                    )
                    self.driver.execute_script("""
                        const element = arguments[0];
                        const text = arguments[1];
                        element.value = text;
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                    """, element, text)
                    current_value = element.get_attribute("value")
                    if current_value == text:
                        return True
                except Exception as e:
                    self.logger.warning(f"Attempt {4-attempts} to fill field failed: {e}")
                attempts -= 1
                time.sleep(0.5)

            self.logger.warning(f"Could not fill field {selector}")
            return False

        except Exception as e:
            self.logger.error(f"Error filling field: {e}")
            return False

    def check_visibility(self, by, selector, timeout=3):
        """Checks if an element is visible without waiting too long
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            timeout: Custom timeout in seconds
            
        Returns:
            bool: Whether element is visible
        """
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located((by, selector))
            )
            return True
        except TimeoutException:
            return False

    def find_similar_element(self, original_element, description=""):
        """Tries to find a similar element to the original using different strategies
        
        Args:
            original_element: Original WebElement
            description: Element description for logging
            
        Returns:
            WebElement or None if not found
        """
        try:
            element_id = original_element.get_attribute("id")
            if element_id:
                element = self.driver.find_element(By.ID, element_id)
                if element.is_displayed() and element.is_enabled():
                    return element

            class_name = original_element.get_attribute("class")
            if class_name:
                classes = class_name.split()
                for class_name in classes:
                    elements = self.driver.find_elements(By.CLASS_NAME, class_name)
                    for element in elements:
                        if element.is_displayed() and element.is_enabled():
                            return element

            text = original_element.text
            if text:
                xpath = f"//*[contains(text(), '{text}')]"
                elements = self.driver.find_elements(By.XPATH, xpath)
                for element in elements:
                    if element.is_displayed() and element.is_enabled():
                        return element

            tag_name = original_element.tag_name
            if tag_name:
                elements = self.driver.find_elements(By.TAG_NAME, tag_name)
                for element in elements:
                    if (element.get_attribute("type") == original_element.get_attribute("type")
                        and element.get_attribute("name") == original_element.get_attribute("name")
                        and element.is_displayed()
                        and element.is_enabled()):
                        return element

            return None

        except Exception as e:
            self.logger.warning(f"Error finding similar element for {description}: {e}")
            return None

    def element_exists(self, element):
        """Checks if an element still exists on the page
        
        Args:
            element: WebElement to check
            
        Returns:
            bool: Whether element exists
        """
        try:
            if not element:
                return False
            element.is_enabled()
            return True
        except Exception:
            return False

    def wait_for_popup_disappear(self, by, selector, timeout=5):
        """Waits until a popup disappears from the page
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            timeout: Custom timeout in seconds
            
        Returns:
            bool: Whether popup disappeared
        """
        try:
            return WebDriverWait(self.driver, timeout).until_not(
                EC.presence_of_element_located((by, selector))
            )
        except TimeoutException:
            return False

    def handle_popup(self, by, selector, description="popup", timeout=None):
        """Handles a popup using multiple strategies
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            description: Popup description for logging
            timeout: Custom timeout in seconds
            
        Returns:
            bool: Whether popup was handled successfully
        """
        try:
            close_buttons = self.driver.find_elements(By.XPATH, 
                "//*[contains(@class, 'close') or contains(@class, 'dismiss') or "
                "contains(@class, 'fechar') or contains(@id, 'close') or "
                "contains(@id, 'fechar') or contains(@title, 'Close') or "
                "contains(text(), '×') or contains(text(), 'x')]"
            )
            
            for button in close_buttons:
                try:
                    if button.is_displayed() and button.is_enabled():
                        if self.click_element(button, f"close button {description}", use_js=True):
                            time.sleep(0.5)
                            if not self.check_visibility(by, selector, 1):
                                return True
                except Exception:
                    continue

            popup = self.wait_for_element_clickable(by, selector, timeout)
            if popup:
                if self.click_element(popup, description, use_js=True):
                    time.sleep(0.5)
                    if not self.check_visibility(by, selector, 1):
                        return True

                try:
                    self.driver.execute_script("arguments[0].remove();", popup)
                    time.sleep(0.5)
                    if not self.check_visibility(by, selector, 1):
                        return True
                except Exception:
                    pass

            self.driver.execute_script("""
                document.querySelectorAll('body > div').forEach(div => {
                    const style = window.getComputedStyle(div);
                    if (style.position === 'fixed' || style.position === 'absolute') {
                        if (style.zIndex > 1000 || style.backgroundColor.includes('rgba(0, 0, 0')
                            || div.className.toLowerCase().includes('overlay')
                            || div.className.toLowerCase().includes('modal')) {
                            div.remove();
                        }
                    }
                });
            """)

            return not self.check_visibility(by, selector, 1)

        except Exception as e:
            self.logger.error(f"Error handling {description}: {e}")
            return False

    def ensure_valid_element(self, by, selector, element, description="", timeout=None):
        """Ensures an element is valid, trying to recover it if necessary
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            element: WebElement to check
            description: Element description for logging
            timeout: Custom timeout in seconds
            
        Returns:
            WebElement or None if not recoverable
        """
        if self.element_exists(element):
            return element

        self.logger.info(f"Trying to recover element {description}...")
        
        for strategy in [
            self.wait_for_element_present,
            self.wait_for_element_visible,
            self.wait_for_element_clickable
        ]:
            try:
                new_element = strategy(by, selector, timeout)
                if new_element and self.element_exists(new_element):
                    return new_element
            except Exception:
                continue

        try:
            return self.find_similar_element(element, description)
        except Exception:
            return None

    def fill_masked_field(self, by, selector, text, mask=None):
        """Fills a field that has an input mask
        
        Args:
            by: Selenium By locator strategy
            selector: Element selector
            text: Text to enter
            mask: Optional mask pattern
            
        Returns:
            bool: Whether field was filled successfully
        """
        try:
            element = self.wait_for_element_visible(by, selector)
            if not element or not self.element_exists(element):
                self.logger.warning(f"Masked field not found: {selector}")
                return False

            self.driver.execute_script("""
                const element = arguments[0];
                const originalProto = Element.prototype;
                const origAddEventListener = originalProto.addEventListener;
                element.addEventListener = function(type, listener, options) {
                    if (type === 'input' || type === 'keydown' || type === 'keyup' || type === 'keypress') {
                        return;
                    }
                    return origAddEventListener.call(this, type, listener, options);
                };
            """, element)

            try:
                element.clear()
                self.driver.execute_script("arguments[0].value = '';", element)
            except Exception:
                pass

            if mask and any(c in mask for c in "0123456789"):
                text = ''.join(c for c in text if c.isdigit())

            for char in text:
                element.send_keys(char)
                time.sleep(0.05)

            current_value = element.get_attribute("value")
            if current_value and (text in current_value or current_value in text):
                return True

            self.driver.execute_script(
                "arguments[0].value = arguments[1];",
                element,
                text
            )

            self.driver.execute_script("""
                const element = arguments[0];
                ['change', 'input', 'blur'].forEach(eventName => {
                    element.dispatchEvent(new Event(eventName, { bubbles: true }));
                });
            """, element)

            return True

        except Exception as e:
            self.logger.error(f"Error filling masked field: {e}")
            return False
