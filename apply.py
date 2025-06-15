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
from utils.query_keywords import bad_keywords, good_keywords, query_search
from utils.timer import timer
from utils.logging_formatter import ColoredFormatter

# State variables to fully define session state. Some variables can be changed by user like jobs_per_page.
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

# Handshake-specific selectors — these may need to be updated over time with site updates.
# If the code suddenly breaks one day, it's likely here.
SELECTORS = {
    'job_block': "[data-hook*='job-result-card']", # a single job application block in the left column
    'job_block_title': "[id]",
    'apply_btn': "[aria-label='Apply']",
    'apply_btns_internal_or_external': ["[aria-label='Apply']", "[aria-label='Apply externally']"],
    'submit_btn': "//button[contains(text(), 'Submit Application')]",
    'submit_btn_disabled': "//button[contains(@class, 'disabled') or @disabled][contains(text(), 'Submit Application')]",
    'dismiss_btn': "button[aria-label='Cancel application']", # x button at top right of application modal for a specific job
    'pagination_next_btn': "button[aria-label='next page']",
    'apply_modal_content': "[data-enter][data-dialog='true']",
    'selection_elements': "[aria-haspopup='listbox'][role='combobox'][value='']",
    'selection_elements_to_fill': "//div[@role='listbox']/div[@role='option' and @aria-selected='false' and (text()='Supporting Documents' or text()='Transcript' or text()='Cover Letter' or text()='Henry Deutsch Resume')]",
}

@timer
def open_and_login(url, driver, s, email, password):
    """
    Opens url [handshake] and logs in with email and password.

    driver (webdriver.Chrome): Selenium WebDriver instance for browser automation
    """

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
    """
    Clicks out of a modal if there is one. Throws nothing if no modal exists.
    """
    if s.element_exists(SELECTORS['apply_modal_content']):
        s.click_with_mouse(SELECTORS['dismiss_btn'])

@timer
def update_job_tracking(state):
    """
    Updates job tracking file with current state.
    """
    if state['did_log_submissions']:
        return
    
    # Calculate session duration in minutes
    session_duration = round((datetime.now() - state['session_start_time']).total_seconds() / 60, 2)
    
    tracking_file = "utils/job_tracking.json"
    
    # Initialize empty data file if it doesn't exist, and initialize `data` either way
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
    
    # Add new session to `data.sessions`
    current_time = datetime.now().strftime("%m/%d/%y %I:%M%p").lower()
    logging.debug(f'Logging job list len: {state["job_list_len"]}, tab count: {state["tab_count"]}, visited range: {state["visited_indices"]}')
    new_session = {
        "date": current_time,
        "session_submissions": state['submissions_count'],
        "job_list_len": state['job_list_len'],
        "visited_indices": state['visited_indices'],
        "last_applied_job_idx": state['last_applied_job_idx'],
        "session_duration_minutes": session_duration
    }
    data["sessions"].append(new_session)
        
    # Write updated data to data file
    with open(tracking_file, 'w') as f:
        json.dump(data, f, indent=4)

    # Mark that we've logged submissions
    state['did_log_submissions'] = True

