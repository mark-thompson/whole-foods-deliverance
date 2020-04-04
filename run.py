import argparse
import logging
import pickle
import os
from time import sleep
from random import uniform
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import chromedriver_binary

from config import Config
from notify import send_sms, send_telegram, alert, annoy

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def store_cookies(driver, path=Config.PKL_PATH):
    cookies = driver.get_cookies()
    if cookies:
        log.info('Writing session cookie to: ' + path)
        with open(path, 'wb') as file:
            pickle.dump(cookies, file)


def load_cookies(driver, path=Config.PKL_PATH):
    log.info('Reading cookie values from: ' + path)
    with open(path, 'rb') as file:
        cookies = pickle.load(file)
    if cookies:
        log.info('Found {} cookie values'.format(len(cookies)))
        for c in cookies:
            if c.get('expiry'):
                c['expiry'] = int(c['expiry'])
            driver.add_cookie(c)


def wait_for_element(driver, locator, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
    except TimeoutException:
        log.error("Timed out waiting for target element: {}".format(locator))
        raise


def get_element(driver, locator, **kwargs):
    wait_for_element(driver, locator, **kwargs)
    return(driver.find_element(*locator))


def navigate(driver, locator, **kwargs):
    log.info("Navigating via locator: {}".format(locator))
    get_element(driver, locator, **kwargs).click()


def is_logged_in(driver):
    try:
        text = get_element(driver, Config.Locators.LOGIN).text
        return(Config.Patterns.NOT_LOGGED_IN not in text)
    except Exception:
        return(False)


def slots_available(driver):
    slots = get_element(driver, Config.Locators.SLOTS)
    return(Config.Patterns.NO_SLOTS not in slots.text)


def navigate_to_slot_select(driver):
    navigate(driver, (By.ID, 'nav-cart'))
    navigate(driver, (
        By.XPATH,
        "//*[contains(text(),'{}')]/..".format(Config.Patterns.WF_CHECKOUT)
    ))
    navigate(driver, (
        By.XPATH,
        "//span[contains(@class, 'byg-continue-button')]"
    ))
    navigate(driver, (By.ID, 'subsContinueButton'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="wf-deliverance")
    parser.add_argument('--force_login', '-f', action='store_true',
                        help="Login and refresh session cookie if it exists")
    args = parser.parse_args()

    log.info('Invoking Selenium Chrome webdriver')
    driver = webdriver.Chrome()
    log.info('Navigating to Amazon')
    driver.get(Config.BASE_URL)

    if args.force_login or not os.path.exists(Config.PKL_PATH):
        # Login and capture Amazon cookie values...
        log.info('Waiting for user login...')
        elapsed = 0
        while not is_logged_in(driver):
            wait = 1
            sleep(wait)
            elapsed += wait
            if is_logged_in(driver):
                break
            if not elapsed % 60:
                alert('Log in to continue')
        log.info('Logged in')
        store_cookies(driver)
    else:
        # ...or load from storage
        load_cookies(driver)
        driver.refresh()
        if is_logged_in(driver):
            log.info('Successfully logged in via stored cookie')
        else:
            raise RuntimeError('Error logging in with stored cookie.')

    # Navigate from (presumably) BASE_URL to SLOT_URL
    log.info('Navigating to delivery slot selection')
    navigate_to_slot_select(driver)
    # Check for delivery slots
    if slots_available(driver):
        annoy()
        alert('Delivery slots available. What do you need me for?', 'Sosumi')
    while not slots_available(driver):
        sleep(uniform(20, 30))
        driver.refresh()
        if slots_available(driver):
            log.info('Found slots :D')
            alert('Delivery slots found', 'Blow')
            send_sms(get_element(driver, Config.Locators.SLOTS).text)
            send_telegram(get_element(driver, Config.Locators.SLOTS).text)
            break
        else:
            log.info('No slots :( waiting...')
    try:
        # Allow time to check out manually
        sleep(900)
    except KeyboardInterrupt:
        log.warning('Slumber disturbed')
    log.info('Closing webdriver')
    driver.close()
