import logging
import re

from .exceptions import SlotDateElementAmbiguous
from .utils import click_when_enabled, get_element_text

log = logging.getLogger(__name__)


class WebElement:
    def __init__(self, element):
        self._element = element
        self.driver = element.parent

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

    def find_ancestor(self, xpath):
        elems = self._element.find_elements_by_xpath(
            "./ancestor::{}".format(xpath)
        )
        if len(elems) > 1:
            log.warning("Multiple ancestors found with xpath: '{}'".format(
                xpath
            ))
        return elems[0]

    def find_child(self, xpath_or_pattern):
        if not re.search(r'/|\[', xpath_or_pattern):
            xpath = ".//*[contains(@class, '{}')]".format(xpath_or_pattern)
        else:
            xpath = xpath_or_pattern
        child = self._element.find_elements_by_xpath(xpath)
        if len(child) > 1:
            log.debug("Multiple children found with xpath: '{}'".format(xpath))
        return child[0]

    def select(self, **kwargs):
        click_when_enabled(self.driver, self._element, **kwargs)


class DateElement(WebElement):
    STR_XPATH = ['day-of-week', 'month-day']
    STR_SEP = ', '


class SlotElement(WebElement):
    STR_XPATH = ['slot-time-window-text', 'slot-price-text']
    STR_SEP = ' - '
    DATE_CLS = DateElement

    def __init__(self, slot_element, date_element=None):
        self._element = slot_element
        self.driver = slot_element.parent
        if date_element is None:
            log.debug('Attempting to find date element for slot: {}'.format(
                slot_element
            ))
            date_element = self.find_date_element()
        if not isinstance(date_element, self.DATE_CLS):
            date_element = self.DATE_CLS(date_element)
        self._date_element = date_element

    @property
    def full_name(self):
        return '::'.join([self._date_element.name, self.name])

    def find_date_element(self):
        id = (self.find_ancestor("div[contains(@class, 'ufss-slotselect ')]")
              .get_attribute('id'))
        elems = self.driver.find_elements_by_xpath(
            "//button[@name='{}']".format(id)
        )
        if len(elems) != 1:
            raise SlotDateElementAmbiguous(
                'Expected 1 date element but found {}'.format(len(elems))
            )
        else:
            return elems[0]

    def select(self, **kwargs):
        self._date_element.select(**kwargs)
        click_when_enabled(
            self.driver,
            self.find_child('ufss-slot-toggle-native-button'),
            **kwargs
        )


class DateElementMulti(DateElement):
    STR_XPATH = ['a-size-base-plus date-button-text', 'calendar-date-text']


class SlotElementMulti(SlotElement):
    STR_XPATH = ['slotRadioLabel']
    DATE_CLS = DateElementMulti

    def __str__(self):
        return self.STR_SEP.join(
            [self.delivery_type,
             get_element_text(self.find_child(self.STR_XPATH[0]))]
        )

    @property
    def delivery_type(self):
        return re.search(r'(UN)?ATTENDED', self.id).group()

    @property
    def name(self):
        return str(self)

    def find_date_element(self):
        id = re.search(r'\d{4}-\d{2}-\d{2}', self.id).group()
        elems = self.driver.find_elements_by_xpath(
            "//button[contains(@id, 'date-button-{}')]".format(id)
        )
        if len(elems) != 1:
            raise SlotDateElementAmbiguous(
                'Expected 1 date element but found {}'.format(len(elems))
            )
        else:
            return elems[0]

    def select(self, **kwargs):
        click_when_enabled(
            self.driver,
            self.driver.find_element_by_xpath(
                "//button[contains(@id, 'selector-button-{}')]".format(
                    self.delivery_type.lower()
                )
            ),
            **kwargs
        )
        self._date_element.select(**kwargs)
        click_when_enabled(self.driver, self._element, **kwargs)


class CartItem(WebElement):
    STR_XPATH = ['sc-product-title', 'qs-widget-container']
    STR_SEP = ' - Qty: '

    @property
    def product_id(self):
        return self._element.get_attribute('data-asin')

    @property
    def data(self):
        return {
            'name': self.name,
            'quantity': get_element_text(self.find_child(self.STR_XPATH[1])),
            'price': get_element_text(self.find_child('sc-price ')),
            'product_id': self.product_id,
            'link': self.find_child('sc-product-link').get_attribute('href')
        }


class PaymentRow(WebElement):
    @property
    def card_number(self):
        return get_element_text(self.find_child('card-info')).split(' ')[-1]

    def select(self, **kwargs):
        click_when_enabled(
            self.driver,
            self.find_child(".//input[@type='radio']"),
            **kwargs
        )
