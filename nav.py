from selenium.common.exceptions import WebDriverException


class NavigationException(WebDriverException):
    """Thrown when a navigation action does not reach target destination"""
    pass
