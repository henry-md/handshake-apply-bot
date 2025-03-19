from apply import main
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import logging
import json
import time

def get_num_jobs_to_skip_initially():
    with open("utils/job_tracking.json", "r") as f:
        data = json.load(f)
    return data["last_applied_job_idx_visited"] if "last_applied_job_idx_visited" in data else 0

STATE = {
    'num_jobs_to_skip_initially': get_num_jobs_to_skip_initially()
}


# Try applying to all jobs on all pages, and allow retry on failure
while True:
    try:
        # Set up driver
        chrome_options = Options()
        # chrome_options.add_argument('--headless') # Headless mode :o
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=chrome_options
        )

        # Apply for jobs, use logger & update json tracking file
        state, _ = main(driver=driver, state=STATE)
        logging.info(f'🪦 Program died: outside main function')
        time.sleep(3600)

    except Exception as e:
        logging.error(f"Error occurred in main(): {str(e)}")

    finally:
        driver.quit()