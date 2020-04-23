import argparse
import logging
import toml
import re
from time import sleep
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException
from concurrent.futures import ThreadPoolExecutor

import config
from deliverance.elements import SlotElement, SlotElementMulti, CartItem
from deliverance.exceptions import Redirect, RouteRedirect
from deliverance.nav import Route, Waypoint, handle_redirect
from deliverance.notify import (send_sms, send_telegram, alert, annoy,
                                conf_dependent)
from deliverance.utils import (login_flow, wait_for_elements, jitter,
                               dump_source, remove_qs, timestamp)

log = logging.getLogger(__name__)


def build_route(site_config, route_name, parser_args):
    route_dict = site_config.routes[route_name]
    return Route(
        route_dict['route_start'],
        parser_args,
        *[Waypoint(*w) for w in route_dict['waypoints']]
    )


def clean_slotname(slot_or_str):
    if isinstance(slot_or_str, SlotElement):
        name = slot_or_str.full_name
    else:
        name = slot_or_str
    return name.lower().replace(' ', '')


@conf_dependent('slot_preference')
def get_prefs_from_conf(conf):
    log.info('Reading slot preferences from conf: {}'.format(conf))
    prefs = []
    for day, windows in conf.items():
        for window in windows:
            if window.lower() == 'any':
                if day.lower() == 'any':
                    log.info("'Any' day, 'Any' time specified. "
                             "Will look for first available slot")
                    return None
                prefs.append(day.lower())
            else:
                prefs.append(clean_slotname('::'.join([day, window])))
    return prefs


def save_cart(driver, site_config):
    filepath = '{}_cart_{}.toml'.format(
        site_config.service.replace(' ', ''),
        timestamp()
    )
    driver.get(config.BASE_URL + site_config.cart_endpoint)
    jitter(.4)
    cart = []
    for element in wait_for_elements(driver, config.Locators.CART_ITEMS):
        try:
            cart.append(CartItem(element).data)
        except Exception:
            log.warning('Failed to parse a cart item')
    if cart:
        log.info('Writing {} cart items to: {}'.format(len(cart), filepath))
        with open(filepath, 'w', encoding='utf-8') as f:
            toml.dump({'cart_item': cart}, f)  # :)


def get_slots(driver, prefs, slot_route, timeout=5):
    # Make sure we are on the slot select page. If not, nav there
    if slot_route.waypoints[-1].dest not in remove_qs(driver.current_url):
        try:
            handle_redirect(driver, slot_route.args.ignore_oos)
        except Redirect:
            slot_route.navigate(driver)
    log.info('Checking for available slots')
    preferred_slots = []
    # Wait for one of two possible slot container elements to be present
    WebDriverWait(driver, timeout).until(
        lambda driver: (
            driver.find_elements(*config.Locators.SLOT_CONTAINER)
            or driver.find_elements(*config.Locators.SLOT_CONTAINER_MULTI)
        )
    )
    # *Temporary*
    if driver.find_elements(*config.Locators.SLOT_CONTAINER_MULTI):
        log.warning('Detected multiple delivery option slot container')
        slots = []
        for e in driver.find_elements(*config.Locators.SLOT_DATE_MULTI):
            slot = SlotElementMulti(e)
            if not re.search(config.Patterns.NO_SLOTS_MULTI, slot.text):
                slots.append(str(slot._date_element))
        if slots:
            dump_source(driver)
        return slots
    slots = [
        SlotElement(e) for e in driver.find_elements(*config.Locators.SLOT)
    ]
    if slots:
        log.info('Found {} slots: \n{}'.format(
            len(slots), '\n'.join([s.full_name for s in slots])
        ))
    if slots and prefs:
        log.info('Comparing available slots to prefs')
        for cmp in prefs:
            if cmp.startswith('any'):
                _pref = [s for s in slots
                         if cmp.replace('any', '') in clean_slotname(s)]
            else:
                _pref = [s for s in slots if clean_slotname(s).startswith(cmp)]
            preferred_slots.extend(_pref)
        if preferred_slots:
            log.info('Found {} preferred slots: {}'.format(
                len(preferred_slots),
                '\n'+'\n'.join([p.full_name for p in preferred_slots])
            ))
        return preferred_slots
    else:
        return slots


