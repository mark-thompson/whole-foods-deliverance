import argparse
import logging
import pickle
import os
import re
from time import sleep
from random import uniform
from datetime import datetime
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import chromedriver_binary

import config
from notify import send_sms, send_telegram, alert, annoy

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class NavigationException(WebDriverException):
    """Thrown when a navigation action does not reach target destination"""
    pass


def store_session_data(driver, path=config.PKL_PATH):
    data = {
        'cookies': driver.get_cookies(),
        'storage': {
            k: driver.execute_script(
                'for(var k,s=window.{}Storage,d={{}},i=0;i<s.length;++i)'
                'd[k=s.key(i)]=s.getItem(k);return d'.format(k)
            ) for k in ['local', 'session']
        }
    }
    if any(data.values()):
        log.info('Writing session data to: ' + path)
        with open(path, 'wb') as file:
            pickle.dump(data, file)
    else:
        log.warning('No session data found')


def load_session_data(driver, path=config.PKL_PATH):
    log.info('Reading session data from: ' + path)
    with open(path, 'rb') as file:
        data = pickle.load(file)
    if data.get('cookies'):
        log.info('Loading {} cookie values'.format(len(data['cookies'])))
        for c in data['cookies']:
            if c.get('expiry'):
                c['expiry'] = int(c['expiry'])
            driver.add_cookie(c)
    for _type, values in data['storage'].items():
        if values:
            log.info('Loading {} {}Storage values'.format(len(values), _type))
        for k, v in values.items():
            driver.execute_script(
                'window.{}Storage.setItem(arguments[0], arguments[1]);'.format(
                    _type
                ),
                k, v
            )


def wait_for_element(driver, locator, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
    except TimeoutException:
        log.error("Timed out waiting for target element: {}".format(locator))
        raise


def remove_qs(url):
    """Remove URL query string the lazy way"""
    return url.split('?')[0]


def jitter(seconds, pct=20):
    """This seems unnecessary"""
    sleep(uniform(seconds*(1-pct/100), seconds*(1+pct/100)))


def get_element(driver, locator, **kwargs):
    wait_for_element(driver, locator, **kwargs)
    return driver.find_element(*locator)


def is_logged_in(driver):
    if remove_qs(driver.current_url) == config.BASE_URL:
        try:
            text = get_element(driver, config.Locators.LOGIN).text
            return config.Patterns.NOT_LOGGED_IN not in text
        except Exception:
            return False
    elif remove_qs(driver.current_url) == config.AUTH_URL:
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
            log.info('Logged in')
            store_session_data(driver)
            break
        elif elapsed > timeout_mins:
            raise RuntimeError(
                'Timed out waiting for login (>= {}min)'.format(timeout_mins)
            )
        elif elapsed not in alerted:
            alerted.append(elapsed)
            alert('Log in to continue')
        sleep(1)


def navigate(driver, locator, dest, **kwargs):
    log.info("Navigating via locator: {}".format(locator))
    try:
        elem = get_element(driver, locator, **kwargs)
        jitter(.8)
        elem.click()
    except TimeoutException:
        log.error('Handling login redirect')
        if remove_qs(driver.current_url) == config.AUTH_URL:
            wait_for_auth(driver)
        else:
            raise
    if remove_qs(driver.current_url) == dest:
        log.info("Navigated to '{0}'".format(dest))
        raise NavigationException("Navigation to '{}' failed".format(dest))


def navigate_route(driver, route):
    route_start = route.pop(0)
    if remove_qs(driver.current_url) != route_start:
        log.info('Navigating to route start: {}'.format(route_start))
        driver.get(route_start)
    log.info('Navigating route with {} stops'.format(len(route)))
    for t in route:
        navigate(driver, t[0], t[1])
    log.info('Route complete')


def get_slots(driver):
    slot_container = get_element(driver, config.Locators.SLOTS)
    slotselect_elems = slot_container.find_elements(
        By.XPATH,
        ".//div[contains(@class, 'ufss-slotselect ')]"
    )
    slots = {}
    for cont in slotselect_elems:
        id = cont.get_attribute('id')
        slots[id] = {
            'date_btn': driver.find_element(
                By.XPATH,
                "//button[@name='{}']".format(id)
            ),
            'slot_btns': cont.find_elements(
                By.XPATH,
                ".//button[contains(@class, 'ufss-slot-toggle-native-button')]"
            )
        }
    return(slots)


def slots_available(driver):
    slots = get_slots(driver)
    return any([len(v['slot_btns']) for v in slots.values()])


def slots_text(slots):
    text = []
    for d in slots.values():
        if not d['slot_btns']:
            continue
        text.append('\n' + d['date_btn'].text.replace('\n', ' - '))
        for s in d['slot_btns']:
            text.append(
                re.sub(r'\n|\s\s+', ' - ',
                       s.get_attribute('innerText').strip())
            )
    if text:
        return '\n'.join(["Whole Foods delivery slots found!", *text])


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
        load_session_data(driver)
        driver.refresh()
        if is_logged_in(driver):
            log.info('Successfully logged in via stored session data')
        else:
            log.error('Error logging in with stored session data')
            wait_for_auth(driver)
    # Navigate from BASE_URL to SLOT_URL
    navigate_route(driver, config.Routes.WholeFoods.TO_SLOT_SELECT)
    # Check for delivery slots
    if slots_available(driver):
        annoy()
        alert('Delivery slots available. What do you need me for?', 'Sosumi')
    while not slots_available(driver):
        log.info('No slots found :( waiting...')
        jitter(25)
        driver.refresh()
        if slots_available(driver):
            alert('Delivery slots found')
            slots = get_slots(driver)
            message_body = slots_text(slots)
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
