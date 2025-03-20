from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os
from pprint import pprint
import sys
import time
import traceback
import logging
from query_keywords import query_search

# Import helper functions from apply.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from apply import open_and_login
from utils.selenium_helper import Helper

def main():
    # Load environment variables
    load_dotenv()
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("PASSWORD")

    # Driver setup
    chrome_options = Options()
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    logging.getLogger("selenium").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("webdriver_manager").setLevel(logging.WARNING)

    # Initialize helper
    s = Helper(driver, logging)

    # Construct URL with params (same as in apply.py)
    url = "https://jhu.joinhandshake.com/stu/postings"
    params = {
        "page": 1,
        "per_page": 1000,
        "sort_direction": "desc",
        "sort_column": "default",
        "query": query_search,
        "employment_type_names[]": "Full-Time",
        "job.job_types[]": "9",
    }
    full_url = f"{url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
    
    # Login to the platform
    open_and_login(full_url, driver, s, EMAIL, PASSWORD)

    # Wait for the job list to load
    time.sleep(params['per_page'] / 100)

    # Find all job cards
    # Apply to all jobs in left panel
    job_list = s.find_all_elements_with_wait("[data-hook='jobs-card']", timeout=10)
    assert job_list, '🔄 No jobs found'
    
    # Extract job titles
    job_titles = []
    for job in job_list:
        try:
            title_element = job.find_element("css selector", "h3")
            title_text = title_element.text
            job_titles.append(title_text)
        except:
            continue

    # Print results
    print(f"\nFound {len(job_list)} jobs:\n")
    pprint(job_titles, width=120, sort_dicts=False)

    return driver

if __name__ == "__main__":
    try:
        driver = main()
        print('PROGRAM DIED: OUTSIDE MAIN FUNCTION')
        time.sleep(60*60)
    except Exception as e:
        print('Error occurred in main:')
        print(traceback.format_exc())
        time.sleep(60*60)
    finally:
        driver.quit()

