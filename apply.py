from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os
import logging
import time
import traceback
from pynput import keyboard
import json
from datetime import datetime

# Custom imports
from utils.selenium_helper import Helper

# Global variables
submissions_count = 0
stop_loop = False
did_log_submissions = False

def open_and_login(url, driver, s, EMAIL, PASSWORD):
    # Open page
    driver.get(url)

    # Login
    s.click_with_wait("[data-bind='click: track_sso_click']")
    s.type_into_element_with_wait("[name='loginfmt']", EMAIL)
    s.click_with_wait("[type='submit']")
    s.type_into_element_with_wait("[name='passwd']", PASSWORD)
    s.click_with_wait("[type='submit']")
    s.click_without_error("[class='sso-button']")

    # If url reset after login, go back
    if driver.current_url != url:
        driver.get(url)

def click_out_of_modal(s):
    if s.element_exists('[data-hook="apply-modal-content"]'):
        s.click_with_mouse('button[aria-label="dismiss"]')

def on_press(key):
    global stop_loop
    try:
        if key == keyboard.Key.enter:
            print("Enter pressed - stopping after current job")
            stop_loop = True
    except AttributeError:
        pass

def update_job_tracking(submissions_count):
    global did_log_submissions
    if did_log_submissions or not submissions_count:
        return
    
    tracking_file = "utils/job_tracking.json"
    
    try:
        # Read existing data
        with open(tracking_file, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialize if file doesn't exist or is invalid
        data = {"total_submissions": 0, "sessions": []}
    
    # Update total submissions
    data["total_submissions"] += submissions_count
    
    # Add new session
    current_time = datetime.now().strftime("%m/%d/%y %I:%M%p").lower()
    new_session = {
        "date": current_time,
        "session_submissions": submissions_count
    }
    data["sessions"].append(new_session)
    
    # Write updated data
    with open(tracking_file, 'w') as f:
        json.dump(data, f, indent=4)

    # Mark that we've logged submissions
    did_log_submissions = True

def main():
    # Track submissions for this session, and whether we should stop 
    # the loop because of a keyboard interrupt
    global submissions_count, stop_loop
    
    # Setup keyboard listener
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    
    # Load environment variables
    load_dotenv()
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")

    # Driver setup
    chrome_options = Options()
    # Uncomment the line below if you want to run in headless mode
    # chrome_options.add_argument('--headless')
    # Initialize Chrome driver with automatic ChromeDriver management
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("webdriver_manager").setLevel(logging.WARNING)

    # Get helper functions
    s = Helper(driver, logging)

    # Construct full URL with params
    url = "https://jhu.joinhandshake.com/stu/postings"
    params = {
        "page": "1",
        "per_page": "100",
        "sort_direction": "desc",
        "sort_column": "default",
        "query": "software engineer",
        "employment_type_names[]": "Full-Time",
        "job.job_types[]": "9",
    }
    full_url = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    open_and_login(full_url, driver, s, EMAIL, PASSWORD)

    # Apply to all jobs in left panel
    job_preview_panel = s.find_element_with_wait("[aria-label='Job Preview']")
    job_list = s.find_all_elements_with_wait("[data-hook='jobs-card']")
    assert job_list, '🔄 No jobs found'
    for i in range(len(job_list)):
        if stop_loop:
            print("🛑 Stopping job applications as requested")
            break
            
        click_out_of_modal(s)

        # Revive job_list if stale
        if not job_list[i] or not s.web_element_exists(job_list[i]):
            old_len = len(job_list)
            job_list = s.find_all_elements_with_wait("[data-hook='jobs-card']")
            print('old job list len', old_len)
            print('new job list', job_list)
            assert job_list and len(job_list) == old_len, '🔄 Failed to revive job_list'
        
        # Scroll and click on job in left panel
        try:
            s.scroll_into_view(job_list[i])
            s.click_web_element(job_list[i])
        except:
            print('🔄 Failed to scroll and click on job in left panel')
            continue
        
        # Skip external applications
        apply_btn, idx = s.find_any_element_with_wait("[aria-label='Apply']", "[aria-label='Apply Externally']")
        if idx == 1:
            continue

        # Apply to the specific job in right panel
        s.click_web_element(apply_btn)
        apply_modal = s.find_element_with_wait('data-hook="apply-modal-content"', timeout=1) # Seems to use full time no matter what, strange.
        selection_elements = s.find_all_elements('[class="Select-control"] > *[class="Select-multi-value-wrapper"]', parent=apply_modal)
        for element in selection_elements:
            s.click_web_element_with_mouse(element)
            time.sleep(0.75)
            # click 35px below the element
            s.actions.move_to_element_with_offset(element, 0, 35).click().perform()
        
        # Click submit
        if s.element_exists('[data-hook="submit-application"]', parent=apply_modal):
            s.click_with_mouse('[data-hook="submit-application"]', parent=apply_modal)
            submissions_count += 1
        else:
            print('🔄 No submit button found')
            continue

    # Style points
    click_out_of_modal(s)

    listener.stop()
    update_job_tracking(submissions_count)
    return driver

if __name__ == "__main__":
    try:
        driver = main()
        print('PROGRAM DIED: OUTSIDE MAIN FUNCTION')
        time.sleep(60*60)
    except Exception as e:
        update_job_tracking(submissions_count)
        print('Error occurred in main:')
        print(traceback.format_exc())
        time.sleep(60*60)
    finally:
        driver.quit()
