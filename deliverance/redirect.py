import logging
from time import sleep
from datetime import datetime
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from .exceptions import RouteRedirect, UnhandledRedirect, ItemOutOfStock
from .utils import wait_for_element, click_when_enabled, dump_source
from .notify import alert

log = logging.getLogger(__name__)


def wait_for_auth(browser, timeout_mins=10):
    t = datetime.now()
    alerted = []
    if browser.is_logged_in():
        log.debug('Already logged in')
        return
    log.info('Waiting for user login...')
    while not browser.is_logged_in():
        elapsed = int((datetime.now() - t).total_seconds() / 60)
        if browser.is_logged_in():
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


def handle_oos(browser, timeout_mins=10):
    try:
        browser.save_removed_items()
    except Exception:
        log.error('Could not save removed items')
    if browser.args.ignore_oos:
        log.warning('Attempting to proceed through OOS alert')
        click_when_enabled(
            browser.driver,
            wait_for_element(browser.driver, browser.Locators.OOS_CONTINUE)
        )
    else:
        t = datetime.now()
        alert(
            "An item is out of stock. Press continue if you'd like to proceed",
            'Sosumi'
        )
        while browser.Patterns.OOS_URL in browser.current_url:
            if int((datetime.now() - t).total_seconds()) > timeout_mins*60:
                raise ItemOutOfStock(
                    'Encountered OOS alert and timed out waiting for user '
                    'input\n Use `ignore-oos` to bypass these alerts'
                )
            sleep(1)


def handle_throttle(browser, timeout_mins=10):
    alert('Throttled', 'Sosumi')
    # Dump source until we're sure we have correct locator for continue button
    dump_source(browser.driver)
    try:
        click_when_enabled(
            browser.driver,
            wait_for_element(browser.driver,
                             browser.Locators.THROTTLE_CONTINUE),
            timeout=60
        )
    except Exception as e:
        log.error(e)
    t = datetime.now()
    while browser.Patterns.THROTTLE_URL in browser.current_url:
        if int((datetime.now() - t).total_seconds()) > timeout_mins*60:
            raise UnhandledRedirect(
                'Throttled and timed out waiting for user input'
            )
        sleep(1)


def handle_redirect(browser, valid_dest=None, timeout=None, route=None):
    current = browser.current_url
    log.warning("Redirected to: '{}'".format(current))

    if browser.Patterns.AUTH_URL in current:
        wait_for_auth(browser)
    elif browser.Patterns.OOS_URL in current:
        handle_oos(browser)
    elif browser.Patterns.THROTTLE_URL in current:
        handle_throttle(browser)
        raise RouteRedirect('Redirected after throttle')
    elif route and current == route.route_start:
        if not route.waypoints_reached:
            browser.driver.refresh()
        raise RouteRedirect()
    elif valid_dest and timeout:
        log.warning(
            'Handling unknown redirect (timeout in {}s)'.format(timeout)
        )
        try:
            WebDriverWait(browser.driver, timeout).until(
                EC.url_matches('|'.join(valid_dest))
            )
        except TimeoutException:
            raise UnhandledRedirect(
                "Timed out waiting for redirect to a valid dest\n"
                "Current URL: '{}'".format(browser.current_url)
            )
    else:
        raise UnhandledRedirect()
