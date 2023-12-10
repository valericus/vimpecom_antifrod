#!/bin/env python3
import argparse
import logging

import requests
from pystrix.agi import AGI
from pystrix.agi.core import Verbose, Hangup
from requests.exceptions import JSONDecodeError

from utils import CallInfo, get_call_info

log = logging.getLogger(__name__)

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['register', 'check'], required=True)
parser.add_argument('-H', '--host', help='Host to register outgoing or check incoming call')


def register_call(host: str, agi: AGI, call_info: CallInfo):
    url = f'https://{host}/aos/saveRequest'
    response = requests.post(url, json=call_info.to_json())

    if response == 200:
        agi.execute(Verbose(f'Registered call {call_info}'))
    else:
        agi.execute(Verbose(f'Failed to register call {call_info}: {response.text}'))


def check_call(host: str, agi: AGI, call_info: CallInfo):
    url = f'https://{host}/aos/checkRequest'
    response = requests.post(url, json=call_info.to_json())
    try:
        response.raise_for_status()
        result = response.json()['result']
        if result is not True:
            agi.execute(Verbose(f'Not registered call {call_info}, terminating'))
            agi.execute(Hangup())
    except Exception:
        agi.execute(
            Verbose(f'Failed to check call {call_info}: {response.status_code} {response.reason} {response.text}')
        )


if __name__ == '__main__':
    args = parser.parse_args()
    agi = AGI()
    try:
        call_info = get_call_info(agi)

        if args.action == 'register':
            register_call(args.host, agi, call_info)
        elif args.action == 'check':
            check_call(args.host, agi, call_info)
        else:
            raise RuntimeError(f'Unknown action {args.action}')

    except Exception as e:
        agi.execute(Verbose(f'Something went wrong: {e}'))
