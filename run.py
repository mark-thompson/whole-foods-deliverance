import argparse
import logging
import os
from time import sleep
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import chromedriver_binary

import config
import utils
from slots import SlotElement
from nav import NavigationException
from notify import send_sms, send_telegram, alert, annoy

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_element(driver, locator, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
    except TimeoutException:
        log.error("Timed out waiting for target element: {}".format(locator))
        raise
    return driver.find_element(*locator)


def is_logged_in(driver):
    if utils.remove_qs(driver.current_url) == config.BASE_URL:
        try:
            text = get_element(driver, config.Locators.LOGIN).text
            return config.Patterns.NOT_LOGGED_IN not in text
        except Exception:
            return False
    elif (utils.remove_qs(driver.current_url) == config.AUTH_URL
          or config.BASE_URL+'ap/cvf' in driver.current_url):
        return False
    else:
        # Lazily assume true if we are anywhere but BASE_URL and AUTH_URL
        return True


def wait_for_auth(driver, timeout_mins=10):
    t = datetime.now()
    alerted = []
    if is_logged_in(driver):
        log.debug('Already logged in')
        return
    log.info('Waiting for user login...')
    while not is_logged_in(driver):
        elapsed = int((datetime.now() - t).total_seconds() / 60)
        if is_logged_in(driver):
            break
        elif elapsed > timeout_mins:
            raise RuntimeError(
                'Timed out waiting for login (>= {}min)'.format(timeout_mins)
            )
        elif elapsed not in alerted:
            alerted.append(elapsed)
            alert('Log in to proceed')
        sleep(1)
    log.info('Logged in')
    utils.store_session_data(driver)


def navigate(driver, locator, dest, timeout=5):
    log.info("Navigating via locator: {}".format(locator))
    elem = get_element(driver, locator, timeout=timeout)
    utils.jitter(.8)
    elem.click()
    try:
        WebDriverWait(driver, timeout).until(
            EC.staleness_of(elem)
        )
    except TimeoutException:
        pass
    if utils.remove_qs(driver.current_url) == config.BASE_URL + dest:
        log.info("Navigated to '{}'".format(dest))
    else:
        raise NavigationException(
            "Navigation to '{}' failed".format(dest)
        )


def navigate_route(driver, route):
    route_start = route.pop(0)
    if utils.remove_qs(driver.current_url) != route_start:
        log.info('Navigating to route start: {}'.format(route_start))
        driver.get(route_start)
    log.info('Navigating route with {} stops'.format(len(route)))
    for t in route:
        try:
            navigate(driver, t[0], t[1])
        except NavigationException:
            if utils.remove_qs(driver.current_url) == config.AUTH_URL:
                log.error('Handling login redirect')
                wait_for_auth(driver)
            else:
                raise
    log.info('Route complete')


def get_slots(driver):
    slot_container = get_element(driver, config.Locators.SLOTS)
    slotselect_elems = slot_container.find_elements(
        By.XPATH,
        ".//div[contains(@class, 'ufss-slotselect ')]"
    )
    slots = []
    for cont in slotselect_elems:
        id = cont.get_attribute('id')
        date_elem = driver.find_element(
            By.XPATH,
            "//button[@name='{}']".format(id)
        )
        for slot in cont.find_elements(
            By.XPATH,
            ".//*[contains(@class, 'ufss-slot  ufss-available')]"
        ):
            slots.append(SlotElement(slot, date_elem))
    return(slots)


def slots_available(driver):
    return len(get_slots(driver))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="wf-deliverance")
    parser.add_argument('--force_login', '-f', action='store_true',
                        help="Login and refresh session data if it exists")
    args = parser.parse_args()

    log.info('Invoking Selenium Chrome webdriver')
    driver = webdriver.Chrome()
    log.info('Navigating to ' + config.BASE_URL)
    driver.get(config.BASE_URL)

    if args.force_login or not os.path.exists(config.PKL_PATH):
        # Login and capture Amazon session data...
        wait_for_auth(driver)
    else:
        # ...or load from storage
        utils.load_session_data(driver)
        driver.refresh()
        if is_logged_in(driver):
            log.info('Successfully logged in via stored session data')
        else:
            log.error('Error logging in with stored session data')
            wait_for_auth(driver)
    # Navigate from BASE_URL to SLOT_URL
    navigate_route(driver, config.Routes.WholeFoods.SLOT_SELECT)
    # Check for delivery slots
    if slots_available(driver):
        annoy()
        alert('Delivery slots available. What do you need me for?', 'Sosumi')
    while not slots_available(driver):
        log.info('No slots found :( waiting...')
        utils.jitter(25)
        driver.refresh()
        if slots_available(driver):
            alert('Delivery slots found')
            slots = get_slots(driver)
            message_body = utils.generate_message(slots)
            send_sms(message_body)
            send_telegram(message_body)
            break
    try:
        # Allow time to check out manually
        sleep(900)
    except KeyboardInterrupt:
        log.warning('Slumber disturbed')
    log.info('Closing webdriver')
    driver.close()
