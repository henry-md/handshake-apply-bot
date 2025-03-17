from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from typing import List
import time
from functools import wraps
from selenium.webdriver.common.action_chains import ActionChains

# TODO
# Refactor this so that with_mouse and with_wait are keyword arguments that can be set to True, and are False by default

def log_execution_time(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        start_time = time.time()
        result = func(self, *args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        self.logging.debug(f'{func.__name__}{args} {kwargs} took {execution_time:.2f}s')
        return result
    return wrapper

class Helper:
  def __init__(self, driver, logging):
    self.driver = driver
    self.logging = logging
    self.actions = ActionChains(driver)

  def web_element_exists(self, element: WebElement) -> bool:
    try:
      element.is_displayed()
      return True
    except:
      return False
    
  def element_exists(self, selector: str, parent=None) -> bool:
    try:
      if parent is None:
        parent = self.driver
      return bool(parent.find_element(By.CSS_SELECTOR, selector))
    except:
      return False
    
  def scroll_into_view(self, element) -> None:
    self.driver.execute_script("arguments[0].scrollIntoView();", element)

  @log_execution_time
  def find_element_with_wait(self, selector: str, parent=None, timeout=3) -> WebElement:
    try:
      if parent is None:
        parent = self.driver
      res = WebDriverWait(parent, timeout).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
      )
      self.logging.debug(f'Searching for: {selector}; Found')
      return res
    except:
      self.logging.debug(f'Searching for: {selector}; Not found')

  def find_all_elements(self, selector: str, parent=None) -> List[WebElement]:
    try:
      if parent is None:
        parent = self.driver
      return parent.find_elements(By.CSS_SELECTOR, selector)
    except:
      self.logging.debug(f'Searching for: {selector}; Not found')
      return []

  @log_execution_time
  def find_all_elements_with_wait(self, selector: str, parent=None, timeout=3) -> List[WebElement]:
    try:
      if parent is None:
        parent = self.driver
      res = WebDriverWait(parent, timeout).until(
          EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
      )
      self.logging.debug(f'Searching for: {selector}; Found')
      return res
    except:
      self.logging.debug(f'Searching for: {selector}; Not found')

  @log_execution_time
  def find_any_element_with_wait(self, *selectors, parent=None) -> tuple[WebElement, int]:
    """
    Searches for any of the provided selectors and returns the first WebElement found along with its index in the argument list.
    
    Args:
        *selectors: Variable number of selector strings
        parent: Optional parent element to search within
    
    Returns:
        Tuple of (WebElement, index) if found, or (None, -1) if no element is found
    """
    if parent is None:
      parent = self.driver
    
    for _ in range(10):
      for idx, selector in enumerate(selectors):
        try:
          element = parent.find_element(By.CSS_SELECTOR, selector)
          self.logging.debug(f'Found {selector} from list of args')
          return element, idx
        except:
          pass
      time.sleep(0.1)
    
    return None, -1

  def find_element(self, selector: str, parent=None, by=By.CSS_SELECTOR) -> WebElement | None:
    try:
      if parent is None:
        parent = self.driver
      res = parent.find_element(by, selector)
      self.logging.debug(f'Quick searching for: {selector}; Found')
      return res
    except:
      self.logging.debug(f'Quick searching for: {selector}; Not found')

  def click_web_element(self, element) -> None:
    try:
      self.logging.debug(f'Clicking: {element}')
      self.driver.execute_script("""
          arguments[0].scrollIntoView(); 
          arguments[0].click();
          arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
          arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
      """, element)
      self.logging.debug(f'Clicked')
    except:
      self.logging.debug(f'Failed to click: {element}')

  def click_with_mouse(self, selector: str, parent=None) -> None:
    try:
      if parent is None:
        parent = self.driver
      element = self.find_element(selector, parent)
      if not element: raise Exception(f'Element not found, so can\'t click: {selector}')
      self.click_web_element_with_mouse(element)
      self.logging.debug(f'Clicked with mouse: {selector}')
    except:
      self.logging.debug(f'Failed to click with mouse: {selector}')

  def click_web_element_with_mouse(self, element) -> None:
    try:
      self.actions.move_to_element(element).click().perform()
      self.logging.debug(f'Clicked with mouse: {element}')
    except:
      self.logging.debug(f'Failed to click web element')

  @log_execution_time
  def click_with_wait(self, selector: str, parent=None, timeout=3) -> None:
    self.logging.debug(f'Clicking: {selector}')
    if parent is None:
      parent = self.driver
    element = self.find_element_with_wait(selector, parent)
    if not element: raise Exception(f'Element not found, so can\'t click: {selector}')
    if self.driver is None:
      self.click_web_element(element, self.driver)
    else:
      self.driver.execute_script("arguments[0].click();", element)
    self.logging.debug(f'Clicked: {selector}')

  @log_execution_time
  def click_with_wait_without_error(self, selector: str, parent=None, timeout=3) -> None:
    try:
      self.click_with_wait(selector, parent, timeout)
    except:
      self.logging.debug(f'Couldn\'t click but didn\'t sweat: {selector}')

  @log_execution_time
  def click_without_error(self, selector: str, parent=None) -> None:
    try:
      self.click(selector, parent)
    except:
      self.logging.debug(f'Couldn\'t click but didn\'t sweat: {selector}')

  @log_execution_time
  def click(self, selector: str, parent=None) -> None:
    self.logging.debug(f'Quick clicking: {selector}')
    if parent is None:
      parent = self.driver
    element = self.find_element(selector, parent)
    if not element: raise Exception(f'Element not found, so can\'t click: {selector}')
    self.click_web_element(element)
    self.logging.debug(f'Clicked')

  @log_execution_time
  def type_into_element_with_wait(self, selector: str, text, parent=None) -> None:
    self.logging.debug(f'Typing: {text} into: {selector}')
    if parent is None:
      parent = self.driver
    element = self.find_element_with_wait(selector, parent)
    if not element: raise Exception(f'Element not found, so can\'t type: {selector}')
    element.send_keys(text)
    self.logging.debug(f'Typed')

  @log_execution_time
  def stringify_elements(self, res: List[WebElement]) -> List[str]:
    element_text = []
    for i, element in enumerate(res):
      # Handle warning messages
      if element.tag_name == 'span' and element.get_attribute('class') == 'artdeco-inline-feedback__message':
        element_text.append(f"REQUIREMENT FOR THE ABOVE^ (element {i + 1}): {element.text}")
        continue
      
      # Handle all other form elements
      type_str = f" (Type: {element.get_attribute('type')})" if element.tag_name == 'input' else ''
      curr_element_text = f"Element {i + 1}: HTML Tag: {element.tag_name}{type_str}; "
      # Check input and selection default value
      if element.tag_name == 'input' or element.tag_name == 'select':
        default_value = element.get_attribute('value')
        curr_element_text += f"Default Value: '{default_value}'; "
      # Check label and span inner text
      if element.tag_name == 'label' or element.tag_name == 'span':
        try:
          child_span = element.find_element(By.CSS_SELECTOR, "span:not([class*='hidden'])")
          curr_element_text += f"Inner Text: '{child_span.text}'; "
        except:
          curr_element_text += f"Inner Text: '{element.text}'; "
      # Check selection options
      if element.tag_name == 'select':
        options = element.find_elements(By.TAG_NAME, 'option')
        curr_element_text += f"Options: {[opt.text for opt in options[:30]]}{' & other options...' if len(options) > 30 else ''}; "
      # Check if span or label is required
      if element.tag_name == 'span' or element.tag_name == 'label':
        parent = element.find_element(By.XPATH, './..')
        after_parent = self.driver.execute_script(
          "return window.getComputedStyle(arguments[0], '::after').getPropertyValue('content');",
          parent
        )
        after_element = self.driver.execute_script(
          "return window.getComputedStyle(arguments[0], '::after').getPropertyValue('content');",
          element
        )
        is_required = after_parent.strip('"') == '*' or after_element.strip('"') == '*'
        if is_required: curr_element_text += f"Required: {is_required}; "
      element_text.append(curr_element_text)
    return element_text
