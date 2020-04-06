from selenium.webdriver.common.by import By


CONF_PATH = 'conf.toml'
PKL_PATH = '.session_storage.pkl'
BASE_URL = 'https://www.amazon.com/'
SLOT_URL = BASE_URL + 'gp/buy/shipoptionselect/handlers/display.html'
AUTH_URL = BASE_URL + 'ap/signin'


class Patterns:
    NOT_LOGGED_IN = "Hello, Sign in"
    UNAVAILABLE = "We're sorry we are unable to fulfill your entire order."
    NO_SLOTS = "No delivery windows available."
    WF_CHECKOUT = "Checkout Whole Foods"


class Locators:
    LOGIN = (By.ID, 'nav-link-accountList')
    GRID = (By.CLASS_NAME, 'ufss-widget-grid')
    SLOTS = (By.CLASS_NAME, 'ufss-slotselect-container')


class Routes:
    class WholeFoods:
        TO_SLOT_SELECT = [
            BASE_URL,
            ((By.ID, 'nav-cart'),
                'gp/cart/view.html'),
            ((By.XPATH, "//*[contains(text(),'Checkout Whole Foods')]/.."),
                'alm/byg'),
            ((By.XPATH, "//span[contains(@class, 'byg-continue-button')]"),
                'alm/substitution'),
            ((By.ID, 'subsContinueButton'),
                'gp/buy/shipoptionselect/handlers/display.html')
        ]
