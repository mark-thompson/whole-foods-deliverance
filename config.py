from selenium.webdriver.common.by import By
import toml

CONF_PATH = 'conf.toml'
PKL_PATH = '.session_storage.pkl'
try:
    if toml.load(CONF_PATH)["url"]["use_smile"]:
        BASE_URL = 'https://smile.amazon.com/'
    else:
        BASE_URL = 'https://www.amazon.com/'
except Exception:
    BASE_URL = 'https://www.amazon.com/'

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
    SLOT_CONTAINER = (By.CLASS_NAME, 'ufss-slotselect-container')
    SLOT_CONTAINER_MULTI = (By.ID, 'slot-container-root')
    SLOT_DATE_MULTI = (By.XPATH, "//*[contains(@id ,'slot-container-20')]")
    SLOT = (By.XPATH, "//*[contains(@class, 'ufss-slot ') and "
                      "contains(@class, 'ufss-available')]")
    OOS_ITEM = (By.XPATH, "//*[contains(@class, ' item-row')]")
    OOS_CONTINUE = (By.XPATH, "//*[@name='continue-bottom']")
    CART_ITEMS = (By.XPATH, "//div[@data-name='Active Items']"
                            "/*[contains(@class, 'sc-list-item')]")
    THROTTLE_CONTINUE = (By.XPATH, "//*[contains(@id, 'throttle') and "
                                   "@role='button']")


class SiteConfig:
    def __init__(self, service):
        if service not in VALID_SERVICES:
            raise ValueError(
                "Invalid service '{}'\n Services implemented: \n{}".format(
                    service, VALID_SERVICES
                )
            )
        self.service = service
        self.Locators = Locators()
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
                    (By.XPATH, "//*[contains(@class, 'ufss-overview-continue-button')]"),
                    'gp/buy/payselect/handlers/display.html'
                ),
                (
                    (By.ID, 'continue-top'),
                    'gp/buy/spc/handlers/display.html'
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
