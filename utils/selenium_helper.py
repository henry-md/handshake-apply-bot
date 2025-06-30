from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from typing import List
import time
from functools import wraps
from selenium.webdriver.common.action_chains import ActionChains

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
  
  def stringify_elements(self, res: List[WebElement | None] | WebElement | None, relevant_attributes=[]) -> List[str] | str:
    """
    Stringifies a list of WebElements.
    If relevant_attributes is empty, all attributes will be included in the string.
    If relevant_attributes is provided, only the attributes in the list will be included in the string.
    Acts robustly in the case that some of the relevant_attributes are not present in the given element.
    Includes the visible text content between the tags.
    Ex. <input value="test">test</input>
    """
    if res is None:
      return "None"
    
    element_strings = []
    if isinstance(res, WebElement):
      res = [res]
    for element in res:
      if element is None:
        element_strings.append("None")
        continue
      tag_name = element.tag_name
      
      # Get all attributes as a dictionary
      attrs = self.driver.execute_script("""
        let attrs = {};
        let element = arguments[0];
        for (let i = 0; i < element.attributes.length; i++) {
          attrs[element.attributes[i].name] = element.attributes[i].value;
        }
        return attrs;
      """, element)

      # For input elements, also get the 'value' property (not always in attributes)
      if tag_name.lower() == "input" and ("value" not in attrs or (relevant_attributes and "value" in relevant_attributes)):
        attrs["value"] = element.get_attribute("value") or ""
      
      # Filter attributes if relevant_attributes is provided
      if relevant_attributes:
        filtered_attrs = {}
        for k in relevant_attributes:
          if k in attrs:
            filtered_attrs[k] = attrs[k]
        attrs = filtered_attrs
      
      # Format attributes as k='v'
      attr_str = ' '.join([f"{k}='{v}'" for k, v in attrs.items()])
      attr_str = f" {attr_str}" if attr_str else ""
      
      # Get the visible text content
      text_content = element.text or ""
      
      # Compose the HTML string
      html_str = f"<{tag_name}{attr_str}>{text_content}</{tag_name}>"
      element_strings.append(html_str)
    return element_strings if len(element_strings) > 1 else element_strings[0]

  def web_element_exists(self, element: WebElement) -> bool:
    try:
      element.is_displayed()
      return True
    except:
      return False
    
  def element_exists(self, selector: str, by=By.CSS_SELECTOR, parent=None) -> bool:
    try:
      if parent is None:
        parent = self.driver
      return bool(parent.find_element(by, selector))
    except:
      return False
    
  def scroll_into_view(self, element) -> None:
    self.driver.execute_script("arguments[0].scrollIntoView();", element)

  @log_execution_time
  def find_element_with_wait(self, selector: str, by=By.CSS_SELECTOR, parent=None, timeout=3) -> WebElement:
    try:
      if parent is None:
        parent = self.driver
      res = WebDriverWait(parent, timeout).until(
        EC.element_to_be_clickable((by, selector))
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
  def find_any_element_with_wait(self, *selectors: str, parent=None) -> tuple[WebElement, int]:
    """
    Searches for any of the provided selectors and returns the first WebElement found along with its index in the argument list.
    
    Args:
        *selectors: Variable number of selector strings
        parent: Optional parent element to search within
    
    Returns:
        Tuple of (WebElement, index) if found, or (None, -1) if no element is found. Index is the index of the selector that was found in the argument list.
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
      element.click()
      # self.driver.execute_script("""
      #   arguments[0].scrollIntoView(); 
      #   arguments[0].click();
      #   arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
      #   arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
      # """, element)
      self.logging.debug(f'Clicked')
    except:
      self.logging.error(f'Failed to click: {self.stringify_elements(element)}')

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
      self.logging.debug(f'Clicked with mouse: {self.stringify_elements(element)}')
    except:
      self.logging.debug(f'Failed to click web element')

  @log_execution_time
  def click_with_wait(self, selector: str, by=By.CSS_SELECTOR, parent=None, timeout=3) -> None:
    self.logging.debug(f'Clicking: {selector}')
    if parent is None:
      parent = self.driver
    element = self.find_element_with_wait(selector, by, parent)
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
  def type_into_element_with_wait(self, selector: str, text, by=By.CSS_SELECTOR, parent=None, timeout=None) -> None:
    self.logging.debug(f'Typing: {text} into: {selector}')
    if parent is None:
        parent = self.driver
    
    # Method 1: Using kwargs dictionary
    kwargs = {'selector': selector, 'by': by, 'parent': parent}
    if timeout is not None:
        kwargs['timeout'] = timeout
    element = self.find_element_with_wait(**kwargs)

    if not element: raise Exception(f'Element not found, so can\'t type: {selector}')
    element.send_keys(text)
    self.logging.debug(f'Typed')

