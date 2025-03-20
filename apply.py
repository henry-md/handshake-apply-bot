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
from utils.query_keywords import query_keywords, bad_keywords, query_search

DEFAULT_STATE = {
    'submissions_count': 0,
    'job_list_len': 0,
    'tab_count': 1,
    'visited_indices': [0, 0],  # [start_idx, current_idx]
    'last_applied_job_idx': 0,  # idx of last successful application
    'did_log_submissions': False,
    'session_start_time': None,
    'num_jobs_to_skip_initially': 0,
    'jobs_per_page': 25,
}

def open_and_login(url, driver, s, email, password):
    # Open page
    driver.get(url)

    # Login
    s.click_with_wait("[data-bind='click: track_sso_click']")
    s.type_into_element_with_wait("[name='loginfmt']", email, timeout=10)
    s.click_with_wait("[type='submit']")
    s.type_into_element_with_wait("[name='passwd']", password, timeout=10)
    s.click_with_wait("[type='submit']")
    s.click_with_wait_without_error("[class='sso-button']", timeout=1.5)

    # If url reset after login, go back
    if driver.current_url != url:
        driver.get(url)

def click_out_of_modal(s):
    if s.element_exists('[data-hook="apply-modal-content"]'):
        s.click_with_mouse('button[aria-label="dismiss"]')

