import logging
import pickle
import re
from time import sleep
from random import uniform

import config

log = logging.getLogger(__name__)


def remove_qs(url):
    """Remove URL query string the lazy way"""
    return url.split('?')[0]


def jitter(seconds, pct=20):
    """This seems unnecessary"""
    sleep(uniform(seconds*(1-pct/100), seconds*(1+pct/100)))


def store_session_data(driver, path=config.PKL_PATH):
    data = {
        'cookies': driver.get_cookies(),
        'storage': {
            k: driver.execute_script(
                'for(var k,s=window.{}Storage,d={{}},i=0;i<s.length;++i)'
                'd[k=s.key(i)]=s.getItem(k);return d'.format(k)
            ) for k in ['local', 'session']
        }
    }
    if any(data.values()):
        log.info('Writing session data to: ' + path)
        with open(path, 'wb') as file:
            pickle.dump(data, file)
    else:
        log.warning('No session data found')


def load_session_data(driver, path=config.PKL_PATH):
    log.info('Reading session data from: ' + path)
    with open(path, 'rb') as file:
        data = pickle.load(file)
    if data.get('cookies'):
        log.info('Loading {} cookie values'.format(len(data['cookies'])))
        for c in data['cookies']:
            if c.get('expiry'):
                c['expiry'] = int(c['expiry'])
            driver.add_cookie(c)
    for _type, values in data['storage'].items():
        if values:
            log.info('Loading {} {}Storage values'.format(len(values), _type))
        for k, v in values.items():
            driver.execute_script(
                'window.{}Storage.setItem(arguments[0], arguments[1]);'.format(
                    _type
                ),
                k, v
            )


def generate_message(slots):
    text = []
    for d in slots.values():
        if not d['slot_btns']:
            continue
        text.append('\n' + d['date_btn'].text.replace('\n', ' - '))
        for s in d['slot_btns']:
            text.append(
                re.sub(r'\n|\s\s+', ' - ',
                       s.get_attribute('innerText').strip())
            )
    if text:
        return '\n'.join(["Whole Foods delivery slots found!", *text])
