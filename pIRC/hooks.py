from functools import wraps
from typing import Optional, Callable

def queue():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            args[0].queue(func, *args, **kwargs)
        return wrapped_command
    return wrapped


def load():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'LOAD'
        return wrapped_command
    return wrapped


def close():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'CLOSE'
        return wrapped_command
    return wrapped


def ping():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PING'
        return wrapped_command
    return wrapped


def pong():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PONG'
        return wrapped_command
    return wrapped


def connect():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'CONNECT'
        return wrapped_command
    return wrapped


def join():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'JOIN'
        wrapped_command._matcher = r'^:(\S+) JOIN :?(.*)'
        return wrapped_command
    return wrapped


def nick():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'NICK'
        wrapped_command._matcher = r'^:(\S+) NICK :?(.*)'
        return wrapped_command
    return wrapped


def part():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PART'
        wrapped_command._matcher = r'^:(\S+) PART :?(.*)'
        return wrapped_command
    return wrapped


def quit():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'QUIT'
        wrapped_command._matcher = r'^:(\S+) QUIT :?(.*)'
        return wrapped_command
    return wrapped


def disconnect():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'DISCONNECT'
        return wrapped_command
    return wrapped


class command(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func: Callable):
        # Default the command's name to an exact match of the function's name.
        # ^func_name$
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'COMMAND'
        wrapped_command._matcher = matcher
        return wrapped_command


class chancommand(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func: Callable):
        # Default the command's name to an exact match of the function's name.
        # ^func_name$
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PRIVCOMMAND'
        wrapped_command._matcher = matcher
        return wrapped_command


class privcommand(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func: Callable):
        # Default the command's name to an exact match of the function's name.
        # ^func_name$
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PRIVCOMMAND'
        wrapped_command._matcher = matcher
        return wrapped_command


class code(object):
    def __init__(self, code: int, matcher: Optional[str]=None):
        if not code or isinstance(code, int) and len(code) < 4:
            raise Exception(
                "Numeric code must be present as a 3 digit integer for a code hook."
            )
        self._code = code
        self._matcher = matcher

    def __call__(self, func: Callable):
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'CODE'
        wrapped_command._code = self.code
        wrapped_command._matcher = matcher
        return wrapped_command


class raw(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func):
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'RAW'
        wrapped_command._matcher = matcher
        return wrapped_command


class once(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func):
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'ONCE'
        wrapped_command._matcher = matcher
        return wrapped_command


class text(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func):
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'TEXT'
        wrapped_command._matcher = matcher
        return wrapped_command


class channel(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func):
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'CHANNEL'
        wrapped_command._matcher = matcher
        return wrapped_command


class private(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func):
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PRIVATE'
        wrapped_command._matcher = matcher
        return wrapped_command


class action(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func):
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'ACTION'
        wrapped_command._matcher = matcher
        return wrapped_command


class notice(object):
    def __init__(self, matcher: Optional[str]=None):
        self._matcher = matcher

    def __call__(self, func):
        matcher = self._matcher
        if matcher is None:
            matcher = r'^%s$' % func.func_name.replace('_', ' ')

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'NOTICE'
        wrapped_command._matcher = matcher
        return wrapped_command


def interval(min: int, max: Optinal[int]=None):
    def wrapped(func):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'THREAD'
        wrapped_command._min = min
        wrapped_command._max = max
        return wrapped_command
    return wrapped