@timer
def apply_to_jobs_in_left_panel(state, s):
    """
    Apply to all jobs in this page (and no other pages). Read jobs from open left panel, skip jobs (& toggle necessary pages), and apply to the rest that fit our criteria: internal applications (i.e. no link to apply on their site) w/ one good keyword and none of the bad keywords.

    Before applying to every job, it will try to refresh the list of jobs if it's gotten stale and some job no longer exists.
    """

    # Apply to all jobs in left panel
    job_list = s.find_all_elements_with_wait(SELECTORS['job_block'])
    assert job_list, '🔄 No jobs found'
    state['job_list_len'] = len(job_list)

    # Skip first few jobs
    pages_to_skip = state['num_jobs_to_skip_initially'] // len(job_list)
    remaining_jobs = state['num_jobs_to_skip_initially'] % len(job_list)

    # Skip full pages and update visited_indices state
    for i in range(pages_to_skip):
        s.click_with_wait(SELECTORS['pagination_next_btn'], timeout=4)
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
            job_list = s.find_all_elements_with_wait(SELECTORS['job_block'])
            assert job_list and len(job_list) == old_len, '🔄 Failed to revive job_list'
            logging.info(f'💪 Revived job_list to length {len(job_list)}')
        
        # Scroll and click on job in left panel
        try:
            s.scroll_into_view(job_list[i])
            s.click_web_element(job_list[i])
        except:
            logging.error('🔄 Failed to scroll and click on job in left panel')
            continue
        
        # Skip external applications
        apply_btn, idx = s.find_any_element_with_wait(*SELECTORS['apply_btns_internal_or_external'])
        if idx == 1 or idx == -1:
            continue
            
        # Filter jobs with good and bad keywords
        try:
            title_element = s.find_element(SELECTORS['job_block_title'], parent=job_list[i])
            title_text = title_element.text

            # Check that all levels of good_keywords are satisfied
            break_flag = False
            for level_name, good_keyword_level in good_keywords.items():
                if not any(keyword.lower() in title_text.lower() for keyword in good_keyword_level):
                    logging.info(f"✋ Skipping job with title: {title_text} - doesn't match requirement for {level_name}")
                    break_flag = True
                    break
            if break_flag: continue

            # Check that no bad keywords are in the title
            if any(keyword.lower() in title_text.lower() for keyword in bad_keywords):
                continue
        except Exception as e:
            logging.error(f"Failed to check job title: {str(e)}")
            continue

        # Apply to the specific job in right panel: for every job, click it, and simply click 35px below all the input selections.
        print()
        logging.info(f'📝 Trying to apply to job w/ title: {title_text}')
        try:
            s.click_web_element(apply_btn)
            apply_modal = s.find_element_with_wait(SELECTORS['apply_modal_content'], timeout=1) # Seems to use full time no matter what, strange.
            selection_elements = s.find_all_elements(SELECTORS['selection_elements'], parent=apply_modal)
            for selection_input in selection_elements:
                # Click selection autofill if it's already available
                selection_fill = s.find_element(SELECTORS['selection_elements_to_fill'], by=By.XPATH)
                if selection_fill:
                    s.click_web_element(selection_fill)
                    continue

                # Otherwise, click the search box first to get the autofill option
                selection_input.click()
                selection_fill = s.find_element_with_wait(SELECTORS['selection_elements_to_fill'], by=By.XPATH, timeout=3)
                if not selection_fill:
                    raise Exception('🔄 No selection fill found')
                s.click_web_element(selection_fill)
                time.sleep(3)
        except Exception as e:
            logging.error(f"✌️ Ts too complicated twin. Error clicking selections, will skip to next job. Error: {str(e)}")
            continue

        # Click submit on this job app
        try:
            submit_btn = None
            if not selection_elements:
                submit_btn = s.find_element_with_wait(SELECTORS['submit_btn'], by=By.XPATH, timeout=3)
            else:
                submit_btn = s.find_element(SELECTORS['submit_btn'], by=By.XPATH)
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
            if s.element_exists(SELECTORS['submit_btn_disabled'], by=By.XPATH, parent=apply_modal):
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

@timer
def main(state=DEFAULT_STATE, driver=None, email=None, password=None, debug_level=logging.INFO):
    """
    A lot of setup: Load env variables (email, password), set up driver (for )
    """

    # Ensure state has all the keys in DEFAULT_STATE
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
    
    # Create a colored formatter and apply it to the root logger
    colored_formatter = ColoredFormatter(
        fmt='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M'
    )
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.setFormatter(colored_formatter)

    # Get helper functions
    helper_logger = logging.getLogger('selenium_helper')
    helper_logger.setLevel(logging.CRITICAL)
    s = Helper(driver, helper_logger)

    # Construct full URL with params
    url = "https://jhu.joinhandshake.com/stu/postings"
    params = {
        "query": query_search,
        "page": "1",
        "per_page": state['jobs_per_page'],
        "employmentTypes": "1", # Full-time
        "employmentTypes": "2", # Part-time
        "jobType": "3", # Internship
        "jobType": "6", # On Campus Student Employment
        "jobType": "7", # Fellowship
        "pay%5BsalaryType%5D": "1", # Paid
    }
    full_url = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    full_url = "https://jhu.joinhandshake.com/job-search/9566411?jobType=3&jobType=6&jobType=7&pay%5BsalaryType%5D=1&query=software+engineer&per_page=25&page=1"
    
    open_and_login(full_url, driver, s, email, password)
    time.sleep(int(params['per_page']) / 100) # 10 seconds per 1000 jobs

    # Apply to jobs and then click next
    state['session_start_time'] = datetime.now()
    try:
        while True:
            apply_to_jobs_in_left_panel(state, s)
            s.click_with_wait(SELECTORS['pagination_next_btn'])
            state['tab_count'] += 1
            logging.info(f'⏭️ Going to next page: {state["tab_count"]}')
            logging.debug(f'state at this point: {state}')
            time.sleep(int(params['per_page']) / 100)
    except Exception as e:
        logging.critical(f"Error occurred in main(): {str(e)}")
        logging.critical(traceback.format_exc())
    finally:
        update_job_tracking(state)
    
    return state, driver

if __name__ == "__main__":
    try:
        state, driver = main()
        logging.critical('🪦 Program died: outside main function')
        time.sleep(3600)
    except Exception as e:
        logging.critical('🪦 Error occurred in main:')
        logging.critical(traceback.format_exc())
        time.sleep(3600)
    finally:
        update_job_tracking(state)
        driver.quit()
