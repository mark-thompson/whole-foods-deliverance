import logging
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import BASE_URL, AUTH_URL
from utils import get_element, jitter, remove_qs, wait_for_auth

log = logging.getLogger(__name__)


class NavigationException(WebDriverException):
    """Thrown when a navigation action does not reach target destination"""
    pass


class Waypoint:
    def __init__(self, locator, dest, optional=False):
        self.locator = locator
        self.dest = dest
        self.optional = optional

    def __str__(self):
        return "<Waypoint {} -> '{}'>".format(self.locator, self.dest)


class Route:
    def __init__(self, route_start, *args):
        self.route_start = route_start
        self.waypoints = args

    def __len__(self):
        return len(self.waypoints)

    def __str__(self):
        return "<Route beginning at '{}' with {} stops>".format(
            self.route_start, len(self))

    def navigate_waypoint(self, driver, waypoint, timeout):
        log.info('Navigating ' + str(waypoint))
        elem = get_element(driver, waypoint.locator, timeout=timeout)
        jitter(.8)
        elem.click()
        try:
            WebDriverWait(driver, timeout).until(
                EC.staleness_of(elem)
            )
        except TimeoutException:
            pass
        if remove_qs(driver.current_url) == BASE_URL + waypoint.dest:
            log.info("Navigated to '{}'".format(waypoint.dest))
        else:
            raise NavigationException(
                "Navigation to '{}' failed".format(waypoint.dest)
            )

    def navigate(self, driver, timeout=10):
        log.info('Navigating ' + str(self))
        if remove_qs(driver.current_url) != self.route_start:
            log.info('Navigating to route start: {}'.format(self.route_start))
            driver.get(self.route_start)
        for waypoint in self.waypoints:
            try:
                self.navigate_waypoint(driver, waypoint, timeout)
                valid_dest = [
                    waypnt.dest for waypnt in
                    self.waypoints[self.waypoints.index(waypoint)+1:]
                ]
            except NavigationException as e:
                if remove_qs(driver.current_url) == AUTH_URL:
                    log.error('Handling login redirect')
                    wait_for_auth(driver)
                elif remove_qs(driver.current_url) in valid_dest:
                    log.warning("Navigated to valid dest '{}'".format(
                        remove_qs(driver.current_url)
                    ))
                else:
                    log.warning(
                        "Current URL '{}' does not match target\n"
                        "Handling possible redirect (timeout in {}s)".format(
                            remove_qs(driver.current_url), timeout
                        )
                    )
                    try:
                        WebDriverWait(driver, timeout).until(
                            EC.url_contains(waypoint.dest)
                        )
                        log.info("Made it to '{}'".format(waypoint.dest))
                    except TimeoutException:
                        raise e
        log.info('Route complete')
