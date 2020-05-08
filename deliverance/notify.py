import logging
import requests
import os
from random import random
from twilio.rest import Client as TwilioClient
import platform

from .utils import conf_dependent

log = logging.getLogger(__name__)


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
    ).json()

    if not response.get('ok'):
        raise requests.exceptions.HTTPError(response)
    else:
        return response


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
    return result


def alert(message, sound='Blow'):
    log.info("Alerting user with message: '{}'".format(message))
    try:
        if platform.system() == "Windows":
            os.popen(
                "PowerShell -Command \"Add-Type –AssemblyName System.Speech; "
                "(New-Object System.Speech.Synthesis.SpeechSynthesizer)."
                "Speak('{}');".format(message)
            )
        elif platform.system() == "Linux":
            # requires speech-dispatcher
            os.popen(
                'spd-say "{}"'.format(message)
            )
        else:
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
                )
            )
    except Exception:
        pass
