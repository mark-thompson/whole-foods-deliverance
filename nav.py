import logging
from selenium.common.exceptions import WebDriverException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import BASE_URL, Patterns
from utils import wait_for_element, jitter, remove_qs, wait_for_auth

log = logging.getLogger(__name__)


class NavigationException(WebDriverException):
    """Thrown when a navigation action does not reach target destination"""
    pass


class RouteRedirectException(WebDriverException):
    """Thrown when a route is redirected to its starting point"""
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
        self.waypoints_reached = 0

    def __len__(self):
        return len(self.waypoints)

    def __str__(self):
        return "<Route beginning at '{}' with {} stops>".format(
            self.route_start, len(self))

    def navigate_waypoint(self, driver, waypoint, timeout):
        log.info('Navigating ' + str(waypoint))
        elem = wait_for_element(driver, waypoint.locator, timeout=timeout)
        jitter(.4)
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

    def navigate(self, driver, timeout=20):
        log.info('Navigating ' + str(self))
        self.waypoints_reached = 0
        if remove_qs(driver.current_url) != self.route_start:
            log.info('Navigating to route start: {}'.format(self.route_start))
            driver.get(self.route_start)
        for waypoint in self.waypoints:
            try:
                valid_dest = [
                    waypnt.dest for waypnt in
                    self.waypoints[self.waypoints.index(waypoint)+1:]
                ]
                if remove_qs(driver.current_url) == BASE_URL + waypoint.dest:
                    log.warning("Already at dest: '{}'".format(waypoint.dest))
                else:
                    self.navigate_waypoint(driver, waypoint, timeout)
            except NavigationException as e:
                current = remove_qs(driver.current_url)
                if Patterns.AUTH in current:
                    log.warning('Handling login redirect')
                    wait_for_auth(driver)
                elif any(d in current for d in valid_dest):
                    log.warning("Navigated to valid dest '{}'".format(current))
                elif current == self.route_start and self.waypoints_reached:
                    raise RouteRedirectException()
                else:
                    log.warning(
                        "Current URL '{}' does not match target\n"
                        "Handling possible redirect (timeout in {}s)".format(
                            current, timeout
                        )
                    )
                    try:
                        WebDriverWait(driver, timeout).until(
                            EC.url_matches('|'.join(valid_dest))
                        )
                    except TimeoutException:
                        log.error(
                            "Timed out waiting for redirect to a valid dest\n"
                            "Current URL: '{}'".format(driver.current_url)
                        )
                        raise e
            self.waypoints_reached += 1
        log.info('Route complete')