def update_job_tracking(state):
    if state['did_log_submissions']:
        return
    
    # Calculate session duration in minutes
    session_duration = round((datetime.now() - state['session_start_time']).total_seconds() / 60, 2)
    
    tracking_file = "utils/job_tracking.json"
    
    try:
        # Read existing data
        with open(tracking_file, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialize if file doesn't exist or is invalid
        data = {"total_submissions": 0, "last_applied_job_idx": 0, "sessions": []}
    
    # Update cumulative stats
    data["total_submissions"] += state['submissions_count']
    data["last_applied_job_idx"] = max(data["last_applied_job_idx"], state['last_applied_job_idx'])
    
    # Add new session
    current_time = datetime.now().strftime("%m/%d/%y %I:%M%p").lower()
    logging.info(f'Logging job list len: {state["job_list_len"]}, tab count: {state["tab_count"]}, visited range: {state["visited_indices"]}')
    new_session = {
        "date": current_time,
        "session_submissions": state['submissions_count'],
        "job_list_len": state['job_list_len'],
        "visited_indices": state['visited_indices'],
        "last_applied_job_idx": state['last_applied_job_idx'],
        "session_duration_minutes": session_duration
    }
    data["sessions"].append(new_session)
        
    # Write updated data
    with open(tracking_file, 'w') as f:
        json.dump(data, f, indent=4)

    # Mark that we've logged submissions
    state['did_log_submissions'] = True

def apply_to_jobs_in_left_panel(state, s):
    # Apply to all jobs in left panel
    job_list = s.find_all_elements_with_wait("[data-hook='jobs-card']")
    assert job_list, '🔄 No jobs found'
    state['job_list_len'] = len(job_list)

    # Skip first few jobs
    pages_to_skip = state['num_jobs_to_skip_initially'] // len(job_list)
    remaining_jobs = state['num_jobs_to_skip_initially'] % len(job_list)

    # Skip full pages and update visited_indices state
    for i in range(pages_to_skip):
        s.click_with_wait('button[data-hook="search-pagination-next"]', timeout=4)
        state['num_jobs_to_skip_initially'] -= len(job_list)
        state['visited_indices'][0] += len(job_list)
        state['visited_indices'][1] += len(job_list)
        time.sleep(int(len(job_list)) / 100)
    state['tab_count'] += pages_to_skip
    state['visited_indices'][0] += remaining_jobs
    state['visited_indices'][1] += remaining_jobs

    # Apply to rest
    for i in range(remaining_jobs, len(job_list)):
        state['visited_indices'][1] += 1
            
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
            if any(keyword.lower() in title_text.lower() for keyword in bad_keywords):
                continue

        except Exception as e:
            logging.error(f"Failed to check job title: {str(e)}")
            continue

        # Apply to the specific job in right panel
        s.click_web_element(apply_btn)
        apply_modal = s.find_element_with_wait('data-hook="apply-modal-content"', timeout=1) # Seems to use full time no matter what, strange.
        selection_elements = s.find_all_elements('[class="Select-control"] > *[class="Select-multi-value-wrapper"]', parent=apply_modal)
        for element in selection_elements:
            # s.actions.move_to_element(element).click().perform()
            s.click_web_element_with_mouse(element)
            # click 35px below the element
            time.sleep(1)
            s.actions.move_to_element_with_offset(element, 0, 35).click().perform()        

        # Click submit
        try:
            submit_btn = None
            if not selection_elements:
                submit_btn = s.find_element_with_wait("//button[.//span[contains(text(), 'Submit Application')]]", by=By.XPATH, timeout=3)
            else:
                submit_btn = s.find_element("//button[.//span[contains(text(), 'Submit Application')]]", by=By.XPATH)
            # check if submit_btn is disabled, and if it is, remove disabled attribute
            if submit_btn.get_attribute('disabled'):
                s.driver.execute_script("arguments[0].removeAttribute('disabled');", submit_btn)
            s.actions.move_to_element(submit_btn).click().perform()
            state['submissions_count'] += 1
            state['last_applied_job_idx'] = state['visited_indices'][1]
            logging.info(f'🚀 Applied to job: {title_text} ({state["submissions_count"]} so far)')
        except Exception as e:
            logging.error(f"Error clicking submit: {str(e)}")
            # Sometimes Handshake's button stop working (with or without a bot) — that's their problem
            if s.element_exists("//button[contains(@class, 'disabled') or @disabled]//span[contains(text(), 'Submit Application')]", by=By.XPATH, parent=apply_modal):
                logging.error('😡 Wasn\'t able to remove disabled from Handshake submit button')
            else:
                # Otherwise it's prob our bad
                logging.error('🔄 No submit button found or wasn\'t able to click it')
            continue

    # Only update state if we went through loop without error
    state['num_jobs_to_skip_initially'] = 0

    # Style points
    click_out_of_modal(s)
    logging.info("✅ Successfully applied to all jobs in current tab")

def main(state=DEFAULT_STATE, driver=None, email=None, password=None, debug_level=logging.INFO):
    # Make a deep copy of state
    for k, v in DEFAULT_STATE.items():
        if k not in state:
            state[k] = v

    # Load environment variables
    if email is None or password is None:
        load_dotenv()
        email = os.getenv("EMAIL")
        password = os.getenv("PASSWORD")

    # Driver setup
    if driver is None:
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
        level=debug_level,
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
        "per_page": state['jobs_per_page'],
        "sort_direction": "desc",
        "sort_column": "default",
        "query": query_search,
        "employment_type_names[]": "Full-Time",
        "job.job_types[]": "9",
    }
    full_url = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    open_and_login(full_url, driver, s, email, password)
    time.sleep(int(params['per_page']) / 100) # 10 seconds per 1000 jobs

    # Apply to jobs and then click next
    state['session_start_time'] = datetime.now()
    try:
        while True:
            apply_to_jobs_in_left_panel(state, s)
            s.click_with_wait('button[data-hook="search-pagination-next"]')
            state['tab_count'] += 1
            logging.info(f'⏭️ Going to next page: {state["tab_count"]}')
            logging.info(f'state at this point: {state}')
            time.sleep(int(params['per_page']) / 100)
    except Exception as e:
        logging.error(f"Error occurred in main(): {str(e)}")
        logging.error(traceback.format_exc())
    finally:
        update_job_tracking(state)
    
    return state, driver

if __name__ == "__main__":
    try:
        state, driver = main()
        logging.info('🪦 Program died: outside main function')
        time.sleep(3600)
    except Exception as e:
        logging.error('🪦 Error occurred in main:')
        logging.error(traceback.format_exc())
        time.sleep(3600)
    finally:
        update_job_tracking(state)
        driver.quit()
