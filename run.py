import argparse
import logging
import os
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
import chromedriver_binary

import config
from slots import SlotElement
from notify import send_sms, send_telegram, alert, annoy
from utils import (get_element, is_logged_in, wait_for_auth, jitter,
                   load_session_data)

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def get_slots(driver, site_config):
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
    return(slots)


def slots_available(driver, site_config):
    return len(get_slots(driver, site_config))


def generate_message(slots, desired_slot=None):
    text = []
    for slot in slots:
        date = str(slot._date_element)
        if date not in text:
            text.extend(['', date])
        text.append(str(slot))
    if desired_slot:
        text.extend(['Will attempt to checkout using slot:',
                     desired_slot.full_name])
    if text:
        return '\n'.join(["Whole Foods delivery slots found!", *text])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="wf-deliverance")
    parser.add_argument('--force_login', '-f', action='store_true',
                        help="Login and refresh session data if it exists")
    parser.add_argument('--checkout', '-c', action='store_true',
                        help="Select first available slot and checkout")
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
    # v-- Change this dynamically when more site configs exist
    site_config = config.WholeFoods
    # Navigate from BASE_URL to SLOT_URL
    site_config.Routes.SLOT_SELECT.navigate(driver)
    # Check for delivery slots
    if slots_available(driver, site_config):
        annoy()
        alert('Delivery slots available. What do you need me for?', 'Sosumi')
    while not slots_available(driver, site_config):
        log.info('No slots found :( waiting...')
        jitter(25)
        driver.refresh()
        if slots_available(driver, site_config):
            alert('Delivery slots found')
            slots = get_slots(driver, site_config)
            if args.checkout:
                desired_slot = slots[0]
            message_body = generate_message(slots, desired_slot)
            send_sms(message_body)
            send_telegram(message_body)
            break
    if args.checkout:
        log.info('Attempting to select slot and checkout')
        slots = get_slots(driver, site_config)
        log.info('Selecting slot: ' + slots[0].full_name)
        slots[0].select(driver)
        site_config.Routes.CHECKOUT.navigate(driver)
        alert('Checkout complete', 'Hero')
        sleep(60)
    else:
        try:
            # Allow time to check out manually
            sleep(900)
        except KeyboardInterrupt:
            log.warning('Slumber disturbed')
    log.info('Closing webdriver')
    driver.close()
