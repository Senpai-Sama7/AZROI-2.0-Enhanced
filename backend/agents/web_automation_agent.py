import logging
import os
import time
from typing import List, Dict, Optional, Union, Tuple, Any
from selenium import webdriver  # type: ignore
from selenium.webdriver.firefox.options import Options  # type: ignore
from selenium.webdriver.common.by import By  # type: ignore
from selenium.webdriver.firefox.service import Service  # type: ignore
from selenium.webdriver.support.ui import WebDriverWait  # type: ignore
from selenium.webdriver.support import expected_conditions as EC  # type: ignore
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException  # type: ignore
from selenium.webdriver.common.action_chains import ActionChains  # type: ignore
from selenium.webdriver.common.keys import Keys  # type: ignore
from webdriver_manager.firefox import GeckoDriverManager  # type: ignore

class WebAutomationAgent:
    """
    Agent for automating web browser tasks using Selenium and Firefox.
    Supports headless and visible modes, wait mechanisms, and advanced web interactions.
    """
    def __init__(self, headless: bool = True, implicit_wait: int = 10, screenshot_dir: str = "./screenshots"):
        self.logger = logging.getLogger("WebAutomationAgent")
        options = Options()
        if headless:
            options.add_argument("-headless")
        
        # Additional Firefox options for better performance and stability
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        self.screenshot_dir = screenshot_dir
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)
            
        try:
            service = Service(GeckoDriverManager().install())
            self.driver = webdriver.Firefox(service=service, options=options)
            self.driver.implicitly_wait(implicit_wait)
            self.logger.info("WebAutomationAgent initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {e}")
            raise

    def open_url(self, url: str) -> bool:
        """
        Opens a URL in the browser.
        
        Args:
            url: The URL to open
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Opening URL: {url}")
            self.driver.get(url)
            return True
        except WebDriverException as e:
            self.logger.error(f"Failed to open URL {url}: {e}")
            return False

    def wait_for_element(self, by: str, value: str, timeout: int = 10) -> bool:
        """
        Waits for an element to be present on the page.
        
        Args:
            by: Locator strategy (e.g., 'id', 'xpath', 'css_selector')
            value: Locator value
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if element found within timeout, False otherwise
        """
        try:
            self.logger.info(f"Waiting for element by {by}: {value}")
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located((getattr(By, by.upper()), value))
            )
            return True
        except TimeoutException:
            self.logger.warning(f"Timed out waiting for element by {by}: {value}")
            return False

    def click_element(self, by: str, value: str, wait_time: int = 10) -> bool:
        """
        Clicks on an element after waiting for it to be clickable.
        
        Args:
            by: Locator strategy
            value: Locator value
            wait_time: Time to wait for element to be clickable
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Clicking element by {by}: {value}")
            element = WebDriverWait(self.driver, wait_time).until(
                EC.element_to_be_clickable((getattr(By, by.upper()), value))
            )
            element.click()
            return True
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"Failed to click element by {by}: {value} - {e}")
            return False

    def fill_input(self, by: str, value: str, text: str, wait_time: int = 10) -> bool:
        """
        Fills text into an input field after waiting for it to be present.
        
        Args:
            by: Locator strategy
            value: Locator value
            text: Text to enter in the input field
            wait_time: Time to wait for element
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.logger.info(f"Filling input {value} with text: {text}")
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((getattr(By, by.upper()), value))
            )
            element.clear()
            element.send_keys(text)
            return True
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"Failed to fill input {value}: {e}")
            return False

    def extract_text(self, by: str, value: str, wait_time: int = 10) -> Optional[str]:
        """
        Extracts text from an element after waiting for it to be present.
        
        Args:
            by: Locator strategy
            value: Locator value
            wait_time: Time to wait for element
            
        Returns:
            str or None: Text content if successful, None otherwise
        """
        try:
            self.logger.info(f"Extracting text from element by {by}: {value}")
            element = WebDriverWait(self.driver, wait_time).until(
                EC.presence_of_element_located((getattr(By, by.upper()), value))
            )
            return element.text
        except (TimeoutException, NoSuchElementException) as e:
            self.logger.error(f"Failed to extract text from element by {by}: {value} - {e}")
            return None

    def find_elements(self, by: str, value: str) -> List:
        """
        Finds all elements matching the provided selector.
        
        Args:
            by: Locator strategy
            value: Locator value
            
        Returns:
            list: List of WebElement objects
        """
        try:
            return self.driver.find_elements(getattr(By, by.upper()), value)
        except Exception as e:
            self.logger.error(f"Error finding elements by {by}: {value} - {e}")
            return []

    def take_screenshot(self, filename: Optional[str] = None) -> Optional[str]:
        """
        Takes a screenshot of the current page.
        
        Args:
            filename: Name for the screenshot file (without extension)
            
        Returns:
            str or None: Path to the screenshot if successful, None otherwise
        """
        try:
            if filename is None:
                filename = f"screenshot_{int(time.time())}"
            
            file_path = os.path.join(self.screenshot_dir, f"{filename}.png")
            self.driver.save_screenshot(file_path)
            self.logger.info(f"Screenshot saved to {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"Failed to take screenshot: {e}")
            return None

    def execute_javascript(self, script: str, *args) -> Optional[Any]:
        """
        Executes JavaScript in the browser context.
        
        Args:
            script: JavaScript code to execute
            *args: Arguments to pass to the JavaScript code
            
        Returns:
            Any: Result of the JavaScript execution or None if failed
        """
        try:
            return self.driver.execute_script(script, *args)
        except Exception as e:
            self.logger.error(f"Failed to execute JavaScript: {e}")
            return None

    def switch_to_frame(self, frame_reference) -> bool:
        """
        Switches to an iframe.
        
        Args:
            frame_reference: Index, name/id, or WebElement of the frame
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.driver.switch_to.frame(frame_reference)
            return True
        except Exception as e:
            self.logger.error(f"Failed to switch to frame: {e}")
            return False

    def switch_to_default_content(self) -> bool:
        """
        Switches back to the main document context.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.driver.switch_to.default_content()
            return True
        except Exception as e:
            self.logger.error(f"Failed to switch to default content: {e}")
            return False

    def get_page_source(self) -> str:
        """
        Gets the source HTML of the current page.
        
        Returns:
            str: HTML source of the current page
        """
        return self.driver.page_source

    def get_cookies(self) -> List[Dict]:
        """
        Gets all cookies from the current session.
        
        Returns:
            list: List of dictionaries containing cookie information
        """
        return self.driver.get_cookies()

    def add_cookie(self, cookie_dict: Dict) -> bool:
        """
        Adds a cookie to the current session.
        
        Args:
            cookie_dict: Dictionary with cookie information
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.driver.add_cookie(cookie_dict)
            return True
        except Exception as e:
            self.logger.error(f"Failed to add cookie: {e}")
            return False

    def navigate_back(self) -> None:
        """Navigates back in browser history."""
        self.driver.back()

    def navigate_forward(self) -> None:
        """Navigates forward in browser history."""
        self.driver.forward()

    def refresh_page(self) -> None:
        """Refreshes the current page."""
        self.driver.refresh()

    def hover_over_element(self, by: str, value: str) -> bool:
        """
        Hovers over an element.
        
        Args:
            by: Locator strategy
            value: Locator value
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            element = self.driver.find_element(getattr(By, by.upper()), value)
            ActionChains(self.driver).move_to_element(element).perform()
            return True
        except Exception as e:
            self.logger.error(f"Failed to hover over element: {e}")
            return False

    def perform_key_action(self, key_action: str) -> bool:
        """
        Performs a keyboard action like pressing Enter, Tab, etc.
        
        Args:
            key_action: Key to press (e.g., 'ENTER', 'TAB')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            action = ActionChains(self.driver)
            action.send_keys(getattr(Keys, key_action)).perform()
            return True
        except Exception as e:
            self.logger.error(f"Failed to perform key action {key_action}: {e}")
            return False

    def drag_and_drop(self, source_by: str, source_value: str, 
                      target_by: str, target_value: str) -> bool:
        """
        Performs drag and drop operation from source to target element.
        
        Args:
            source_by: Locator strategy for source element
            source_value: Locator value for source element
            target_by: Locator strategy for target element
            target_value: Locator value for target element
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            source = self.driver.find_element(getattr(By, source_by.upper()), source_value)
            target = self.driver.find_element(getattr(By, target_by.upper()), target_value)
            ActionChains(self.driver).drag_and_drop(source, target).perform()
            return True
        except Exception as e:
            self.logger.error(f"Failed to perform drag and drop: {e}")
            return False

    def health_check(self) -> Tuple[bool, str]:
        """
        Performs a health check on the WebAutomationAgent.
        
        Returns:
            tuple: (status: bool, message: str) - Status and additional information
        """
        try:
            self.driver.title  # Simple check to see if browser is responsive
            return True, "WebAutomationAgent is healthy"
        except Exception as e:
            error_msg = f"WebAutomationAgent health check failed: {e}"
            self.logger.error(error_msg)
            return False, error_msg
