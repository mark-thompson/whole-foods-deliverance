import toml
import random
import logging
from time import sleep
from functools import wraps
from datetime import datetime
from urllib.parse import urlparse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        TimeoutException)

from config import CONF_PATH

log = logging.getLogger(__name__)


def conf_dependent(conf_key):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if 'conf' not in kwargs:
                try:
                    kwargs['conf'] = toml.load(CONF_PATH)[conf_key]
                except Exception:
                    log.error("{}() requires a config file at"
                              " '{}' with key '{}'".format(func.__name__,
                                                           CONF_PATH,
                                                           conf_key))
                    return
            try:
                return func(*args, **kwargs)
            except Exception:
                log.error('Action failed:', exc_info=True)
                return
        return wrapper
    return decorator


def remove_qs(url):
    """Remove URL query string the lazy way"""
    return url.split('?')[0]


def jitter(seconds):
    """This seems unnecessary"""
    pct = abs(random.gauss(.2, .05))
    sleep(random.uniform(seconds*(1-pct), seconds*(1+pct)))


def timestamp():
    return datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')


def dump_toml(obj, name):
    filepath = '{}_{}.toml'.format(name, timestamp())
    log.info('Writing {} items to: {}'.format(len(obj), filepath))
    with open(filepath, 'w', encoding='utf-8') as f:
        toml.dump(obj, f)


def dump_source(driver):
    filename = 'source_dump{}_{}.html'.format(
        urlparse(driver.current_url).path.replace('/', '-')
        .replace('.html', ''),
        timestamp()
    )
    log.info('Dumping page source to: ' + filename)
    with open(filename, 'w', encoding='utf-8') as f:
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


class presence_of_any_elements_located(object):
    """An expected condition for use with WebDriverWait"""

    def __init__(self, locators):
        self.locators = locators

    def __call__(self, driver):
        for locator in self.locators:
            elements = driver.find_elements(*locator)
            if elements:
                return elements
        return False


def wait_for_elements(driver, locators, timeout=5):
    if not isinstance(locators, list):
        locators = [locators]
    try:
        return WebDriverWait(driver, timeout).until(
            presence_of_any_elements_located(locators)
        )
    except TimeoutException:
        log.error("Timed out waiting for target element: {}".format(locators))
        raise


def wait_for_element(driver, locators, **kwargs):
    return wait_for_elements(driver, locators, **kwargs)[0]


def get_element_text(element):
    return element.get_attribute('innerText').strip()


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
