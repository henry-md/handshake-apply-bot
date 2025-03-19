from apply import main
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
import json
import time
from apply import update_job_tracking
from apply import DEFAULT_STATE

def get_num_jobs_to_skip_initially():
    with open("utils/job_tracking.json", "r") as f:
        data = json.load(f)
    return data["last_applied_job_idx_visited"] if "last_applied_job_idx_visited" in data else 0

STATE = {
    'submissions_count': 0,
    'job_list_len': 0,
    'tab_count': 1,
    'last_job_idx_visited': 0,
    'last_applied_job_idx_visited': 0,
    'did_log_submissions': False,
    'session_start_time': None,
    'num_jobs_to_skip_initially': 100, # get_num_jobs_to_skip_initially()
    'jobs_per_page': 50
}

# Check that all keys in STATE are in DEFAULT_STATE
assert all(k in DEFAULT_STATE for k in STATE), '🔄 Missing keys in STATE'

# Try applying to all jobs on all pages, and allow retry on failure
while True:
    state = STATE.copy()

    try:
        # Set up driver
        chrome_options = Options()
        # chrome_options.add_argument('--headless') # Headless mode :o
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        # Apply for jobs, use logger & update json tracking file
        state, _ = main(driver=driver, state=state, debug_level=logging.DEBUG)
        print('from robust file, state:', state)
        logging.info(f'🪦 Program died: outside main function')
        update_job_tracking(state)
        time.sleep(3600)

    except Exception as e:
        logging.error(f"Error occurred in main(): {str(e)}")

    finally:
        update_job_tracking(state)
        time.sleep(3600)
        driver.quit()
        