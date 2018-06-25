from functools import wraps
from typing import Optional, Callable, Union
from typing.re import Pattern
from .threads import JobThread

# Special hook that allows the related function to be called from any thread
# and then execute in the bot's actual thread. 
# Basiclally it queues the function to be ran on the bot's own terms
def queue():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            args[0].queue(func, *args, **kwargs)
        return wrapped_command
    return wrapped

# Hook that is triggered upon loading/reloading of 
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


def connect():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'CONNECT'
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

### Hooks that trigger on common verbs

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


def join():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'JOIN'
        return wrapped_command
    return wrapped


def nick():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'NICK'
        return wrapped_command
    return wrapped


def part():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PART'
        return wrapped_command
    return wrapped


def quit():
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'QUIT'
        return wrapped_command
    return wrapped


### Hooks that trigger on the PRVIMSG verb, custom match against the message

class command(object):
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func: Callable):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'COMMAND'
        wrapped_command._match = {'message': message}
        return wrapped_command


class chancommand(object):
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func: Callable):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PRIVCOMMAND'
        wrapped_command._match = {'message': message}
        return wrapped_command


class privcommand(object):
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func: Callable):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PRIVCOMMAND'
        wrapped_command._match = {'message': message}
        return wrapped_command


class privmsg(object):
    # verb - PRIVMSG
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PRIVMSG'
        wrapped_command._match = {'message': message}
        return wrapped_command


class channel(object):
    # verb - PRIVMSG
    # args[0] - starts with # or &
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'CHANNEL'
        wrapped_command._match = {'message': message}
        return wrapped_command


class private(object):
    # verb - PRIVMSG
    # args[0] - does /not/ start with a # or &
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'PRIVATE'
        wrapped_command._match = {'message': message}
        return wrapped_command


class action(object):
    # verb - PRIVMSG
    # args[1] - ACTION
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        match = {'message': message}

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'ACTION'
        wrapped_command._match = {'message': message}
        return wrapped_command

### Hooks that trigger on the NOTICE verb, custom match against the message

class notice(object):
    # verb - NOTICE
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'NOTICE'
        wrapped_command._match = {'message': message}
        return wrapped_command
        
### Hooks that trigger on a numeric verb

class code(object):
    # verb - 3 digit number
    def __init__(self, code: int):
        if not code or not isinstance(code, int) or code > 999:
            raise Exception(
                "Numeric code must be present as a 3 digit integer for a code hook."
            )
        self._code = code

    def __call__(self, func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'CODE'
        wrapped_command._match = {'verb': self._code}
        return wrapped_command

### Hooks that trigger for each incoming line, custom match against the whole line

class raw(object):
    # Runs against unparsed line
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func: Callable):
        match = self._match
        if match is None:
            match = True

        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'RAW'
        wrapped_command._match = {'line': match}
        return wrapped_command

### Hooks that trigger on a specific interval or interval range in seconds, specify the min and max wait time

def interval(min: int, max: Optional[int]=None):
    def wrapped(func):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'INTERVAL'
        wrapped_command._thread = JobThread
        wrapped_command._min = min
        wrapped_command._max = max
        return wrapped_command
    return wrapped

### Hook that is only called once, removes self after execution
# must be declared only on an already hooked function
# eg
#
# @once()
# @code(420)
# def custom_function(val):
#   print("This will wait for a line with verb '420', run, then be removed from further execution")

def once():
    def wrapped(func: Callable):
        if hasattr(func, '_type') and not hasattr(func, '_thread'):
            # only declare once on existing hooked functions that aren't threads
            func._once = True
        return func
    return wrapped
