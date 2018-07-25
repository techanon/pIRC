
import re
from typing import Optional, Any, Union, Callable, Pattern



def _match_check(source: Union[Pattern, tuple, str], target: str) -> bool:
    if isinstance(source, tuple):  # match for any
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

        elif isinstance(source, tuple):  # check against keys only
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
            continue  # skip current argument index
        if isinstance(y, tuple):
            for z in y:
                if _match_check(z, x):
                    break
            else:
                return False

        elif not _match_check(y, x):
            return False

    return True


class Parser:
    def __init__(self, line: Optional[str] = None):
        self.data = {}
        if line: self.parse(line)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def parse(self, line: str) -> None:
        self.data = {
            'raw': line,
            'tags': None,
            'source': None,
            'verb': None,
            'args': []
        }

        args = line.split(' ')
        if args[0].startswith('@'):
            # process message tags
            self.data['tags'] = {}
            tags = args.pop(0).lstrip('@')
            for x in tags.split(';'):
                if len(x):
                    y = tuple(x.split('='))
                    if len(y) == 1:
                        y += (True,)
                    if len(y[0]) > 0:
                        self.data['tags'][y[0]] = y[1]

        if args[0].startswith(':'):
            # process message source
            source = args.pop(0).lstrip(':')
            self.data['source'] = {}
            user = nick = host = None
            if source.find('@') > -1:
                front, host = tuple(source.split('@'))
                if len(front):
                    if front.find('!') > -1:
                        nick, user = tuple(front.split('!'))
                    else:
                        nick = front
            else:
                host = source
            self.data['source']['raw'] = source
            self.data['source']['host'] = host
            self.data['source']['user'] = user
            self.data['source']['nick'] = nick

        self.data['verb'] = args.pop(0)

        for i, arg in enumerate(args):
            if arg.startswith(':'): #process trailing arg
                args = args[:i] + [' '.join(args[i:]).lstrip(':')]
                break
        self.data['args'] = args

    def compare(self, kwargs) -> bool:
        for k, v in kwargs.items():
            if k == 'tags':  # self.data[k] is a dynamic dict
                if isinstance(v, dict) or isinstance(v, tuple) or isinstance(v, str):  # allowed types
                    if isinstance(v, tuple):  # keys only, convert to dict
                        v = {x: True for x in v}
                    elif isinstance(v, str):  # key only, convert to dict
                        v = {v: True}
                    if not _match_tags(v, self.data[k]):
                        return False
                else:
                    raise Exception(
                        "Invalid type for {}: {}".format(k, type(v)))

            elif k == 'source': # self.data[k] is a limited dict
                if isinstance(v, Pattern) or isinstance(v, tuple) or isinstance(v, str): # raw source match
                    if not _match_check(v, self.data[k]['raw']):
                        return False

                elif isinstance(v, dict): # match against fields
                    for o in ['raw', 'host', 'user', 'nick']:
                        if isinstance(v[o], Pattern) or isinstance(v[o], tuple) or isinstance(v[o], str):
                            if o in v and not _match_check(v[o], self.data[k][o]):
                                return False
                        else:
                            raise Exception(
                                "Invalid type for {}[{}]: {}".format(k, o, type(v)))
                else:
                    raise Exception(
                        "Invalid type for {}: {}".format(k, type(v)))


            elif k == 'args':  # self.data[k] is an array
                if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, str):  # allowed types
                    if not isinstance(v, list):
                        v = [v]
                    if not _match_args(v, self.data[k]):
                        return False
                else:
                    raise Exception(
                        "Invalid type for {}: {}".format(k, type(v)))

            # self.data[k] is a string
            else:
                if isinstance(v, Pattern) or isinstance(v, tuple) or isinstance(v, str):  # allowed types
                    if not _match_check(v, self.data[k]):
                        return False
                else:
                    raise Exception(
                        "Invalid type for {}: {}".format(k, type(v)))
        return True
