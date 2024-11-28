import os
import json
import re
import time
import random
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dotenv import load_dotenv

load_dotenv()

# access the variables
linked_email = os.getenv('LINKEDIN_EMAIL')
linked_password = os.getenv('LINKEDIN_PASSWORD')

def get_random_user_agent():
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        # Add more as needed
    ]
    return random.choice(user_agents)


def init_driver():
    chrome_options = Options()
    chrome_options.add_argument("--incognito")  # Enable incognito mode
    chrome_options.add_argument(f"user-agent={get_random_user_agent()}")  # Add random user-agent
    # chrome_options.add_argument("--headless")  # Optional: Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")

    # Path to the ChromeDriver binary (Ensure you have it installed)
    driver_path = "/usr/local/bin/chromedriver"  # Adjust this if needed
    service = Service(driver_path)

    # Initialize the WebDriver with options and service
    driver = webdriver.Chrome(service=service, options=chrome_options)

    return driver

def login_to_linkedin(driver):
    driver.get("https://www.linkedin.com/login?fromSignIn=true&trk=guest_homepage-basic_nav-header-signin")
    time.sleep(random.uniform(2,7))

    username = driver.find_element(By.NAME, "session_key")
    password = driver.find_element(By.NAME, "session_password")
    signin = driver.find_element(By.CSS_SELECTOR, "button.btn__primary--large.from__button--floating")

    time.sleep(random.uniform(6, 8))
    username.send_keys(linked_email)  # Replace with your email
    time.sleep(random.uniform(2, 5))
    password.send_keys(linked_password)  # Replace with your password
    time.sleep(random.uniform(2, 6))
    signin.click()

    print('Logged in')

    time.sleep(random.uniform(7, 12))


def clean_text(text):
    """Helper function to clean text by removing newline characters, extra spaces, and unnecessary whitespace."""
    # Replace newlines with spaces and remove leading/trailing whitespace
    text = text.replace('\n', ' ').strip()
    # Replace multiple spaces with a single space
    text = ' '.join(text.split())
    text = text.replace(' ·', '').replace('· ', '').replace('·', '')
    return text


def parse_dates(dates_text):
    """Helper function to parse dates and split them into start and end dates in YYYYMMDD format."""
    dates_parts = dates_text.split('·')[0].strip()
    if 'Present' in dates_parts:
        start_date, _ = dates_parts.split(' - ')
        end_date = '20991231'  # Placeholder for "Present"
    else:
        start_date, end_date = dates_parts.split(' - ')

    # Convert start and end dates to the YYYYMMDD format
    start_date = format_date(start_date)
    end_date = '20991231' if end_date == 'present' else format_date(end_date)

    return start_date, end_date


def format_date(date_str):
    """Helper function to format a date string into 'YYYYMMDD' format."""
    date_str = date_str.strip()
    for date_format in ("%b %Y", "%b %d, %Y", "%Y"):  # Try different formats
        try:
            date_obj = datetime.strptime(date_str, date_format)
            return date_obj.strftime("%Y%m%d")
        except ValueError:
            continue
    # If no format matches, return a specific placeholder
    return "20990101"  # Or you can decide to handle differently if needed

