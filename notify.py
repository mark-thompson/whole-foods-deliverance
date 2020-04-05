import logging
import requests
import toml
import os
from random import random
from twilio.rest import Client as TwilioClient

from config import Config

log = logging.getLogger(__name__)


def conf_dependent(conf_key):
    def decorator(func):
        def wrapper(*args, **kwargs):
            if 'conf' not in kwargs:
                try:
                    kwargs['conf'] = toml.load(Config.CONF_PATH)[conf_key]
                except Exception:
                    log.error("{}() requires a config file at"
                              " '{}' with key '{}'".format(func.__name__,
                                                           Config.CONF_PATH,
                                                           conf_key))
                    return
            try:
                return(func(*args, **kwargs))
            except Exception:
                log.error('Action failed:', exc_info=True)
                return
        return wrapper
    return decorator


@conf_dependent('telegram')
def send_telegram(body, conf):
    log.info('Sending Telegram message (chat_id: {}, len: {})'.format(
        conf['chat_id'], len(body)
    ))
    response = requests.get(
        'https://api.telegram.org/bot{}/sendMessage?'
        'chat_id={}&parse_mode=Markdown&text={}'.format(
            conf['token'],
            conf['chat_id'],
            body
        )
    )
    return(response.json())


@conf_dependent('twilio')
def send_sms(body, conf):
    client = TwilioClient(conf['sid'], conf['token'])
    log.info('Sending SMS (num: {}, len: {})'.format(
        conf['to_num'], len(body)
    ))
    result = client.messages.create(
        body=body,
        from_=conf['from_num'],
        to=conf['to_num']
    )
    return(result)


def alert(message, sound='Blow'):
    log.info("Alerting user with message: '{}'".format(message))
    try:
        os.popen(
            'afplay /System/Library/Sounds/{}.aiff && '
            'say "{}" --rate 150 --voice Fiona'.format(sound, message)
        )
    except Exception:
        pass


def annoy():
    """Sorry about it"""
    try:
        for _ in range(15):
            os.popen(
                'sleep {} && afplay /System/Library/Sounds/Sosumi.aiff'.format(
                    random()
                ))
    except Exception:
        pass
