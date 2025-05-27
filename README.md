# BetBot

A Python automation bot for collecting data and red packets from betting websites automatically.

## Features

- Automated login to multiple betting sites
- Automated reward collection
- Currency value tracking
- Telegram notifications
- Scheduled executions
- Robust popup handling
- Smart element handling with multiple retry strategies
- Detailed logging

## Requirements

- Python 3.9+
- Microsoft Edge WebDriver
- Dependencies listed in requirements.txt

## Configuration

The bot is configured through `config.py`:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Target Telegram chat ID
- `BROWSER_CONFIG`: Edge browser configuration settings
- `SITES`: List of sites with their credentials
- `SELECTORS`: CSS/XPath selectors for web elements
- `TIMEOUTS`: Various timeout settings
- `POPUP_SELECTORS`: Selectors for handling different types of popups

## Project Structure

```
bet_share/
├── config.py           # Configuration settings
├── main.py            # Main script with scheduler
├── src/
│   ├── betbot.py      # Core bot implementation
│   ├── handlers/
│   │   └── web_element_handler.py  # Web element interaction handler
│   └── utils/
│       └── money_handler.py        # Currency value handling utilities
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Configure `config.py` with your settings
4. Make sure you have Microsoft Edge WebDriver installed

## Usage

Run the bot with:

```bash
python main.py
```

The bot will automatically run every 2 hours according to the schedule in `main.py`.

## Technical Details

### BetBot Class
Main bot class that handles:
- Browser initialization
- Site login
- Popup management
- Reward collection
- Value tracking
- Telegram notifications

### WebElementHandler Class
Handles all web element interactions with:
- Smart element detection
- Multiple retry strategies
- Stale element handling
- Popup management
- Form filling

### MoneyHandler Class
Handles currency operations:
- String to float conversion
- Float to string formatting
- Value difference calculation

## Error Handling

The bot includes comprehensive error handling:
- Selenium exceptions
- Network issues
- Invalid elements
- Login failures
- Browser crashes

## Logging

Detailed logging is available in `bet_bot.log` and console output
