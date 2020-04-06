from selenium.webdriver.common.by import By


class Config:
    CONF_PATH = 'conf.toml'
    PKL_PATH = '.session_cookie.pkl'
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
        GRID = (By.ID, 'ufss-widget-grid')
        SLOTS = (By.CLASS_NAME, 'ufss-slotselect-container')
