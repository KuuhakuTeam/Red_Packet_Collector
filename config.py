# Configuration file for the web automation script


# Telegram configuration
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Browser configuration options
BROWSER_CONFIG = {
    "headless": False,        # Run browser in headless mode
    "disable_gpu": False,     # Disable GPU hardware acceleration
    "no_sandbox": False,      # Disable sandbox mode
    "disable_dev_shm": False  # Disable /dev/shm usage
}

# List of sites to process with their credentials
SITES = [
    {"url": "hrl_here", "username": "username_here", "password": "password_here"},
]

# Web element selectors for different pages
SELECTORS = {
    "login_button": "div[class*='lobby-image']",                  # Login button selector
    "username_field": "input[data-input-name='account']",         # Username input field
    "password_field": "input[data-input-name='userpass']",        # Password input field
    "submit_button": "div.ui-badge__wrapper button.ui-button.ui-button--primary.ui-button--normal.ui-button--block",  # Submit button
    "main_button": "div.redpocket-collet-normal",                 # Main action button
    "currency_value": "//*[starts-with(@class, '_currency-count_')]",  # Currency value display
    "prize_value": "div._pocket_r2902_51 div.prize span",        # Prize value display
    "popup_block": "div.ui-popup.ui-popup--center.safe-area-top.safe-area-bottom.ui-dialog"  # Popup blocker
}

# Timeout settings for various operations
TIMEOUTS = {
    "page_load": 30,        # Maximum time to wait for page load
    "element_wait": 10,     # Default wait time for elements
    "popup_check": 40,      # Time to check for popups
    "retry_interval": 2     # Interval between retries
}

# Selectors for different types of popups
POPUP_SELECTORS = {
    "i.ui-dialog-close-box__icon": "Standard popup",
    "i.ui-dialog-close-box__icon svg": "SVG popup",
    "//div[@class='ui-button__content']//span[text()='Cancelar']": "Cancel button popup",
    "i.ui-dialog-close-box__icon[style*='display: inline-flex']": "Inline flex popup"
}
