from dataclasses import dataclass

from pystrix.agi import AGI


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


def _get_var(environment: dict, variable: str, required: bool = False):
    result = environment.get(variable)
    if result == 'unknown':
        result = None

    if result is None and required:
        raise AGIVariableNotFound(variable)

    return result


def get_call_info(agi: AGI):
    environment = agi.get_environment()
    caller = _get_var(environment, 'agi_callerid')
    destination = _get_var(environment, 'agi_dnid')
    redirection = _get_var(environment, 'agi_rdnis', required=False)

    return CallInfo(caller, destination, redirection)


class AGIVariableNotFound(RuntimeError):
    def __init__(self, missing_variable: str):
        super().__init__(f'Variable {missing_variable} not found in Asterisk environment')
