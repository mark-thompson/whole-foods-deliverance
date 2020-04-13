import logging
import pickle
from time import sleep
from random import uniform
from datetime import datetime
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        TimeoutException)

import config
from notify import alert

log = logging.getLogger(__name__)


def remove_qs(url):
    """Remove URL query string the lazy way"""
    return url.split('?')[0]


def jitter(seconds, pct=20):
    """This seems unnecessary"""
    sleep(uniform(seconds*(1-pct/100), seconds*(1+pct/100)))


def dump_source(driver):
    filename = 'source_dump_{}.html'.format(
        round(datetime.utcnow().timestamp() * 1000)
    )
    log.info('Dumping page source to: ' + filename)
    with open(filename, 'w') as f:
        f.write(driver.page_source)


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


def get_element(driver, locator, timeout=5):
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located(locator)
        )
    except TimeoutException:
        log.error("Timed out waiting for target element: {}".format(locator))
        raise
    return driver.find_element(*locator)


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
            text = get_element(driver, config.Locators.LOGIN).text
            return config.Patterns.NOT_LOGGED_IN not in text
        except Exception:
            return False
    elif config.Patterns.AUTH in remove_qs(driver.current_url):
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
