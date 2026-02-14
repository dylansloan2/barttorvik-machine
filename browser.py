from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import chromedriver_autoinstaller
import time
import logging
from pathlib import Path
from typing import Optional

class BrowserClient:
    def __init__(self, headless: bool = True, timeout: int = 30, screenshot_dir: Optional[Path] = None):
        self.headless = headless
        self.timeout = timeout
        self.screenshot_dir = screenshot_dir
        self.driver = None
        self.logger = logging.getLogger(__name__)
    
    def start(self):
        """Start the browser session"""
        try:
            # Install correct ChromeDriver automatically
            chromedriver_autoinstaller.install()
            
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            
            self.logger.info("Browser started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start browser: {e}")
            raise
    
    def stop(self):
        """Stop the browser session"""
        if self.driver:
            self.driver.quit()
            self.driver = None
            self.logger.info("Browser stopped")
    
    def get_page(self, url: str, wait_time: int = 3) -> bool:
        """Navigate to a URL and wait for page to load"""
        try:
            self.logger.info(f"Loading page: {url}")
            self.driver.get(url)
            time.sleep(wait_time)
            
            # Wait for page to be ready
            WebDriverWait(self.driver, self.timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            return True
            
        except TimeoutException:
            self.logger.error(f"Timeout loading page: {url}")
            if self.screenshot_dir:
                self.save_screenshot(f"timeout_{url.replace('/', '_')}")
            return False
        except WebDriverException as e:
            self.logger.error(f"WebDriver error loading {url}: {e}")
            if self.screenshot_dir:
                self.save_screenshot(f"error_{url.replace('/', '_')}")
            return False
    
    def save_screenshot(self, filename: str):
        """Save a screenshot for debugging"""
        if self.screenshot_dir:
            self.screenshot_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = self.screenshot_dir / f"{filename}.png"
            self.driver.save_screenshot(str(screenshot_path))
            self.logger.info(f"Screenshot saved: {screenshot_path}")
    
    def find_elements(self, by: By, value: str, timeout: int = 10):
        """Find elements with timeout"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_elements(by, value)
        except TimeoutException:
            self.logger.warning(f"Elements not found: {by}={value}")
            return []
    
    def find_element(self, by: By, value: str, timeout: int = 10):
        """Find single element with timeout"""
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((by, value))
            )
            return self.driver.find_element(by, value)
        except TimeoutException:
            self.logger.warning(f"Element not found: {by}={value}")
            return None
    
    def __enter__(self):
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
