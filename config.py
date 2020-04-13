from selenium.webdriver.common.by import By
import toml

CONF_PATH = 'conf.toml'
PKL_PATH = '.session_storage.pkl'
try:
    BASE_URL = toml.load(CONF_PATH)["base_url"]["url"]
except Exception:
    BASE_URL = 'https://www.amazon.com/'


VALID_SERVICES = [
    'Whole Foods',
    'Amazon Fresh'
]


class Patterns:
    AUTH = BASE_URL + 'ap/'
    NOT_LOGGED_IN = "Hello, Sign in"


class Locators:
    LOGIN = (By.ID, 'nav-link-accountList')
    SLOT_CONTAINER = (By.CLASS_NAME, 'ufss-slotselect-container')
    SLOT_SELECT = (By.XPATH, ".//div[contains(@class, 'ufss-slotselect ')]")
    SLOT = (By.XPATH, ".//*[contains(@class, 'ufss-slot ') and "
                      "contains(@class, 'ufss-available')]")


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
