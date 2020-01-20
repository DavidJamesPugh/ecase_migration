"""
-Processing and printing of admission/administrative files,
from eCase or from established files on the network

Tests in tests.py TestingEcaseReportsAvailable for if the reports exist
"""

import datetime
import os
import time
from urllib.request import urlretrieve

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException, \
    SessionNotCreatedException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

import constants
import downloader_support_functions
import button_functions


def ecase_login():
    """
        Establishes an instance of chrome in selenium.
        Navigates to eCase and logs in with credentials provided in constants.py
    """
    prefs = {'download.default_directory': rf'{constants.DOWNLOADS_DIR}'}
    options = webdriver.ChromeOptions()
    options.add_experimental_option('prefs', prefs)
    try:
        driver = webdriver.Chrome(options=options)
    except SessionNotCreatedException as e:
        button_functions.popup_error(f"{e}.\n"
                                     f"Please contact the Datatec to update "
                                     f"local ChromeDriver to the latest version")
        return

    driver.get(f'{constants.ECASE_URL}')

    user_name = driver.find_element_by_id('mod_login_username')
    user_password = driver.find_element_by_id('mod_login_password')
    user_name.clear()
    user_name.send_keys(f'{constants.ECASE_USERNAME}')
    user_password.clear()
    user_password.send_keys(f'{constants.ECASE_PASSWORD}')
    driver.find_element_by_name('loginButton').click()

    return driver


def ecase_data(driver):
    """
        Navigates to the report screen,
        and downloads all reports with the keyword ‘data’
    """
    driver.get(f'{constants.ECASE_URL}?action=reportGenerator&active=1')
    driver.find_element_by_id('filter-report-name').send_keys('data')

    driver.implicitly_wait(10)
    buttons = driver.find_elements_by_id('generate')

    for button in buttons:
        button.click()
        time.sleep(2)
        driver.implicitly_wait(10)


def ecase_pi_risk(driver):
    """
    Downloads the pir_code from ecase reports that contains the customer codes for each resident
    """
    # Download the csv with all customer codes
    driver.get(f'{constants.ECASE_URL}?action=reportGenerator&active=1')
    driver.find_element_by_id('filter-report-name').send_keys('pir_code')
    while not os.path.isfile(rf'{constants.DOWNLOADS_DIR}\pir_code.csv'):
        try:
            driver.find_element_by_id('generate').click()
        except NoSuchElementException:
            continue
        except ElementClickInterceptedException:
            continue


def care_plan_audits_download(driver, wing: str):
    """
        Clicks the ‘Generate’ button,
        and enters the wing into the filter box,
        and downloads the subsequent report.
        Should be used in a loop of wings,
        in conjunction with eCase_Care_Plans_Audit.
        This is used in a loop within ButtonFunctions.py, to
        pass in each wing and download the wing's file. This file
        is then used to create a file with a sheet for each area
        and their care plan status.
    """
    driver.get(f'{constants.ECASE_URL}?action=reportGenerator&active=1')
    driver.find_element_by_id('filter-report-name').send_keys('cp_')
    driver.implicitly_wait(10)
    driver.find_element_by_id('generate').click()
    driver.find_element_by_id('clause-field-0').send_keys(wing)
    driver.find_element_by_id('btn-generate').click()
    time.sleep(2)


def main_bowel_report(driver, wing: str, age: int):
    """
    Downloads file of bowel reports of specified wing,
    for the previous *age* month in the past i.e, 1 = previous month,
    2 = 2 months ago etc
    :param driver: selenium driver object
    :param wing: area
    :param age: number of months in the past
    :return:
    """
    driver.get(f'{constants.ECASE_URL}?action=reportGenerator&active=1')
    driver.find_element_by_id('filter-report-name').send_keys('bowel_report')
    driver.implicitly_wait(10)

    month = (datetime.datetime.now() - datetime.timedelta(days=30 * age)).month
    year = (datetime.datetime.now() - datetime.timedelta(days=30 * age)).year
    month_spec = downloader_support_functions.date_selector(month, year)
    count = age

    wait = WebDriverWait(driver, 10)
    driver.implicitly_wait(10)
    driver.find_elements_by_id('generate')[0].click()

    fields = driver.find_elements_by_id('clause-field-0')
    date_from_fields = driver.find_elements_by_xpath('//*[@id="clause-field-0-date"]')
    date_to_fields = driver.find_elements_by_xpath('//*[@id="clause-field-1-date "]')
    fields[0].send_keys(wing)
    date_from_fields[1].click()

    downloader_support_functions.click_previous_month_button(driver, count)
    # finding the first available selectable date, and hovering to it
    first_available_date = wait.until(
        ec.element_to_be_clickable((
            By.CSS_SELECTOR, f"body > div.Zebra_DatePicker.dp_visible > "
                             f"table.dp_daypicker > tbody > tr:nth-child(2)"
                             f" > td:nth-child({month_spec[1]})")))

    ActionChains(driver).move_to_element(first_available_date).perform()
    driver.find_element_by_css_selector(f"body > div.Zebra_DatePicker.dp_visible >"
                                        f" table.dp_daypicker > tbody > "
                                        f"tr:nth-child(2) > td:nth-child({month_spec[1]}) ").click()
    date_to_fields[1].click()

    downloader_support_functions.click_previous_month_button(driver, count)

    driver.find_element_by_css_selector(
        "body > div.Zebra_DatePicker.dp_visible > table.dp_daypicker > "
        f"tbody > tr:nth-child({month_spec[0]}) > td:nth-child({month_spec[2]}) ").click()
    driver.implicitly_wait(10)
    driver.find_element(By.XPATH,
                        '//*[@id="btn-generate"]').click()


