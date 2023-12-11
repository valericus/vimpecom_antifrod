#!/bin/env python3
import argparse
from dataclasses import dataclass

import requests
from pystrix.agi import AGI
from pystrix.agi.core import Verbose, Hangup

parser = argparse.ArgumentParser()
parser.add_argument('action', choices=['register', 'check'])
parser.add_argument('-H', '--host', help='Host to register outgoing or check incoming call')


@dataclass
class CallInfo:
    caller: str
    destination: str
    redirection: str

    def to_json(self):
        return {
            'msisdnA': self.caller,
            'msisdnB': self.destination,
            'redirectingNumber': self.redirection
        }

    def __str__(self):
        if self.redirection is None:
            return f'from {self.caller} to {self.destination}'
        else:
            return f'from {self.caller} to {self.destination} over {self.redirection}'

    @staticmethod
    def _get_var(environment: dict, variable: str, required: bool = False):
        result = environment.get(variable)
        if result == 'unknown':
            result = None

        if result is None and required:
            raise AGIVariableNotFound(variable)

        return result

    @classmethod
    def from_agi(cls, agi: AGI):
        environment = agi.get_environment()
        caller = cls._get_var(environment, 'agi_callerid')
        destination = cls._get_var(environment, 'agi_dnid')
        redirection = cls._get_var(environment, 'agi_rdnis', required=False)

        return CallInfo(caller, destination, redirection)


class AGIVariableNotFound(RuntimeError):
    def __init__(self, missing_variable: str):
        super().__init__(f'Variable {missing_variable} not found in Asterisk environment')


def register_call(host: str, agi: AGI, call_info: CallInfo):
    url = f'http://{host}/aos/saveRequest'
    response = requests.post(url, json=call_info.to_json())

    if response.status_code == 200:
        agi.execute(Verbose(f'Registered call {call_info}'))
    else:
        agi.execute(
            Verbose(f'Failed to register call {call_info}: {response.status_code} {response.reason} {response.text}')
        )


def check_call(host: str, agi: AGI, call_info: CallInfo):
    url = f'http://{host}/aos/checkRequest'
    response = requests.post(url, json=call_info.to_json())
    try:
        response.raise_for_status()
        result = response.json()['result']
        if result is False:
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
        call_info = CallInfo.from_agi(agi)

        if args.action == 'register':
            register_call(args.host, agi, call_info)
        elif args.action == 'check':
            check_call(args.host, agi, call_info)
        else:
            raise RuntimeError(f'Unknown action {args.action}')

    except Exception as e:
        agi.execute(Verbose(f'Something went wrong: {e}'))
