"""Main module of BetBot"""
import os
import re
import time
import json
import logging
import requests
import tempfile
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    TimeoutException,
    WebDriverException
)
from colorama import Fore, Style, init

from config import (
    BROWSER_CONFIG,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    SITES,
    SELECTORS,
    TIMEOUTS,
    POPUP_SELECTORS
)
from src.handlers.web_element_handler import WebElementHandler
from src.utils.money_handler import MoneyHandler

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bet_bot.log")
    ]
)

class BetBot:
    def __init__(self):
        init(autoreset=True)
        self.driver = None
        self.logger = logging.getLogger(__name__)
        self.element_handler = None

    def start_driver(self):
        """Initializes the Edge driver with the appropriate settings"""
        try:
            user_data_dir = tempfile.mkdtemp()
            edge_options = Options()
            edge_options.add_argument(f"--user-data-dir={user_data_dir}")
            
            for key, value in BROWSER_CONFIG.items():
                if value:
                    edge_options.add_argument(f"--{key.replace('_', '-')}")
            
            service = Service("/usr/local/bin/chromedriver")
            self.driver = webdriver.Chrome(service=service, options=edge_options)
            self.driver.implicitly_wait(TIMEOUTS["element_wait"])
            self.element_handler = WebElementHandler(self.driver, self.logger)  # type: ignore
            self.logger.info("Driver configured successfully")
            return True
        except WebDriverException as e:
            self.logger.error(f"Error configuring driver: {e}")
            return False

    def _try_click(self, element, description="", use_js=False):
        """Attempts to click an element with JavaScript fallback"""
        return self.element_handler.click_element(element, description, use_js)

    def login(self, site):
        """Performs login on a specific site"""
        try:
            self.logger.info(f"Starting login at: {site['url']}" )
            self.driver.get(site["url"])
            time.sleep(1)  # Small pause for the initial page to load
            # First attempt: Find and click the login button
            login_buttons = self.element_handler.find_elements(By.CSS_SELECTOR, SELECTORS["login_button"])
            button_found = False
            for button in login_buttons:
                if button.is_displayed() and re.search(r"_btn_\w+_43", button.get_attribute("class")):
                    if self.element_handler.click_element(button, "login button", try_scroll=False):
                        self.logger.info("Login button clicked successfully")
                        button_found = True
                        time.sleep(1)  # Wait for the fields to appear
                        break
            if not button_found:
                self.logger.info("Login button not found, checking if fields are already visible...")
                # Checks if the fields are already visible even without clicking
                fields_visible = self.element_handler.check_visibility(
                    By.CSS_SELECTOR, 
                    SELECTORS["username_field"],
                    timeout=2
                )
                if not fields_visible:
                    self.logger.error("Neither login button nor fields were found")
                    return False
            # Now tries to fill in the fields
            if not self.element_handler.fill_field(
                By.CSS_SELECTOR, 
                SELECTORS["username_field"], 
                site["username"]
            ):
                raise Exception("Error filling username")
            if not self.element_handler.fill_field(
                By.CSS_SELECTOR, 
                SELECTORS["password_field"], 
                site["password"]
            ):
                raise Exception("Error filling password")
            if not self.element_handler.wait_and_click(
                By.CSS_SELECTOR, 
                SELECTORS["submit_button"], 
                "submit button"
            ):
                raise Exception("Error clicking submit button")
            time.sleep(1)  # Wait for login processing
            return True
        except Exception as e:
            self.logger.error(f"Error in login process: {e}")
            return False

    def handle_popups(self):
        """Handles different types of popups that may appear"""
        start_time = time.time()
        popups_closed = 0
        max_attempts = 3
        self.logger.info("Starting popup monitoring...")
        while time.time() - start_time < TIMEOUTS["popup_check"] and max_attempts > 0:
            popup_found = False
            for selector, description in POPUP_SELECTORS.items():
                try:
                    by_type = By.XPATH if selector.startswith('//') else By.CSS_SELECTOR
                    element = self.element_handler.wait_for_element_clickable(by_type, selector, timeout=3)
                    if not element:
                        continue
                    popup_found = True
                    if self._try_click(element, description):
                        popups_closed += 1
                        self.logger.info(f"{description} closed successfully")
                    elif self._try_click(element, description, use_js=True):
                        popups_closed += 1
                        self.logger.info(f"{description} closed via JavaScript")
                    else:
                        body = self.element_handler.find_elements(By.TAG_NAME, "body")
                        if body:
                            self._try_click(body[0], "page body")
                            self.logger.info("Attempted to close popup by clicking elsewhere")
                    time.sleep(1)
                except TimeoutException:
                    continue
                except Exception as e:
                    self.logger.warning(f"Error trying to close {description}: {e}")
                    continue
            if not popup_found:
                max_attempts -= 1
                self.logger.info(f"No popups found. Remaining attempts: {max_attempts}")
            if popups_closed > 0:
                time.sleep(2)
                popup_still_visible = False
                for selector in POPUP_SELECTORS:
                    by_type = By.XPATH if selector.startswith('//') else By.CSS_SELECTOR
                    if self.element_handler.check_visibility(by_type, selector, timeout=1):
                        popup_still_visible = True
                        break
                if not popup_still_visible:
                    break
        self.logger.info(f"Total of {popups_closed} popups closed")

    def collect_reward(self):
        """Collects the available reward"""
        try:
            attempts = 3
            for attempt in range(attempts):
                self.logger.info(f"Attempt {attempt + 1} to collect reward")
                element = self.element_handler.wait_for_element_clickable(
                    By.CSS_SELECTOR,
                    SELECTORS["main_button"],
                    timeout=5
                )
                if not element:
                    continue
                if self.element_handler.click_element(element, "main button"):
                    self.logger.info("Main button clicked successfully")
                    if self.element_handler.check_visibility(
                        By.CSS_SELECTOR,
                        SELECTORS["popup_block"],
                        timeout=2
                    ):
                        self.logger.warning("Package not collected due to block")
                        return False
                    try:
                        prize = self.element_handler.wait_for_element_present(
                            By.CSS_SELECTOR,
                            SELECTORS["prize_value"],
                            timeout=3
                        )
                        if prize:
                            self.logger.info(f"Prize collected: {prize.text}")
                            return True
                    except Exception:
                        pass
                    self.logger.info("Package appears to have been collected successfully")
                    return True
                time.sleep(1)
            self.logger.warning("Could not collect reward after all attempts")
            return False
        except Exception as e:
            self.logger.error(f"Error collecting reward: {e}")
            return False

    def capture_value(self):
        """Captures the current currency value"""
        try:
            element = self.element_handler.wait_for_element_present(
                By.XPATH,
                SELECTORS["currency_value"],
                timeout=10
            )
            if not element:
                self.logger.warning("Value element not found")
                return MoneyHandler.float_to_str(0)
            spans = element.find_elements(By.CSS_SELECTOR, "span[data-char]")
            if spans:
                value_text = "".join([(span.get_attribute("data-char") or "") for span in spans])
                if value_text.strip():
                    value_float = MoneyHandler.str_to_float(value_text)
                    return MoneyHandler.float_to_str(value_float)
            value_text = element.text
            if value_text.strip():
                value_float = MoneyHandler.str_to_float(value_text)
                return MoneyHandler.float_to_str(value_float)
            self.logger.warning("Could not capture value")
            return MoneyHandler.float_to_str(0)
        except Exception as e:
            self.logger.error(f"Error capturing value: {e}")
            return MoneyHandler.float_to_str(0)

    def save_value(self, url, value):
        """Saves the captured value to a JSON file"""
        file_name = "valores_sites.json"
        try:
            data = {"last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "sites": {}}
            
            if os.path.exists(file_name):
                with open(file_name, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    
            previous_value = data["sites"].get(url, {}).get("valor", None)
            changed = previous_value != value
            data["sites"][url] = {
                "valor": value,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            with open(file_name, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            return changed, previous_value
        except Exception as e:
            self.logger.error(f"Error saving value: {e}")
            return False, None

    def send_telegram(self, message):
        """Sends a message to the Telegram channel"""
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            response = requests.post(url, json=payload)
            if response.status_code != 200:
                raise requests.RequestException(f"Status code: {response.status_code}")
                
            self.logger.info("Message sent to Telegram successfully")
        except Exception as e:
            self.logger.error(f"Error sending Telegram message: {e}")

    def process_sites(self):
        """Processes all sites from the list"""
        self.send_telegram("<b>Starting site processing...</b>")
        consolidated_message = "<b>Value Report:</b>\n\n"
        
        for site in SITES:
            try:
                self.logger.info(f"Processing site: {site['url']}")
                
                if not self.login(site):
                    raise Exception("Login failed")
                    
                self.handle_popups()
                
                if not self.collect_reward():
                    self.logger.warning("Could not collect reward")
                
                value = self.capture_value()
                changed, previous_value = self.save_value(site["url"], value)
                
                if changed and previous_value:
                    difference = MoneyHandler.calcular_diferenca(previous_value, value)
                    consolidated_message += f"<b>Site:</b> {site['url']}\n<b>Value:</b> {value} ({difference})\n\n"
                else:
                    consolidated_message += f"<b>Site:</b> {site['url']}\n<b>Value:</b> {value}\n\n"
                    
            except Exception as e:
                self.logger.error(f"Error processing site {site['url']}: {e}")
                consolidated_message += f"<b>Site:</b> {site['url']}\n<b>Error:</b> {str(e)}\n\n"
            finally:
                time.sleep(TIMEOUTS["retry_interval"])
                
        self.send_telegram(consolidated_message)

    def run(self):
        """Main method that executes the entire process"""
        print(Fore.CYAN + r"""
                      _        _           
  _ __ ___   __ _  __| | ___  | |__  _   _ 
 | '_ ` _ \ / _` |/ _` |/ _ \ | '_ \| | | |
 | | | | | | (_| | (_| |  __/ | |_) | |_| |
 |_| |_| |_|\__,_|\__,_|\___| |_.__/ \__, |
                                     |___/ 

                .-') _       ) (`-.      
               ( OO ) )       ( OO ).    
   ,------.,--./ ,--,' ,-.-')(_/.  \_)-. 
('-| _.---'|   \ |  |\ |  |OO)\  `.'  /  
(OO|(_\    |    \|  | )|  |  \ \     /\  
/  |  '--. |  .     |/ |  |(_/  \   \ |  
\_)|  .--' |  |\    | ,|  |_.' .'    \_) 
  \|  |_)  |  | \   |(_|  |   /  .'.  \  
   `--'    `--'  `--'  `--'  '--'   '--' 
        """ + Style.RESET_ALL)

        try:
            if not self.start_driver():
                raise Exception("Failed to initialize driver")
                
            self.process_sites()
            self.logger.info("Processing completed successfully")
            
        except Exception as e:
            self.logger.error(f"Error during execution: {e}")
        finally:
            if self.driver:
                self.driver.quit()

if __name__ == "__main__":
    bot = BetBot()
    bot.run()