def generate_message(slots, service, checkout):
    if all(isinstance(slot, str) for slot in slots):
        text = slots
    else:
        text = []
        for slot in slots:
            date = str(slot._date_element)
            if date not in text:
                text.extend(['', date])
            text.append(str(slot))
        if checkout:
            text.extend(
                ['\nWill attempt to checkout using slot:', slots[0].full_name]
            )
    if text:
        return '\n'.join([service + " delivery slots found!", *text])


def main_loop(driver, args):
    slot_prefs = get_prefs_from_conf()
    site_config = config.SiteConfig(args.service)
    login_flow(driver, args.force_login)

    if args.save_cart:
        try:
            save_cart(driver, site_config)
        except Exception:
            log.error('Failed to save cart items')
    slot_route = build_route(site_config, 'SLOT_SELECT', args)
    slot_route.navigate(driver)
    slots = get_slots(driver, slot_prefs, slot_route)
    if slots:
        annoy()
        alert('Delivery slots available. What do you need me for?', 'Sosumi')
    else:
        executor = ThreadPoolExecutor()
    while not slots:
        log.info('No slots found :( waiting...')
        jitter(config.INTERVAL)
        driver.refresh()
        slots = get_slots(driver, slot_prefs, slot_route)
        if slots:
            alert('Delivery slots found')
            message_body = generate_message(slots, args.service, args.checkout)
            executor.submit(send_sms, message_body)
            executor.submit(send_telegram, message_body)
            if not args.checkout:
                break
            checked_out = False
            log.info('Attempting to select slot and checkout')
            while not checked_out:
                try:
                    log.info('Selecting slot: ' + slots[0].full_name)
                    slots[0].select()
                    build_route(site_config, 'CHECKOUT', args).navigate(driver)
                    checked_out = True
                    alert('Checkout complete', 'Hero')
                except RouteRedirect:
                    log.warning('Checkout failed: Redirected to slot select')
                    slots = get_slots(driver, slot_prefs, slot_route)
                    if not slots:
                        break
    try:
        executor.shutdown()
    except Exception as e:
        log.error(e)


parser = argparse.ArgumentParser(description="wf-deliverance")
parser.add_argument('--service', '-s', choices=config.VALID_SERVICES,
                    default=config.VALID_SERVICES[0],
                    help="The Amazon delivery service to use")
parser.add_argument('--force-login', '-f', action='store_true',
                    help="Login and refresh session data if it exists")
parser.add_argument('--checkout', '-c', action='store_true',
                    help="Select first available slot and checkout")
parser.add_argument('--ignore-oos', action='store_true',
                    help="Ignores out of stock alerts, but attempts to "
                         "save removed item details to a local TOML file")
parser.add_argument('--save-cart', action='store_true',
                    help="Saves your cart information to a local TOML file")
parser.add_argument('--no-import', action='store_true',
                    help="Don't import chromedriver_binary. Set this flag "
                         "if using an existing chromedriver in $PATH")
parser.add_argument('--debug', action='store_true')


if __name__ == '__main__':
    args = parser.parse_args()

    logging.basicConfig(
        format='[%(asctime)s] {%(funcName)s} %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO if not args.debug else logging.DEBUG
    )

    if not args.no_import:
        # Import appends ./env/lib/.../chromedriver to $PATH
        import chromedriver_binary

    log.info('Invoking Selenium Chrome webdriver')
    driver = webdriver.Chrome()
    try:
        main_loop(driver, args)
    except WebDriverException:
        alert('Encountered an error', 'Basso')
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
