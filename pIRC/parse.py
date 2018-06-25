
import re
from typing import Optional, Any, Union, Callable
from typing.re import Pattern

def _prep_regex() -> Tuple:
    nick = r'[a-zA-Z][a-zA-Z0-9\[\]\\\'\`\^\{\}-]*'
    user = r'[^\r\n\0 ]+'
    host = r'[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]'

    prefix_parse = r'^(?:(?P<nick>{nick})(?:!(?P<user>{user}))?@)?(?P<host>{host})$'.format(
        host=host, nick=nick, user=user
    )
    prefix = r'(?P<prefix>(?:{nick}(?:!{user})?@)?{host})'.format(
        host=host, nick=nick, user=user
    )
    verb = r'(?P<verb>[a-zA-Z]+|[0-9]{3})'
    params = r'(?P<params>[^:\r\n\0]*(?::[^:\r\n\0]*)*)'

    message = r'^(?::{prefix} +)?{verb} +{params}$'.format(
        prefix=prefix, verb=verb, params=params
    )
    return (re.compile(message, re.IGNORECASE), re.compile(prefix_parse, re.IGNORECASE))

_message_regex, _prefix_regex = _prep_regex()
del _prep_regex


def _match_check(source: Union[Pattern, tuple, str], target: str) -> bool:
    if isinstance(source, tuple): # match for any
        for val in source:
            if _match_check(val, target):
                break
        else:
            return False

    elif isinstance(source, Pattern):  # compare by regex
        if source.match(target) is None:
            return False

    elif isinstance(source, str):
        if source != target:  # compare by exact
            return False

    return True

def _match_tags(source: Union[dict, tuple, str], target: dict) -> bool:
    for r, s in target.items():
        if isinstance(source, dict):
            for x, y in source.items():
                if not _match_check(x, r):  # check key match
                    return False
                if not _match_check(y, s):  # check value match
                    return False

        elif isinstance(source, tuple): # check against keys only
            for x in source:
                if _match_check(x, r):  # check key match
                    break
            else:
                return False

        elif isinstance(source, str):
            if not _match_check(source, r):  # check key match
                return False

    return True

def _match_args(source: list, target: list) -> bool:
    for i, x in enumerate(source):
        if i + 1 > len(target):
            break
        y = source[i] 
        if y is None:
            continue # skip current argument index
        if isinstance(y, tuple):
            for z in y:
                if _match_check(z, x):
                    break
            else:
                return False

        elif not _match_check(y, x):
            return False

    return True



class RegexParser:
    def __init__(self, message: Optional[str]):
        self.raw = None
        self.data = {}
        if message: 
            self.line(message)

    def line(self, message: str) -> None:
        match = _message_regex.match(message)
        if (match is None):
            return
        tmp = match.groupdict()
        self.raw = message

        # tags, prefix, verb, params
        self.data = {**tmp}

        match = _prefix_regex.match(self.data['prefix'])
        match = match.groupdict()
        # host, user, nick
        self.data = {**self.data, **match}

        self.data['args'] = []
        self.data['args'] += self.data['params'][:self.data['params'].find(':')].strip().split(' ')
        self.data['args'] += self.data['params'][self.data['params'].find(':')+1:].rstrip(' :').split(':')

    def compare(self, **kwargs) -> bool:
        for k, v in kwargs.items():
            if k == 'tags':  # self.data[k] is a dict
                if isinstance(v, dict) or isinstance(v, tuple) or isinstance(v, str): # allowed types
                    if isinstance(v, tuple): # keys only, convert to dict
                        v = {x: True for x in v}
                    elif isinstance(v, str): # key only, convert to dict    
                        v = {v: True}
                    if not _match_tags(v, self.data[k]):
                        return False
                else:
                    raise Exception("Invalid type for {}: {}".format(k, type(v)))

            elif k == 'args':  # self.data[k] is an array
                if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, str): # allowed types
                    if not isinstance(v, list):
                        v = [v]
                    if not _match_args(v, self.data[k]):
                        return False
                else:
                    raise Exception("Invalid type for {}: {}".format(k, type(v)))

            # self.data[k] is a string
            elif k in ['verb', 'params', 'prefix', 'line', 'host', 'user', 'nick']:
                if isinstance(v, Pattern) or isinstance(v, tuple) or isinstance(v, str): # allowed types
                    if not _match_check(v, self.data[k]):
                        return False
                else:
                    raise Exception("Invalid type for {}: {}".format(k, type(v)))
        return True
    
class CursorParser: # TODO: implement
    pass
