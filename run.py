import argparse
import logging
from time import sleep
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException

import config
from deliverance.notify import alert
from deliverance.utils import dump_source
from deliverance import Browser

log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="wf-deliverance")
parser.add_argument('--service', '-s', choices=config.VALID_SERVICES,
                    default=config.VALID_SERVICES[0],
                    help="The Amazon delivery service to use")
parser.add_argument('--checkout', '-c', action='store_true',
                    help="Select first available slot and checkout")
parser.add_argument('--ignore-oos', action='store_true',
                    help="Ignores out of stock alerts, but attempts to "
                         "save removed item details to a local TOML file")
parser.add_argument('--save-cart', action='store_true',
                    help="Saves your cart information to a local TOML file")
parser.add_argument('--no-import', action='store_true',
                    help="Don't import chromedriver_binary. Set this flag "
                         "if using an existing chromedriver in $PATH")
parser.add_argument('--debug', action='store_true')


if __name__ == '__main__':
    args = parser.parse_args()

    logging.basicConfig(
        format='[%(asctime)s] {%(funcName)s} %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=logging.INFO if not args.debug else logging.DEBUG
    )

    if not args.no_import:
        # Import appends ./env/lib/.../chromedriver to $PATH
        import chromedriver_binary

    log.info('Invoking Selenium Chrome webdriver')
    opts = Options()
    opts.add_argument("user-data-dir=" + config.USER_DATA_DIR)
    driver = webdriver.Chrome(options=opts)
    try:
        Browser(driver, args).main_loop()
    except WebDriverException:
        alert('Encountered an error', 'Basso')
        if args.debug:
            dump_source(driver)
        raise
    try:
        # allow time to check out manually
        min = 15
        log.info('Sleeping for {} minutes (press Ctrl+C to close)'.format(min))
        sleep(min*60)
    except KeyboardInterrupt:
        log.warning('Slumber disturbed')
    log.info('Closing webdriver')
    driver.close()
