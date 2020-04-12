import argparse
import logging
import os
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
import chromedriver_binary

import config
from slots import SlotElement
from nav import RouteRedirectException
from notify import send_sms, send_telegram, alert, annoy, conf_dependent
from utils import (get_element, is_logged_in, wait_for_auth, jitter,
                   load_session_data, dump_source)

log = logging.getLogger(__name__)


def get_slots(driver, site_config):
    log.info('Checking for available slots')
    slot_container = get_element(driver, site_config.Locators.SLOT_CONTAINER)
    slotselect_elems = slot_container.find_elements(
        *site_config.Locators.SLOT_SELECT
    )
    slots = []
    for cont in slotselect_elems:
        id = cont.get_attribute('id')
        date_elem = driver.find_element(
            By.XPATH,
            "//button[@name='{}']".format(id)
        )
        for slot in cont.find_elements(*site_config.Locators.SLOT):
            slots.append(SlotElement(slot, date_elem))
    if slots:
        log.info('Found {} slots: \n{}'.format(
            len(slots), '\n'.join([s.full_name for s in slots])
        ))
    return(slots)


def clean_slotname(slot_or_str):
    if isinstance(slot_or_str, SlotElement):
        name = slot_or_str.full_name
    else:
        name = slot_or_str
    return name.lower().replace(' ', '')


@conf_dependent('slot_preference')
def get_prefs_from_conf(conf):
    log.info("Creating prefs from conf dict: {}".format(conf))
    prefs = []
    for day, windows in conf.items():
        for window in windows:
            if window.lower() == 'any':
                prefs.append(day.lower())
            else:
                prefs.append(clean_slotname('::'.join([day, window])))
    return(prefs)


def slots_available(driver, site_config, prefs):
    slots = get_slots(driver, site_config)
    preferred_slots = []
    if slots and prefs:
        log.info('Comparing available slots to prefs')
        for cmp in prefs:
            preferred_slots.extend(
                [s for s in slots if clean_slotname(s).startswith(cmp)]
            )
        if preferred_slots:
            log.info('Found {} preferred slots: {}'.format(
                len(preferred_slots),
                '\n'+'\n'.join([p.full_name for p in preferred_slots])
            ))
        return preferred_slots
    else:
        return slots


def generate_message(slots, checkout):
    text = []
    for slot in slots:
        date = str(slot._date_element)
        if date not in text:
            text.extend(['', date])
        text.append(str(slot))
    if checkout:
        text.extend(
            ['', 'Will attempt to checkout using slot:', slots[0].full_name]
        )
    if text:
        return '\n'.join(["Whole Foods delivery slots found!", *text])


def main_loop(driver, args):
    log.info('Reading slot preferences from conf')
    slot_prefs = get_prefs_from_conf()
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
    # v-- Change this dynamically when more site configs exist
    site_config = config.WholeFoods
    # Navigate to slot select
    site_config.Routes.SLOT_SELECT.navigate(driver)
    slots = slots_available(driver, site_config, slot_prefs)
    if slots:
        annoy()
        alert('Delivery slots available. What do you need me for?', 'Sosumi')
    while not slots:
        log.info('No slots found :( waiting...')
        jitter(25)
        driver.refresh()
        slots = slots_available(driver, site_config, slot_prefs)
        if slots:
            alert('Delivery slots found')
            message_body = generate_message(slots, args.checkout)
            send_sms(message_body)
            send_telegram(message_body)
            if not args.checkout:
                break
            checked_out = False
            while not checked_out:
                try:
                    log.info('Attempting to select slot and checkout')
                    log.info('Selecting slot: ' + slots[0].full_name)
                    slots[0].select(driver)
                    site_config.Routes.CHECKOUT.navigate(driver)
                    checked_out = True
                    alert('Checkout complete', 'Hero')
                except RouteRedirectException:
                    log.warning('Checkout failed: Redirected to slot select')
                    slots = slots_available(driver, site_config,
                                            slot_prefs)
                    if not slots:
                        break


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="wf-deliverance")
    parser.add_argument('--force_login', '-f', action='store_true',
                        help="Login and refresh session data if it exists")
    parser.add_argument('--checkout', '-c', action='store_true',
                        help="Select first available slot and checkout")
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO if not args.debug else logging.DEBUG
    )
    log.info('Invoking Selenium Chrome webdriver')
    driver = webdriver.Chrome()
    try:
        main_loop(driver, args)
    except WebDriverException:
        if args.debug:
            dump_source(driver)
        raise
    try:
        # allow time to check out manually
        min = 15
        log.info('Sleeping for {} minutes (press Ctrl+C to close)'.format(min))
        sleep(min*60)
    except KeyboardInterrupt:
        log.warning('Slumber disturbed')
    log.info('Closing webdriver')
    driver.close()
