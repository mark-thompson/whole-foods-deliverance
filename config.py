from selenium.webdriver.common.by import By
import toml

CONF_PATH = 'conf.toml'
USER_DATA_DIR = 'chrome-user-data'
BASE_URL = 'https://www.amazon.com/'
try:
    options = toml.load(CONF_PATH)['options']
    if options.get('use_smile'):
        BASE_URL = 'https://smile.amazon.com/'
    if options.get('chrome_data_dir'):
        USER_DATA_DIR = options['chrome_data_dir']
except Exception:
    pass

NAV_TIMEOUT = 20
INTERVAL = 25

VALID_SERVICES = [
    'Whole Foods',
    'Amazon Fresh'
]


class Patterns:
    AUTH_URL = BASE_URL + 'ap/'
    NOT_LOGGED_IN = "Hello, Sign in"
    OOS_URL = 'gp/buy/itemselect/handlers/display.html'
    OOS = "This item is no longer available"
    THROTTLE_URL = 'throttle.html'
    NO_SLOTS_MULTI = "No.*delivery windows are available"


class Locators:
    LOGIN = (By.ID, 'nav-link-accountList')
    OOS_ITEM = (By.XPATH, "//*[contains(@class, ' item-row')]")
    OOS_CONTINUE = (By.XPATH, "//*[@name='continue-bottom']")
    CART_ITEMS = (By.XPATH, "//div[@data-name='Active Items']"
                            "/*[contains(@class, 'sc-list-item')]")
    THROTTLE_CONTINUE = (By.XPATH, "//*[contains(@id, 'throttle') and "
                                   "@role='button']")
    PAYMENT_ROW = (By.XPATH, "//*[starts-with(@class, 'payment-row')]")


class SlotLocators:
    def __init__(self, slot_type='single'):
        if slot_type == 'single':
            self.CONTAINER = (By.CLASS_NAME, 'ufss-slotselect-container')
            self.SLOT = (
                By.XPATH,
                "//*[contains(@class, 'ufss-slot ') and "
                "contains(@class, 'ufss-available')]"
            )
            self.CONTINUE = (
                By.XPATH,
                "//*[contains(@class, 'ufss-overview-continue-button')]"
            )
        elif slot_type == 'multi':
            self.CONTAINER = (By.ID, 'slot-container-root')
            self.SLOT = (
                By.XPATH,
                "//*[starts-with(@id, 'slot-button-root-20') and "
                "not(contains(@class, 'disabled'))]"
            )
            self.CONTINUE = (
                By.XPATH,
                "//input[@class='a-button-text a-declarative' and "
                "@type='submit']"
            )
        else:
            raise ValueError("Unrecognized slot type '{}'".format(slot_type))


class SiteConfig:
    def __init__(self, service):
        if service not in VALID_SERVICES:
            raise ValueError(
                "Invalid service '{}'\n Services implemented: \n{}".format(
                    service, VALID_SERVICES
                )
            )
        self.service = service
        self.BASE_URL = BASE_URL
        self.Locators = Locators()
        self.Patterns = Patterns()
        self.routes = {}
        self.routes['SLOT_SELECT'] = {
            'route_start': BASE_URL,
            'waypoints': [
                (
                    (By.ID, 'nav-cart'),
                    'gp/cart/view.html'
                ),
                (
                    (By.XPATH, "//*[contains(text(),'Checkout {}')]/..".format(
                        service
                    )),
                    'alm/byg'
                ),
                (
                    (By.XPATH, "//span[contains(@class, 'byg-continue-button')]"),
                    'alm/substitution'
                ),
                (
                    (By.ID, 'subsContinueButton'),
                    'gp/buy/shipoptionselect/handlers/display.html'
                )
            ]
        }
        self.routes['CHECKOUT'] = {
            'route_start': BASE_URL + 'gp/buy/shipoptionselect/handlers/display.html',
            'waypoints': [
                (
                    [SlotLocators().CONTINUE, SlotLocators('multi').CONTINUE],
                    'gp/buy/payselect/handlers/display.html'
                ),
                (
                    (By.ID, 'continue-top'),
                    'gp/buy/spc/handlers/display.html',
                    'select_payment_method'  # function to be called before nav
                ),
                (
                    (By.XPATH, "//input[contains(@class, 'place-your-order-button')]"),
                    'gp/buy/thankyou/handlers/display.html'
                )
            ]
        }

    @property
    def cart_endpoint(self):
        if self.service == 'Amazon Fresh':
            return 'cart/fresh'
        else:
            return 'cart/localmarket'
