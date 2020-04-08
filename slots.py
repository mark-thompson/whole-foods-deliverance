import logging

from utils import click_when_enabled

log = logging.getLogger(__name__)


def get_element_text(element):
    return element.get_attribute('innerText')


class WebElement:
    def __init__(self, element):
        self._element = element

    def __str__(self):
        return self.STR_SEP.join(
            [get_element_text(self.find_child(x)) for x in self.STR_XPATH]
        )

    @property
    def id(self):
        return self._element.get_attribute('id')

    @property
    def name(self):
        return get_element_text(self.find_child(self.STR_XPATH[0]))

    def find_child(self, class_pattern):
        child = self._element.find_elements_by_xpath(
            ".//*[contains(@class, '{}')]".format(class_pattern)
        )
        if len(child) > 1:
            log.warning("Multiple children found with pattern: '{}'".format(
                class_pattern
            ))
        return child[0]

    def select(self, driver, **kwargs):
        click_when_enabled(driver, self._element, **kwargs)


class DateElement(WebElement):
    STR_XPATH = ['day-of-week', 'month-day']
    STR_SEP = ', '


class SlotElement(WebElement):
    STR_XPATH = ['slot-time-window-text', 'slot-price-text']
    STR_SEP = ' - '

    def __init__(self, slot_element, date_element):
        self._element = slot_element
        if not isinstance(date_element, DateElement):
            date_element = DateElement(date_element)
        self._date_element = date_element

    @property
    def full_name(self):
        return '::'.join([self._date_element.name, self.name])

    def select(self, driver, **kwargs):
        self._date_element.select(driver, **kwargs)
        click_when_enabled(
            driver,
            self.find_child('ufss-slot-toggle-native-button'),
            **kwargs
        )
