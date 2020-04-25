import logging
import toml
from time import sleep
from random import uniform
from datetime import datetime
from urllib.parse import urlparse
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (ElementClickInterceptedException,
                                        TimeoutException)

import config
from deliverance.exceptions import ItemOutOfStock, UnhandledRedirect
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


####################
# Redirect Handlers
##################

def handle_oos(driver, ignore_oos, timeout_mins=10):
    try:
        save_removed_items(driver)
    except Exception:
        log.error('Could not save removed items')
    if ignore_oos:
        log.warning('Attempting to proceed through OOS alert')
        click_when_enabled(
            driver,
            wait_for_element(driver, config.Locators.OOS_CONTINUE)
        )
    else:
        t = datetime.now()
        alert(
            "An item is out of stock. Press continue if you'd like to proceed",
            'Sosumi'
        )
        while config.Patterns.OOS_URL in remove_qs(driver.current_url):
            if int((datetime.now() - t).total_seconds()) > timeout_mins*60:
                raise ItemOutOfStock(
                    'Encountered OOS alert and timed out waiting for user '
                    'input\n Use `ignore-oos` to bypass these alerts'
                )
            sleep(1)


def handle_throttle(driver, timeout_mins=10):
    alert('Throttled', 'Sosumi')
    # Dump source until we're sure we have correct locator for continue button
    dump_source(driver)
    try:
        click_when_enabled(
            driver,
            wait_for_element(driver, config.Locators.THROTTLE_CONTINUE),
            timeout=60
        )
    except Exception as e:
        log.error(e)
    t = datetime.now()
    while config.Patterns.THROTTLE_URL in remove_qs(driver.current_url):
        if int((datetime.now() - t).total_seconds()) > timeout_mins*60:
            raise UnhandledRedirect(
                'Throttled and timed out waiting for user input'
            )
        sleep(1)