def nhi_check(driver, nhi):
    """

    :param driver:
    :param nhi:
    :return:
    """
    driver.get(f'{constants.ECASE_URL}?action=search')
    driver.find_element_by_id('activeAndInactive').click()
    nhi = nhi.upper()
    nhi_field = driver.find_element_by_name('txtNHINumber')
    nhi_field.send_keys(nhi)
    driver.find_element_by_id('searchButton').click()

    try:
        driver.find_element(By.XPATH, '//*[@id="formTab1"]/div[2]/h1/span/div/a[3]/u')

    except NoSuchElementException:
        driver.quit()
        if os.path.isfile(rf'{constants.DOWNLOADS_DIR}\fs_Res.csv'):
            os.remove(rf'{constants.DOWNLOADS_DIR}\fs_Res.csv')
        if os.path.isfile(rf'{constants.DOWNLOADS_DIR}\fs_Con.csv'):
            os.remove(rf'{constants.DOWNLOADS_DIR}\fs_Con.csv')
        return button_functions.popup_error("NHI is incorrect, please check you've entered it correctly "
                                            "and the resident is set up correctly")


def preferred_name_and_image(driver, nhi: str):
    r"""
        Gets the resident’s preferred name,
        and saves it in a text file in the eCase\Downloads folder,
        named p_name.txt
    """
    nhi_check(driver, nhi)

    try:
        p_name = driver.find_element_by_name('PreferredName').get_attribute('value')
        file = open(rf'{constants.DOWNLOADS_DIR}\p_name.txt', "w+")
        file.write(p_name)
        file.close()

        img = driver.find_element_by_id('resImage')
        src = img.get_attribute('src')
        file_ext = str.split(src, '.')
        urlretrieve(src,
                    rf'{constants.DOWNLOADS_DIR}\{nhi} Photo.{file_ext[-1]}')

    except NoSuchElementException:
        pass


def resident_contacts(driver, nhi: str):
    """
        Downloads all reports starting with the name ‘fs’.
        Will be Resident info, and Resident Contact’s info
    """
    driver.get(f'{constants.ECASE_URL}?action=reportGenerator&active=1')
    driver.find_element_by_id('filter-report-name').send_keys('fs_')
    driver.implicitly_wait(2)
    buttons = driver.find_elements_by_id('generate')

    while not os.path.isfile(rf'{constants.DOWNLOADS_DIR}\fs_Res.csv'):
        try:
            for button in buttons:
                button.click()
                driver.find_element_by_id('clause-field-0').send_keys(nhi)
                driver.find_element_by_id('btn-generate').click()
                time.sleep(2)
        except NoSuchElementException:
            button_functions.popup_error("Please recheck the NHI number for correctness, and "
                                         "then contact the Datatec; cannot find the resident")
        except ElementClickInterceptedException:
            continue


def doctor_numbers_download(driver):
    """
        Downloads the report with ‘doctor’ in the name.
        Report has a list of residents and who their doctor is.
    """
    driver.get(f'{constants.ECASE_URL}?action=reportGenerator&active=1')
    driver.find_element_by_id('filter-report-name').send_keys('doctor_Numbers')

    driver.implicitly_wait(10)
    driver.find_elements_by_id('generate')[0].click()


def ecase_birthdays(driver):
    """
        Downloads the report with ‘birthdayList’ in the name.
        Report has the list of resident birth dates
    """
    driver.get(f'{constants.ECASE_URL}?action=reportGenerator&active=1')
    driver.find_element_by_id('filter-report-name').send_keys('birthdayList_MCF')
    driver.implicitly_wait(10)
    driver.find_element_by_id('generate').click()


def care_level_csv(driver):
    """
        Downloads reports with ‘pod_’ in the name. 
        Downloads the report ‘pod_MCF’, and ‘pod_Residents’,
        both with the level of care for each resident
    """
    driver.get(f'{constants.ECASE_URL}?action=reportGenerator&active=1')
    driver.find_element_by_id('filter-report-name').send_keys('pod_')
    driver.implicitly_wait(10)
    buttons = driver.find_elements_by_id('generate')
    time.sleep(5)
    for button in buttons:
        button.click()
        time.sleep(2)


def ecase_movements(driver):
    """
        Downloads CSV of ‘temp_movements’.
        Handles the selecting of dates within eCase date selector,
        selects from 1 July 2018, till the end of the current month.
    """
    driver.get(f'{constants.ECASE_URL}?action=reportGenerator&active=1')
    driver.find_element_by_id('filter-report-name').send_keys('temp_movements')

    month_spec = downloader_support_functions.date_selector(datetime.datetime.now().month,
                                                            datetime.datetime.now().year)

    driver.implicitly_wait(10)
    driver.find_elements_by_id('generate')[0].click()

    date_to_fields = driver.find_elements_by_xpath('//*[@id="clause-field-1-date "]')

    date_to_fields[0].click()

    # clicking the date that we hovered over
    driver.find_element_by_css_selector(f"body > div.Zebra_DatePicker.dp_visible >"
                                        f" table.dp_daypicker > tbody > "
                                        f"tr:nth-child({month_spec[0]}) > "
                                        f"td:nth-child({month_spec[2]})").click()

    driver.implicitly_wait(10)
    driver.find_element(By.XPATH,
                        '//*[@id="btn-generate"]').click()
