#!/bin/env python3
import argparse
import syslog
from dataclasses import dataclass
from syslog import LOG_INFO, LOG_ERR
from typing import Optional

import phonenumbers
import requests
from phonenumbers.phonenumberutil import PhoneNumberFormat
from pystrix.agi import AGI
from pystrix.agi.core import Hangup

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['register', 'check'])
parser.add_argument('-H', '--host', help='Host to register outgoing or check incoming call')
parser.add_argument('-t', '--timeout', help='Timeout for verification request in milliseconds',
                    type=int, default=1000)
parser.add_argument('-c', '--code', help='City code to add to short numbers', default='3953')


@dataclass
class CallInfo:
    caller: str
    destination: str
    redirection: Optional[str]

    def to_json(self):
        result = {
            'msisdnA': self.caller,
            'msisdnB': self.destination,
        }
        if self.redirection:
            result['redirectingNumber'] = self.redirection
        return result

    def __str__(self):
        if self.redirection is None:
            return f'from {self.caller} to {self.destination}'
        else:
            return f'from {self.caller} to {self.destination} over {self.redirection}'

    @staticmethod
    def _get_number(environment: dict, variable: str, code: str, required: bool = False):
        result = environment.get(variable)
        if result == 'unknown':
            result = None

        if result is None and required:
            raise AGIVariableNotFound(variable)

        if result is not None:
            number = phonenumbers.parse(result, 'RU')
            if not phonenumbers.is_valid_number(number):
                number = phonenumbers.parse(code + result, 'RU')
            if not phonenumbers.is_valid_number(number):
                raise InvalidPhoneNumber(result, variable)
            result = phonenumbers.format_number(number, PhoneNumberFormat.E164)[1:]

        return result

    @classmethod
    def from_agi(cls, agi: AGI, code):
        environment = agi.get_environment()
        caller = cls._get_number(environment, 'agi_callerid', code)
        destination = cls._get_number(environment, 'agi_dnid', code)
        redirection = cls._get_number(environment, 'agi_rdnis', code, required=False)

        return CallInfo(caller, destination, redirection)


class AGIVariableNotFound(RuntimeError):
    def __init__(self, missing_variable: str):
        super().__init__(f'Variable {missing_variable} not found in Asterisk environment')


class InvalidPhoneNumber(RuntimeError):
    def __init__(self, number: str, variable: str):
        super().__init__(f'Invalid {variable} number {number}')


def register_call(host: str, agi: AGI, call_info: CallInfo, timeout_millis: int):
    url = f'http://{host}/aos/saveRequest'
    response = requests.post(url, json=call_info.to_json(), timeout=timeout_millis / 1000)

    if response.status_code == 200:
        syslog.syslog(LOG_INFO, f'Registered call {call_info}')
    else:
        syslog.syslog(LOG_ERR,
                      f'Failed to register call {call_info}: {response.status_code} {response.reason} {response.text}')


def check_call(host: str, agi: AGI, call_info: CallInfo, timeout_millis: int):
    url = f'http://{host}/aos/checkRequest'
    response = requests.post(url, json=call_info.to_json(), timeout=timeout_millis / 1000)
    try:
        response.raise_for_status()
        result = response.json()['result']
        if (isinstance(result, str) and result.upper() == 'FALSE') or result is False:
            syslog.syslog(LOG_INFO, f'Not registered call {call_info}, terminating')
            agi.execute(Hangup())
        else:
            syslog.syslog(LOG_INFO, f'Call from {call_info} is registered, passing')
    except Exception:
        syslog.syslog(LOG_ERR,
                      f'Failed to check call {call_info}: {response.status_code} {response.reason} {response.text}')


if __name__ == '__main__':
    agi = AGI()
    try:
        args = parser.parse_args()
        call_info = CallInfo.from_agi(agi, args.code)

        if args.action == 'register':
            syslog.syslog(LOG_INFO, f'Registering call {call_info} using host {args.host} with timeout {args.timeout}')
            register_call(args.host, agi, call_info, args.timeout)
        elif args.action == 'check':
            syslog.syslog(LOG_INFO, f'Checking call {call_info} using host {args.host} with timeout {args.timeout}')
            check_call(args.host, agi, call_info, args.timeout)
        else:
            syslog.syslog(LOG_ERR, f'Unknown action {args.action}')

    except Exception as e:
        syslog.syslog(LOG_ERR, f'Something went wrong: {e}')
