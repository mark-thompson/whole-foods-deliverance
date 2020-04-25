import logging
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config import Patterns
from deliverance.exceptions import (NavigationException, RouteRedirect,
                                    UnhandledRedirect)
from deliverance.utils import (wait_for_element, click_when_enabled, jitter,
                               remove_qs, wait_for_auth, handle_oos,
                               handle_throttle)

log = logging.getLogger(__name__)


def handle_redirect(driver, ignore_oos, valid_dest=None, timeout=None,
                    route=None):
    current = remove_qs(driver.current_url)
    log.warning("Redirected to: '{}'".format(current))

    if Patterns.AUTH_URL in current:
        wait_for_auth(driver)
    elif Patterns.OOS_URL in current:
        handle_oos(driver, ignore_oos)
    elif Patterns.THROTTLE_URL in current:
        handle_throttle(driver)
        raise RouteRedirect('Redirected after throttle')
    elif route and current == route.route_start:
        if not route.waypoints_reached:
            driver.refresh()
        raise RouteRedirect()
    elif valid_dest and timeout:
        log.warning(
            'Handling unknown redirect (timeout in {}s)'.format(timeout)
        )
        try:
            WebDriverWait(driver, timeout).until(
                EC.url_matches('|'.join(valid_dest))
            )
        except TimeoutException:
            raise UnhandledRedirect(
                "Timed out waiting for redirect to a valid dest\n"
                "Current URL: '{}'".format(driver.current_url)
            )
    else:
        raise UnhandledRedirect()


class Waypoint:
    def __init__(self, locator, dest, callable=None):
        self.locator = locator
        if not isinstance(dest, list):
            dest = [dest]
        self.dest = dest
        self.callable = callable

    def __str__(self):
        return "<Waypoint {} -> '{}'>".format(self.locator, self.dest)

    def check_current(self, current_url):
        for d in self.dest:
            if d in remove_qs(current_url):
                return d


class Route:
    def __init__(self, route_start, parser_args, *args):
        self.route_start = route_start
        self.args = parser_args
        self.waypoints = args
        self.waypoints_reached = 0

    def __len__(self):
        return len(self.waypoints)

    def __str__(self):
        return "<Route beginning at '{}' with {} stops>".format(
            self.route_start, len(self))

    def navigate_waypoint(self, driver, waypoint, timeout, valid_dest):
        if callable(waypoint.callable):
            log.info('Executing {}() before navigation'.format(
                waypoint.callable.__name__
            ))
            waypoint.callable(driver=driver)
        log.info('Navigating ' + str(waypoint))
        elem = wait_for_element(driver, waypoint.locator, timeout=timeout)
        jitter(.4)
        click_when_enabled(driver, elem)
        try:
            WebDriverWait(driver, timeout).until(
                EC.staleness_of(elem)
            )
        except TimeoutException:
            pass
        current = remove_qs(driver.current_url)
        if waypoint.check_current(current):
            log.info(
                "Navigated to '{}'".format(waypoint.check_current(current))
            )
        elif valid_dest and any(d in current for d in valid_dest):
            log.info("Navigated to valid dest '{}'".format(current))
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
                valid_dest = []
                for w in self.waypoints[self.waypoints.index(waypoint):]:
                    valid_dest.extend(w.dest)
                if waypoint.check_current(driver.current_url):
                    log.warning("Already at dest: '{}'".format(
                        waypoint.check_current(driver.current_url)
                    ))
                else:
                    self.navigate_waypoint(driver, waypoint, timeout,
                                           valid_dest)
            except NavigationException:
                handle_redirect(driver,
                                ignore_oos=self.args.ignore_oos,
                                valid_dest=valid_dest,
                                timeout=timeout,
                                route=self)
            self.waypoints_reached += 1
        log.info('Route complete')