def nested_experience(section,company_name):
    nested_experience_data = {}

    try:
        # Extract the job title from the nested experience
        nested_experience_data['company'] = company_name
        title_xpath = ".//div[contains(@class, 't-bold')]//span[1]"
        title_element = section.find_element(By.XPATH, title_xpath)
        nested_experience_data['title'] = title_element.text.strip()
        work_xpath = ".//div[contains(@class, 'display-flex full-width')]//div[contains(@class, 't-14 t-normal t-black')]//span[@aria-hidden='true']"
        work_detail = section.find_element(By.XPATH, work_xpath)
        nested_experience_data['description'] = clean_text(work_detail.text.strip())

        # Extract the dates and split them into start_date and end_date
        dates_text_element = section.find_element(By.XPATH, ".//span[contains(@class, 't-14') and contains(@class, 't-normal') and contains(@class, 't-black--light')]")
        nested_experience_data['start_date'], nested_experience_data['end_date'] = parse_dates(dates_text_element.text)

        # # Extract the location (optional) from the nested experience
        # location_xpath = ".//span[contains(@class, 't-14') and contains(@class, 't-normal') and contains(@class, 't-black--light')][2]"
        # try:
        #     location_element = section.find_element(By.XPATH, location_xpath)
        #     location_text = location_element.text.strip()
        #
        #     # Replace newline characters with spaces
        #     location_text = location_text.replace('\n', ' ')
        #
        #     # Remove any duplicate entries
        #     location_parts = location_text.split()
        #     unique_location_parts = list(dict.fromkeys(location_parts))
        #     nested_experience_data['location'] = ' '.join(unique_location_parts)

        # except NoSuchElementException:
        #     nested_experience_data['location'] = ''

        # print('nested exp:::',nested_experience_data)
        return nested_experience_data

    except NoSuchElementException as e:
        print(f"Required element not found in nested experience. Details: {e}")
    except Exception as e:
        print(f"An error occurred while processing the nested experience: {e}")

    return nested_experience_data

