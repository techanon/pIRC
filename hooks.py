from functools import wraps
import re
from typing import Optional, Callable, Union, Pattern, Any
from .threads import JobThread

# utility functions for doing dynamic replacements in matches
_replace_format = re.compile(r':(\w*):')

def _replace_match(self, match) -> str:
    if match[1] in self.config['replace']:
        val = self.config['replace'][match[1]]
        if callable(val):
            return str(val(self))
        else:
            return str(val)
    else:
        return ''

def _replace(self, original: Union[Pattern, str]) -> str:
    if isinstance(original, Pattern):
        matcher = re.sub(_replace_format, self._replace_match, original.pattern)
        return re.compile(matcher)
    else:
        return re.sub(_replace_format, self._replace_match, original)



# Special hook that allows the related function to be called from any thread
# and then execute in the bot's actual thread. 
# Basiclally it queues the function to be ran on the bot's own terms
def queue():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            args[0].queue(func, *args, **kwargs)
        return wrapped_command
    return wrapped

# Hook that is triggered upon loading/reloading of 
def load():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'LOAD'
        return wrapped_command
    return wrapped

def close():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'CLOSE'
        return wrapped_command
    return wrapped


def connect():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'CONNECT'
        return wrapped_command
    return wrapped


def disconnect():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(*args, **kwargs):
            return func(*args, **kwargs)
        wrapped_command._type = 'DISCONNECT'
        return wrapped_command
    return wrapped

### Hooks that trigger on common verbs

def ping():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(_self, info):
            return func(_self, info)
        wrapped_command._type = 'PING'
        return wrapped_command
    return wrapped


def pong():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(_self, info):
            return func(_self, info)
        wrapped_command._type = 'PONG'
        return wrapped_command
    return wrapped


def join():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(_self, info):
            return func(_self, info)
        wrapped_command._type = 'JOIN'
        return wrapped_command
    return wrapped


def nick():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(_self, info):
            return func(_self, info)
        wrapped_command._type = 'NICK'
        return wrapped_command
    return wrapped


def part():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(_self, info):
            return func(_self, info)
        wrapped_command._type = 'PART'
        return wrapped_command
    return wrapped


def quit():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        @wraps(func)
        def wrapped_command(_self, info):
            return func(_self, info)
        wrapped_command._type = 'QUIT'
        return wrapped_command
    return wrapped


### Hooks that trigger on the PRVIMSG verb, custom match against the message

class command(object):
    """ 
    TODO: Documentation 
    """
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func: Callable):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(_self, info):
            if isinstance(message, Pattern):
                info['match'] = _replace(_self, message).match(info['message'])
            return func(_self, info)
        wrapped_command._type = 'COMMAND'
        wrapped_command._match = {'message': message}
        return wrapped_command


class chancommand(object):
    """ 
    TODO: Documentation 
    """
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func: Callable):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(_self, info):
            if isinstance(message, Pattern):
                info['match'] = _replace(_self, message).match(info['message'])
            return func(_self, info)
        wrapped_command._type = 'CHANCOMMAND'
        wrapped_command._match = {'message': message}
        return wrapped_command


class privcommand(object):
    """ 
    TODO: Documentation 
    """
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func: Callable):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(_self, info):
            if isinstance(message, Pattern):
                info['match'] = _replace(_self, message).match(info['message'])
            return func(_self, info)
        wrapped_command._type = 'PRIVCOMMAND'
        wrapped_command._match = {'message': message}
        return wrapped_command


class privmsg(object):
    """ 
    TODO: Documentation 
    """
    # verb - PRIVMSG
    # Matches both direct and channel messages
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func):
        # Default the command's name to an exact match of the function's name.
        # ^func name$
        message = self._match
        if message is None:
            message = re.compile('^{}$'.format(func.func_name.replace('_', ' ')))

        @wraps(func)
        def wrapped_command(_self, info):
            if isinstance(message, Pattern):
                info['match'] = _replace(_self, message).match(info['message'])
            return func(_self, info)
        wrapped_command._type = 'PRIVMSG'
        wrapped_command._match = {'message': message}
        return wrapped_command


class channel(object):
    """ 
    TODO: Documentation 
    """
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
        def wrapped_command(_self, info):
            if isinstance(message, Pattern):
                info['match'] = _replace(_self, message).match(info['message'])
            return func(_self, info)
        wrapped_command._type = 'CHANNEL'
        wrapped_command._match = {'message': message}
        return wrapped_command


class private(object):
    """ 
    TODO: Documentation 
    """
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
        def wrapped_command(_self, info):
            if isinstance(message, Pattern):
                info['match'] = _replace(_self, message).match(info['message'])
            return func(_self, info)
        wrapped_command._type = 'PRIVATE'
        wrapped_command._match = {'message': message}
        return wrapped_command


class action(object):
    """ 
    TODO: Documentation 
    """
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

        @wraps(func)
        def wrapped_command(_self, info):
            if isinstance(message, Pattern):
                info['match'] = _replace(_self, message).match(info['message'])
            return func(_self, info)
        wrapped_command._type = 'ACTION'
        wrapped_command._match = {'message': message}
        return wrapped_command

### Hooks that trigger on the NOTICE verb, custom match against the message

class notice(object):
    """ 
    TODO: Documentation 
    """
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
        def wrapped_command(_self, info):
            if isinstance(message, Pattern):
                info['match'] = _replace(_self, message).match(info['message'])
            return func(_self, info)
        wrapped_command._type = 'NOTICE'
        wrapped_command._match = {'message': message}
        return wrapped_command
        
### Hooks that trigger on a numeric verb

class code(object):
    """ 
    TODO: Documentation 
    """
    # verb - 3 digit number
    def __init__(self, code: int):
        if code > 999:
            raise Exception(
                "Numeric code must be an integer less than 999 for a code hook."
            )
        self._code = code

    def __call__(self, func: Callable):
        @wraps(func)
        def wrapped_command(_self, info):
            return func(_self, info)
        wrapped_command._type = 'CODE'
        wrapped_command._match = {'verb': '{:03d}'.format(self._code)}
        return wrapped_command

### Hooks that trigger for each incoming line, custom match against the whole line

class raw(object):
    """ 
    TODO: Documentation 
    """
    # Runs against unparsed line
    def __init__(self, match: Optional[Union[str, Pattern]]=None):
        self._match = match

    def __call__(self, func: Callable):
        match = self._match
        if match is None:
            match = True

        @wraps(func)
        def wrapped_command(_self, info):
            if isinstance(match, Pattern):
                info['match'] = _replace(_self, match).match(info['raw'])
            return func(_self, info)
        wrapped_command._type = 'RAW'
        wrapped_command._match = {'raw': match}
        return wrapped_command

### Hooks that trigger on a specific interval or interval range in seconds, specify the min and max wait time

def interval(min: int, max: Optional[int]=None):
    """ 
    TODO: Documentation 
    """
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
# @hooks.once()
# @hooks.code(420)
# def custom_function(val):
#   print("This will wait for a line with verb '420', run, then be removed from further execution")

def once():
    """ 
    TODO: Documentation 
    """
    def wrapped(func: Callable):
        if hasattr(func, '_type') and not hasattr(func, '_thread'):
            # only declare once on existing hooked functions that aren't threads
            func._once = True
        return func
    return wrapped
