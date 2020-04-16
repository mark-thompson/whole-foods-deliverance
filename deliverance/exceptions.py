from selenium.common.exceptions import WebDriverException


class NavigationException(WebDriverException):
    """
    Raise when a navigation action reaches neither target nor valid destination
    """


class RouteRedirect(WebDriverException):
    """Raise when a route is redirected to its starting point"""


class ItemOutOfStock(WebDriverException):
    """Raise when an OOS alert is encountered"""


class UnhandledRedirect(WebDriverException):
    """Raise when all redirect handlers have failed"""


class SlotDateElementAmbiguous(WebDriverException):
    """
    Raise when a slot element does not have exactly one ancestor matching
    its specified date element XPATH
    """