def scrape_experience_details(driver,show_more_button):

    experiences=[]

    try:
        ul_element = driver.find_element(By.XPATH, '//*[@id="profile-content"]/div/div[2]/div/div/main/section/div[2]/div/div[1]/ul')
        print("Parent ul found")

        experience_sections = ul_element.find_elements(By.XPATH, "./li")
        experience=scrape_experience(driver,experience_sections,show_more_button)
        return experience

    except TimeoutException:
        print("The 'ul' element was not found or the page took too long to load.")
    except NoSuchElementException:
        print("The 'ul' element was not found on the page.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return experiences


def scrape_experience(driver, li_list, show_more_button):
    time.sleep(random.uniform(7, 10))
    experiences = []

    try:
        for section in li_list:
            try:
                experience = {}
                title_element = section.find_element(By.XPATH, ".//div[contains(@class, 't-bold')]//span[1]")
                company_para = clean_text(title_element.text)

                # Handle deeply nested experience entries
                if show_more_button and section.find_elements(By.XPATH, ".//div/div/div/div/ul/li/div/div/div/ul/li"):
                    next_nested_li = section.find_elements(By.XPATH, ".//div/div/div/div/ul/li/div/div/div/ul/li")
                    if next_nested_li:
                        for li in next_nested_li:
                            next_nested_experience_data = nested_experience(li, company_para)
                            if next_nested_experience_data not in experiences:
                                experiences.append(next_nested_experience_data)
                    continue

                # Handle nested experience entries
                nested_li = section.find_elements(By.XPATH, ".//div/div/div/ul/li[span]")
                if nested_li:
                    for li in nested_li:
                        nested_experience_data = nested_experience(li, company_para)
                        if nested_experience_data not in experiences:
                            experiences.append(nested_experience_data)
                    continue
                company_name_element = section.find_element(By.XPATH,
                                                            ".//span[contains(@class, 't-14') and contains(@class, 't-normal') and not(contains(@class, 't-black--light'))][1]")
                company_name_text = clean_text(company_name_element.text)
                # Remove any extraneous job type info
                company_name_text = re.split(r'Full-time|Part-time|Internship', company_name_text)[0].strip()
                experience['company'] = company_name_text
                # Job title and company name extraction
                experience['title'] = company_para
                # Extract work_detail if no nested list or "Show More"
                try:
                    work_detail = section.find_element(By.XPATH,
                    ".//div[contains(@class, 'display-flex full-width')]//div[contains(@class, 't-14 t-normal t-black')]//span[@aria-hidden='true'] ")
                    experience['description'] = clean_text(work_detail.text) if work_detail else ''
                except NoSuchElementException:
                    experience['description'] = ''
                # Location extraction with filtering of "Hybrid," "Remote," or "On-site"
                try:
                    location_element = section.find_element(By.XPATH,
                                                            ".//span[contains(@class, 't-14') and contains(@class, 't-normal') and contains(@class, 't-black--light')][2]")
                    location_text = clean_text(location_element.text).replace('\u00b7', '').strip()
                    location_text = re.split(r'Hybrid|Remote|On-site', location_text)[0].strip()
                    experience['location'] = location_text
                except NoSuchElementException:
                    experience['location'] = ''

                # Start and end dates
                dates_text_element = section.find_element(By.XPATH,
                                                        ".//span[contains(@class, 't-black--light') and contains(@class, 't-14') and contains(@class, 't-normal')][1]")
                experience['startDate'], experience['endDate'] = parse_dates(dates_text_element.text)

                # Append only unique experiences
                if experience not in experiences:
                    experiences.append(experience)

            except NoSuchElementException as e:
                print(f"Required element not found in this section. Skipping this section. Details: {e}")
            except Exception as e:
                print(f"An error occurred while processing this section: {e}")

    except TimeoutException:
        print("The 'ul' element was not found or the page took too long to load.")
    except NoSuchElementException:
        print("The 'ul' element was not found on the page.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return experiences



def extract_experience(driver):
    time.sleep(random.uniform(7, 10))
    experiences = []

    try:
        experience_section = driver.find_element(By.XPATH, "//h2[contains(@class,'pvs-header__title')]//span[contains(@aria-hidden,'true')][normalize-space()='Experience']/ancestor::section")
        print("Experience header found")
        # Locate the parent ul element
        ul_element = experience_section.find_element(By.XPATH, ".//ul")
        print("Parent ul found")

        show_more_button = experience_section.find_elements(By.XPATH, ".//div[contains(@class,'pvs-list__footer-wrapper')]//a[contains(@class, 'optional-action-target-wrapper')]")
        # print('Button Found')
        li_list = ul_element.find_elements(By.XPATH, "./li")
        print(f"Number of PARENT <li> elements found: {len(li_list)}")
        if show_more_button:
            print("Button present")
            # Click on the button to load the full education details page
            show_more_button[0].click()
            print("Button clicked, navigating to full experience page...")

            # Wait for the new page to load
            time.sleep(random.uniform(5, 8))  # Adjust time if necessary

            # Print confirmation that the new page has loaded
            print("Page loaded")
            experience=scrape_experience_details(driver,show_more_button)

            back_button= driver.find_element(By.XPATH, "//button[@aria-label='Back to the main profile page']")
            print('BACK button found')
            back_button.click()
            print('button clicked')
            time.sleep(random.uniform(7, 12))
            return experience
            # experiences = scrape_experience(driver)

        else:
            # If no "Show All" button is present, scrape the current page
            experience = scrape_experience(driver,li_list,show_more_button)
            return experience

    except TimeoutException:
        print("The 'ul' element was not found or the page took too long to load.")
    except NoSuchElementException:
        print("The 'ul' element was not found on the pageeeeeeeeee.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    return experiences
# Call the function with your driver instance

def scrape_profile(driver, url):
    driver.get(url)
    time.sleep(random.uniform(2, 4))
    profile_data = {}

    try:
        profile_data['profile_name'] = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//h1"))
        ).text

        # profile_data['location'] = clean_text(driver.find_element(By.CSS_SELECTOR, ".text-body-small").text)
        try:
            location_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//span[@class='text-body-small inline t-black--light break-words']"))
            )
            profile_data['location'] = location_element.text
        except Exception as e:
            print("Error: ", e)
        profile_data['workExperience'] = extract_experience(driver)

    except NoSuchElementException as e:
        print(f"Error extracting profile data: {e}")
    return profile_data

def main():
    driver = init_driver()
    login_to_linkedin(driver)

    with open("profile.json", 'r') as file:
        linkedin_urls = json.load(file)

    all_profiles_data = []
    for url in linkedin_urls:
        print(f"Scraping profile: {url}")
        try:
            profile_data = scrape_profile(driver, url)
            all_profiles_data.append(profile_data)
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    with open("output.json", "w", encoding="utf-8") as json_file:
        json.dump(all_profiles_data, json_file, ensure_ascii=False, indent=4)

    driver.quit()

if __name__ == "__main__":
    main()