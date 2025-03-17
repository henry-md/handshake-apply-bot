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
import json
from datetime import datetime

# Custom imports
from utils.selenium_helper import Helper
from utils.query_keywords import query_keywords

# Global variables
submissions_count = 0
job_list_len = 0
tab_count = 1
job_list_visited = 0
did_log_submissions = False
session_start_time = None

def open_and_login(url, driver, s, EMAIL, PASSWORD):
    # Open page
    driver.get(url)

    # Login
    s.click_with_wait("[data-bind='click: track_sso_click']")
    s.type_into_element_with_wait("[name='loginfmt']", EMAIL)
    s.click_with_wait("[type='submit']")
    s.type_into_element_with_wait("[name='passwd']", PASSWORD)
    s.click_with_wait("[type='submit']")
    s.click_with_wait_without_error("[class='sso-button']", timeout=1.5)

    # If url reset after login, go back
    if driver.current_url != url:
        driver.get(url)

def click_out_of_modal(s):
    if s.element_exists('[data-hook="apply-modal-content"]'):
        s.click_with_mouse('button[aria-label="dismiss"]')

def update_job_tracking(submissions_count):
    global did_log_submissions, session_start_time, tab_count
    if did_log_submissions:
        return
    
    # Calculate session duration in minutes
    session_duration = round((datetime.now() - session_start_time).total_seconds() / 60, 2)
    
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
    print('logging job list len', job_list_len, 'tab count', tab_count, 'job list visited', job_list_visited)
    new_session = {
        "date": current_time,
        "session_submissions": submissions_count,
        "job_list_len": job_list_len * tab_count,
        "job_list_visited": job_list_visited,
        "session_duration_minutes": session_duration
    }
    data["sessions"].append(new_session)
    
    # Write updated data
    with open(tracking_file, 'w') as f:
        json.dump(data, f, indent=4)

    # Mark that we've logged submissions
    did_log_submissions = True

def apply_to_jobs_in_left_panel(s):
    global submissions_count, job_list_len, job_list_visited, session_start_time

    # Apply to all jobs in left panel
    job_list = s.find_all_elements_with_wait("[data-hook='jobs-card']")
    assert job_list, '🔄 No jobs found'
    job_list_len = len(job_list)
    for i in range(len(job_list)):
        job_list_visited += 1
            
        click_out_of_modal(s)

        # Revive job_list if stale
        if not job_list[i] or not s.web_element_exists(job_list[i]):
            old_len = len(job_list)
            job_list = s.find_all_elements_with_wait("[data-hook='jobs-card']")
            assert job_list and len(job_list) == old_len, '🔄 Failed to revive job_list'
        
        # Scroll and click on job in left panel
        try:
            s.scroll_into_view(job_list[i])
            s.click_web_element(job_list[i])
        except:
            logging.error('🔄 Failed to scroll and click on job in left panel')
            continue
        
        # Skip external applications
        apply_btn, idx = s.find_any_element_with_wait("[aria-label='Apply']", "[aria-label='Apply Externally']")
        if idx == 1:
            continue
            
        # Skip jobs that don't match any keyword
        try:
            title_element = job_list[i].find_element("css selector", "h3")
            title_text = title_element.text
            if not any(keyword.lower() in title_text.lower() for keyword in query_keywords):
                logging.info(f"Skipping job with title: {title_text} - doesn't match keywords")
                continue
        except Exception as e:
            logging.error(f"Failed to check job title: {str(e)}")
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
            logging.info(f'🚀 Applied to job: {title_text} ({submissions_count} so far)')
        else:
            logging.error('🔄 No submit button found')
            continue

    # Style points
    click_out_of_modal(s)
    logging.info("✅ Successfully applied to all jobs")

    update_job_tracking(submissions_count)

def main():
    # Track submissions for this session
    global submissions_count, job_list_len, tab_count, job_list_visited, session_start_time, did_log_submissions
    
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
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M'
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
        "per_page": "25",
        "sort_direction": "desc",
        "sort_column": "default",
        "query": "software engineer",
        "employment_type_names[]": "Full-Time",
        "job.job_types[]": "9",
    }
    full_url = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    open_and_login(full_url, driver, s, EMAIL, PASSWORD)
    time.sleep(int(params['per_page']) / 100) # 10 seconds per 1000 jobs

    # Try applying to all jobs on all pages, and allow retry on failure
    while True:
        try:
            # Apply to jobs and then click next
            session_start_time = datetime.now()
            while True:
                apply_to_jobs_in_left_panel(s)
                if not s.element_exists('button[data-hook="search-pagination-next"]'):
                    break
                s.click_with_wait('button[data-hook="search-pagination-next"]')
                tab_count += 1
                print('tab count', tab_count)
                time.sleep(int(params['per_page']) / 100)
        except Exception as e:
            logging.error(f"Error occurred : {str(e)}")
        finally:
            update_job_tracking(submissions_count)

            # Reset global variables
            submissions_count = 0
            job_list_len = 0
            tab_count = 1
            job_list_visited = 0
            did_log_submissions = False
            session_start_time = None

            input('Press Enter to continue...')

    return driver

if __name__ == "__main__":
    try:
        driver = main()
        logging.info('PROGRAM DIED: OUTSIDE MAIN FUNCTION')
        time.sleep(60*60)
    except Exception as e:
        
        logging.error('Error occurred in main:')
        logging.error(traceback.format_exc())
        time.sleep(60*60)
    finally:
        update_job_tracking(submissions_count)
        driver.quit()
