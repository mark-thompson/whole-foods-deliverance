from selenium.webdriver.common.by import By
import toml

CONF_PATH = 'conf.toml'
PKL_PATH = '.session_storage.pkl'
try:
    BASE_URL = toml.load(CONF_PATH)["base_url"]["url"]
except Exception:
    BASE_URL = 'https://www.amazon.com/'
AUTH_URL = BASE_URL + 'ap/signin'

NOT_LOGGED_IN_PATTERN = "Hello, Sign in"
LOGIN_LOCATOR = (By.ID, 'nav-link-accountList')


from nav import Route, Waypoint  # noqa


class WholeFoods:

    class Locators:
        SLOT_CONTAINER = (By.CLASS_NAME, 'ufss-slotselect-container')
        SLOT_SELECT = (By.XPATH, ".//div[contains(@class, 'ufss-slotselect ')]")
        SLOT = (
            By.XPATH,
            ".//*[contains(@class, 'ufss-slot ') and contains(@class, 'ufss-available')]"
        )

    class Routes:
        SLOT_SELECT = Route(
            BASE_URL,
            Waypoint(
                (By.ID, 'nav-cart'),
                'gp/cart/view.html'
            ),
            Waypoint(
                (By.XPATH, "//*[contains(text(),'Checkout Whole Foods')]/.."),
                'alm/byg'
            ),
            Waypoint(
                (By.XPATH, "//span[contains(@class, 'byg-continue-button')]"),
                'alm/substitution'
            ),
            Waypoint(
                (By.ID, 'subsContinueButton'),
                'gp/buy/shipoptionselect/handlers/display.html'
            )
        )

        CHECKOUT = Route(
            BASE_URL + 'gp/buy/shipoptionselect/handlers/display.html',
            Waypoint(
                (By.XPATH, "//*[contains(@class, 'ufss-overview-continue-button')]"),
                'gp/buy/payselect/handlers/display.html'
            ),
            Waypoint(
                (By.ID, 'continue-top'),
                'gp/buy/spc/handlers/display.html'
            ),
            Waypoint(
                (By.XPATH, "//input[contains(@class, 'place-your-order-button')]"),
                'gp/buy/thankyou/handlers/display.html'
            )
        )
