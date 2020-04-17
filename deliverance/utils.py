import logging
import pickle
import toml
import os
from time import sleep
from random import uniform
from datetime import datetime
from urllib.parse import urlparse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        TimeoutException)

import config
from deliverance.notify import alert

log = logging.getLogger(__name__)


def remove_qs(url):
    """Remove URL query string the lazy way"""
    return url.split('?')[0]


def jitter(seconds, pct=20):
    """This seems unnecessary"""
    sleep(uniform(seconds*(1-pct/100), seconds*(1+pct/100)))


def timestamp():
    return datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')


def dump_source(driver):
    filename = 'source_dump{}_{}.html'.format(
        urlparse(driver.current_url).path.replace('/', '-')
        .replace('.html', ''),
        timestamp()
    )
    log.info('Dumping page source to: ' + filename)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(driver.page_source)


def save_removed_items(driver):
    """Writes OOS items that have been removed from cart to a TOML file"""
    removed = []
    for item in driver.find_elements(*config.Locators.OOS_ITEM):
        if config.Patterns.OOS in item.text:
            removed.append({
                'text': item.text.split(config.Patterns.OOS)[0],
                'product_id': item.find_element_by_xpath(
                        ".//*[starts-with(@name, 'asin')]"
                    ).get_attribute('value')
            })
    if not removed:
        log.warning("Couldn't detect any removed items to save")
    else:
        fp = 'removed_items_{}.toml'.format(timestamp())
        log.info('Writing {} removed items to: {}'.format(len(removed), fp))
        with open(fp, 'w', encoding='utf-8') as f:
            toml.dump({'items': removed}, f)


###########
# Elements
#########

class element_clickable:
    """An expected condition for use with WebDriverWait"""

    def __init__(self, element):
        self.element = element

    def __call__(self, driver):
        if self.element.is_displayed() and self.element.is_enabled():
            return self.element
        else:
            return False


def wait_for_elements(driver, locator, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
    except TimeoutException:
        log.error("Timed out waiting for target element: {}".format(locator))
        raise
    return driver.find_elements(*locator)


def wait_for_element(driver, locator, **kwargs):
    return wait_for_elements(driver, locator, **kwargs)[0]


def click_when_enabled(driver, element, timeout=10):
    element = WebDriverWait(driver, timeout).until(
        element_clickable(element)
    )
    try:
        driver.execute_script("arguments[0].scrollIntoView();", element)
        element.click()
    except ElementClickInterceptedException:
        delay = 1
        log.warning('Click intercepted. Waiting for {}s'.format(delay))
        sleep(delay)
        element.click()

#######
# Auth
######


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


def is_logged_in(driver):
    if remove_qs(driver.current_url) == config.BASE_URL:
        try:
            text = wait_for_element(driver, config.Locators.LOGIN).text
            return config.Patterns.NOT_LOGGED_IN not in text
        except Exception:
            return False
    elif config.Patterns.AUTH_URL in remove_qs(driver.current_url):
        return False
    else:
        # Lazily assume true if we are anywhere but BASE_URL or AUTH pattern
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
    store_session_data(driver)


def login_flow(driver, force_login):
    log.info('Navigating to ' + config.BASE_URL)
    driver.get(config.BASE_URL)

    if force_login or not os.path.exists(config.PKL_PATH):
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
