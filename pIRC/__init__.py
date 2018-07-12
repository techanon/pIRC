import sys
from importlib import reload
import socket
import re
from os import environ
from time import sleep as pause
from time import ctime as now
from traceback import print_tb, print_exc
from . import hooks as hook
from .parse import RegexParser
from threading import Thread, Timer
from typing import TypeVar, Optional, Any, NoReturn, Union, Callable

action_regex = re.compile("^ACTION (.*)")

T_Parser = TypeVar('T_Parser', bound=RegexParser)

class Base(object):
    def __init__(self, host: str, **kwargs) -> None:
        """
        Constructor

        Initializes a new pIRC.Base with provided config variables.
        """
        nick = "pIRCBot" if self.__class__ == Base else self.__class__.__name__
        passphrase = environ.get("{}_PASSPHRASE".format(nick), None)

        # setup default values
        self.config = {
            # Host to connect.
            'host': host,

            # Port to connect.
            'port': 6667,

            # The 'nick' part of 'nick!user@host * name'
            'nick': nick,

            # The name used to identify the connection to the server.
            'ident': nick.lower(),

            # The 'user' part of 'nick!user@host * name'
            'name': nick,

            # Passphrase used to authenticate against auth servers (logging in)
            'passphrase': passphrase,

            # The custom display name
            'realname': "pIRC Bot",

            # Channels that the bot will auto-connect to
            'channels': [],

            # Prefix that the bot looks for when scanning for custom commands
            'command': '!',

            # determines whether multiple matches are allowed per recieved line/msg
            'break_on_match': True,

            # Extremely detailed output for logging
            'verbose': True,

            # Dictionary of keywords that get replaced by its value
            # or result of the value if the value is callable
            # Keywords searched for in the form of :keyword:
            'replace': {},

            # Automatically reconnect
            'reconnect': True
        }

        # update with passed config values
        self.config.update(kwargs)
        self.config['replace'].setdefault('command', self.config['command'])

        self._inbuffer = ""
        self.socket = None
        self.listeners = []
        self.queued = []
        self.ERROR = 0
        self.ulist = {}
        self.channels = {}
        self.isupport = {}
        self._quitting = False
        self._running = False

        # init funcs
        self._add_listeners()
        if self.__class__ == Base:
            self.load_hooks()

    def _replace_match(self, match) -> Any:
        if match.group(1) in self.config['replace']:
            val = self.config['replace'][match.group(1)]
            if callable(val):
                return val()
            else:
                return val
        else:
            return ''

    def _matcher_replace(self, message: str) -> str: #TODO: figure out where to use this
        matcher = re.sub(':(\w*):', self._replace_match, message)

    def load_hooks(self) -> None:
        access = self.__class__
        if 'hookscripts' in self.config:
            access = self
        self._hooks = {}
        for func in access.__dict__.values():
            if callable(func) and hasattr(func, '_type'):
                self._hooks.setdefault(func._type.lower(), [])
                if hasattr(func, '_thread'):
                    self._hooks[func._type.lower()].append(
                        func._thread(func, self))
                else:
                    self._hooks[func._type.lower()].append(func)
        if 'load' in self._hooks:
            for func in self._hooks['load']:
                func(self)

    def _listener(self, match: Union[dict, bool], func: Callable, temp: bool=False) -> None:
        self.listeners.append({'temp': temp, 'func': func, 'match': match})

    def _verb_listener(self, verb: str, func: Callable, temp: bool=False) -> None:
        self._listener({'verb': verb}, func, temp)

    def _raw_listener(self, regex: str, func: Callable, temp: bool=False) -> None:
        self._listener(True, func, temp)

    def _code_listener(self, num: int, func: Callable, temp: bool=False) -> None:
        self._verb_listener('{:03d}'.format(num), func, temp)

    def _add_listeners(self) -> None:
        # Custom hooks listeners
        self._add_codes()
        self._add_commands()
        self._raw_listener(self._run_RAW)  # Catch ALL incoming messages

    def _add_codes(self) -> None:
        # Default code commands for bot state management
        self._code_listener(1, self._init_ping)
        self._code_listener(5, self._compile_isupport)
        self._code_listener(353, self._compile_ulist)
        self._code_listener(443, self._alt_nick)
        # Listener for code command hooks
        self._verb_listener(re.compile(r'^\d{3}$'), self._run_CODES)

    def _add_commands(self) -> None:

        # Self management listeners
        # TODO: find out if these need to be converted to code commands
        self._verb_listener('JOIN', self.manage_ulist)
        self._verb_listener('PART', self.manage_ulist)
        self._verb_listener('NICK', self.manage_ulist)
        self._verb_listener('QUIT', self.manage_ulist)
        
        self._verb_listener('MODE', self._ulist_modes)
        self._verb_listener('PING', self._ping)
        self._verb_listener('PONG', self._pong)
        self._verb_listener('ERROR', self._error)

        # Listeners to run hooks
        self._verb_listener('NOTICE', self._run_NOTICE)
        self._verb_listener('PRIVMSG', self._run_PRIVMSG)
        self._verb_listener('QUIT', self._run_QUIT)
        self._verb_listener('PART', self._run_PART)
        self._verb_listener('NICK', self._run_NICK)
        self._verb_listener('JOIN', self._run_JOIN)
        self._verb_listener('MODE', self._run_MODE)
        self._verb_listener('PING', self._run_PING)
        self._verb_listener('PONG', self._run_PONG)
        self._verb_listener('ERROR', self._run_ERROR)


    def _listen(self) -> None:
        """
        Constantly listens to the input from the server. Since the messages come
        in pieces, we wait until we receive 1 or more full lines to start parsing.

        A new line is defined as ending in \r\n in the RFC, but some servers
        separate by \n. This script takes care of both.
        """
        while True:
            if not self._quitting:
                try:
                    self._inbuffer += self.socket.recv(2048)
                except socket.timeout:
                    pass
                # Some IRC daemons disregard the RFC and split lines by \n rather than \r\n.
                temp = self._inbuffer.split("\n")
                self._inbuffer = temp.pop()

                for line in temp:
                    # Strip \r from \r\n for RFC-compliant IRC servers.
                    line = line.rstrip('\r')
                    if len(line) == 0:
                        continue # skip empty lines
                    if self.config['verbose']:
                        print("({0}: {1}) {2}".format(
                            self.config['name'],
                            self.config['host'],
                            line
                        ))
                    self._running = True
                    self._run_listeners(line)
                if self.queue:
                    self._running = True
                    while len(self.queued) > 0:
                        func, args, kwargs = self.queued.pop(0)
                        func(*args, **kwargs)
                self._running = False


    def _run_hooks(self, parser: T_Parser, key: str, once: Optional[bool]=None) -> bool:
        if key in self._hooks:
            for n, func in [(x, y) for x, y in enumerate(self._hooks[key])]:
                if not hasattr(func, '_match') or parser.compare(**func._match):
                    func(parser.data)
                    if hasattr(func, '_once') and func._once is True:
                        del self._hooks[key][n]
                    if self.config['break_on_match']:
                        return False
        return True


    def _run_threads(self) -> True:
        if 'thread' in self._hooks:
            for n, thread in enumerate(self._hooks['thread']):
                if thread.is_shutdown() or thread.is_alive():
                    self._hooks[n] = thread.copy()
                    self._hooks[n].start()
                else:
                    thread.start()
            else:
                return True


    def _run_listeners(self, line: str) -> None:
        """
        Each listener's associated regular expression is matched against raw IRC
        input. If there is a match, the listener's associated function is called
        with all the regular expression's matched subgroups.
        """
        parser = RegexParser(line) # TODO: switch to CursorParser

        for i, info in enumerate(self.listeners):
            temp = info['temp'] is True
            callbacks = info['funcs']
            
            if info['match'] is True:
                pass
            elif info['match'] is False:
                continue
            elif not parser.compare(**info['match']):
                continue

            for callback in callbacks:
                callback(parser)
            if temp:
                del self.listeners[i]

        self._run_hooks(parser, 'once', True)


    def _run_PRIVMSG(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]

        match = action_regex.match(info['message'])
        if match is not None:
            info['message'] = match.groups()[0]
            self._run_hooks(parser, 'action')

        else:
            if info['message'].startswith(self.config['command']):
                info['message'] = info['message'][len(self.config['command']):]
                if info['target'].startswith('#'):
                    if not self._run_hooks(parser, 'chancommand'):
                        return
                else:
                    if not self._run_hooks(parser, 'privcommand')
                        return
                if not self._run_hooks(parser, 'command')
                    return
            if info['target'].startswith('#'):
                if not self._run_hooks(parser, 'channel'):
                    return
                else:
                    if not self._run_hooks(parser, 'private'):
                        return
            if not self._run_hooks(parser, 'privmsg'):
                return
            

    def _run_NOTICE(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]
        if not self._run_hooks(parser, 'notice'):
            return


    def _run_QUIT(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]
        if not self._run_hooks(parser, 'quit'):
            return


    def _run_PART(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]
        if not self._run_hooks(parser, 'part'):
            return


    def _run_NICK(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]
        if not self._run_hooks(parser, 'nick'):
            return


    def _run_JOIN(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]
        if not self._run_hooks(parser, 'join'):
            return


    def _run_MODE(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]
        if not self._run_hooks(parser, 'mode'):
            return


    def _run_PING(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]
        if not self._run_hooks(parser, 'ping'):
            return


    def _run_PONG(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]
        if not self._run_hooks(parser, 'pong'):
            return


    def _run_ERROR(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'][0]
        info['message'] = info['args'][1]
        if not self._run_hooks(parser, 'error'):
            return


    def _run_CODES(self, parser: T_Parser) -> None:
        info = parser.data
        info['target'] = info['args'].pop(0)
        if not self._run_hooks(parser, 'error'):
            return


    def _run_RAW(self, parser: T_Parser) -> None:
        if not self._run_hooks(parser, 'raw'):
            return


    def _alt_nick(self) -> None:
        self.config['nick'] += '_'
        self.nick(self.config['nick'])


    def _error(self, parser: T_Parser) -> None:
        if not self._quitting:
            self.ERROR += 1
            raise Exception(str(line))
        else:
            self._quitting = False


    def _ping(self, parser: T_Parser) -> None:
        self._cmd("PONG", line)
        if 'ping' in self._hooks:
            for func in self._hooks['ping']:
                func(line)


    def _pong(self, parser: T_Parser) -> None:
        if 'pong' in self._hooks:
            for func in self._hooks['pong']:
                func(line)


    def _compile_isupport(self, parser: T_Parser) -> None: # 005
        isupport = {}
        for arg in args:
            if arg.find(' ') > -1:
                break
            x = arg.split('=')
            if len(x) == 1:
                x.append(None)
            isupport[x[0]] = x[1]
        if 'PREFIX' in isupport:
            if 'PREFIX' not in self.isupport:
                self.isupport['PREFIX'] = []
            match = re.match(r'\((\w+)\)(\S+)', isupport['PREFIX'])
            self.isupport['PREFIX'].extend(zip(match.group(1), match.group(2)))


    def _compile_ulist(self, parser: T_Parser) -> None:
        info = parser.data
        if info['args'][0] == '=':
            info['args'].pop(0)
        channel = info['args'][0]
        args = info['args'][1]
        for user in args.split():
            if 'PREFIX' in self.isupport:
                u = list(user)
                m = modes = ''
                while u[0] in [y for x, y in self.isupport['PREFIX']]:
                    m += u.pop(0)
                user = ''.join(u)
                for mode, prefix in self.isupport['PREFIX']:
                    if prefix in m:
                        modes += mode
                self.ulist.setdefault(user, {})
                if modes:
                    self.ulist[user].update({channel: modes})
                else:
                    self.ulist[user].update({channel: ''})
            else:
                self.ulist[user].update({channel: ''})


    def _ulist_modes(self, parser: T_Parser) -> None:
        info = parser.data
        target = info['args'][0]
        modes = info['args'][1]
        args = info['args'][2:]
        #TODO: update usage to parser.data
        state = None
        offset = 0
        modes = list(modes)
        args = args.split()
        for n, mode in enumerate(modes):
            if mode in '+-':
                state = mode
                offset += 1
            else:
                if not state:
                    continue
                elif state == '+':
                    self.ulist[args[n-offset]].update(
                        {user: self.ulist[args[n-offset]][user]+mode}
                    )
                elif state == '-':
                    self.ulist[args[n-offset]].update(
                        {user: self.ulist[args[n-offset]]
                            [user].replace(mode, '')}
                    )


    def _manage_ulist(self, parser: T_Parser) -> None:
        info = parser.data


        if info['verb'] == 'JOIN':
            self.ulist.setdefault(u, {})
            self.ulist[u].update({args: ''})

        elif info['verb'] == 'NICK':
            if u in self.ulist:
                self.ulist[args] = self.ulist[u]
                del self.ulist[u]
            if self.config['nick'] == u:
                self.config['nick'] = args

        elif info['verb'] == 'PART':
            if u == self.config['nick']:
                for u in [x for x in self.ulist.iterkeys()]:
                    del self.ulist[u][args]
                    if not len(self.ulist[u]):
                        del self.ulist[u]
            else:
                del self.ulist[u][args]
                if not len(self.ulist[u]):
                    del self.ulist[u]

        elif info['verb'] == 'QUIT':
            del self.ulist[u]
            

    def _init_ping(self, message: str) -> None:
        self.listeners.prepend({
            'temp': True, 
            'func': self._init, 
            'match': {'command': 'PONG', 'args': ['_init_']} # verify
        })
        self.ping('_init_')

    def _init(self) -> None:
        if self.config['passphrase']:
            self._cmd("PRIVMSG", "NickServ", "identify {}".format(self.config['passphrase']))

        self.ERROR = 0

        # Initialize (join rooms and start threads) if the bot is not
        # auto-identifying, or has just identified.
        if self.config['channels']:
            self.join(*self.config['channels'])
        # TODO: This doesn't ensure that threads run at the right time, e.g.
        # after the bot has joined every channel it needs to.
        self._run_threads()
        if 'connect' in self._hooks:
            for func in self._hooks['connect']:
                func(self)

    def queue(self, func: Callable, *args, **kwargs) -> None:
        self.queued.append((func, args, kwargs))

    def _cmd(self, cmd: str, *args) -> None:
        usecolon = False
        for x in args:
            if x.find(' ') > -1 or len(x) == 0:
                usecolon = True
            if not usecolon:
                cmd += ' {0}'.format(x)
            else:
                cmd += ' :{0}'.format(x)
        self._raw_cmd(cmd)
        

    def _raw_cmd(self, raw_line: str) -> None:
        if self.config['verbose']:
            # prints to console, does not support UTF8. Convert to \u style output?
            print("({0}: {1}) > {2}".format(
                self.config['name'],
                self.config['host'],
                "".join([x if ord(x) < 128 else '?' for x in raw_line])
            ))
        try:
            self.socket.send(raw_line+"\r\n")
        except socket.timeout:
            print(">>>Socket timed out.")

    ### Functions that are common use case for sending commands to the server

    @hook.queue()
    def message(self, targets: Union[List[str], str], messages: Union[List[Tuple[str, int]], List[str], str]) -> None:
        if isinstance(targets, basestring):
            targets = [targets]
        if isinstance(messages, basestring):
            messages = [messages]
        for y in messages:
            z = 1
            if isinstance(y, tuple) and len(y) == 2:
                y, z = y
            for x in target:
                self._cmd("PRIVMSG", x, str(y))
            pause(z)

    @hook.queue()
    def notice(self, targets: Union[List[str], str], messages: Union[List[Tuple[str, int]], List[str], str]) -> None:
        if isinstance(targets, basestring):
            targets = [targes]
        if isinstance(messages, basestring):
            messages = [messages]
        for y in messages:
            z = 1
            if isinstance(y, tuple) and len(y) == 2:
                y, z = y
            for x in target:
                self._cmd("NOTICE", x, str(y))
            pause(z)

    @hook.queue()
    def me(self, targets: Union[List[str], str], messages: Union[List[Tuple[str, int]], List[str], str]) -> None:
        if isinstance(targets, basestring):
            targets = [targes]
        if isinstance(messages, basestring):
            messages = [messages]
        for y in messages:
            z = 1
            if isinstance(y, tuple) and len(y) == 2:
                y, z = y
            for x in target:
                self._cmd("PRIVMSG", x, "ACTION {}".format(y))
            pause(z)

    @hook.queue()
    def join(self, *channels: Tuple[Union[str, tuple]]) -> None:
        for chan in channels:
            key = None
            if isinstance(chan, tuple):
                self._cmd("JOIN", *chan)
            else:
                self._cmd("JOIN", chan)
            self._cmd("MODE", chan)

    @hook.queue()
    def part(self, *channels: Tuple[str]) -> None:
        self._cmd("PART", ','.join(chan for chan in channels))

    @hook.queue()
    def nick(self, nick: Optional[str]=None) -> None:
        if nick is None:
            nick = self.config['name']
        self._cmd("NICK", nick)

    @hook.queue()
    def ping(self, line: str="timeout") -> None:
        self._cmd("PING", line)

    @hook.queue()
    def quit(self, message: str="Connection Closed") -> None:
        self._cmd("QUIT", message)
        self._quitting = True
        self._close()

    # func that makes the bot's thread pasue for a given amount of seconds

    @hook.queue()
    def pause(self, time: int=1) -> None:
        pause(time)

    # def color(self, matcher) -> str:
    #     return re.sub(':(\d)(?:,(\d))?:', _color_replace, matcher)

    # def _color_replace(self, match):
    #     if len(match.groups()) > 1:
    #         if int(match.group(1)) < 16 and int(match.group(2)) < 16:
    #             return '\x02{0},{1}'.format(match.group(1), match.group(2))

    #     if len(match.groups()) > 0:
    #         if int(match.group(1)) < 16:
    #             return '\x02{0}'.format(match.group(1))

    #     return ''

    @hook.queue()
    def reconnect(self) -> None:
        """
        Function that executes an optional connection reset.

        Closes socket
        Checks for failed attempt count and stalls connection accordingly
        If the reconnect config is True it will reconnect, otherwise the 
        connection and thread will end
        """
        if self.socket:
            self._close(False)
            print("--- {0}: {1} ---".format(
                self.config['name'],
                self.config['host']
            ))
            if self.config['verbose']:
                print("Connection closed.")
            if 'disconnect' in self._hooks:
                for func in self._hooks['disconnect']:
                    func(self)

        if self.ERROR >= 10:
            print("There have been 10 or more failed attempts to reconnect.")
            print(
                "Please wait till the bot is able to do so, then press enter to try again.")
            raw_input('Press ENTER to continue')
        elif self.ERROR:
            waittime = 30*self.ERROR+30
            print("Error occurred (see stack trace). Waiting {0} seconds to reconnect.".format(
                waittime
            ))
            pause(waittime)
        elif self.config['reconnect']:
            # raw_input()
            if self.config['verbose']:
                print("Waiting 10 seconds to reconnect...")
            pause(8)

        if self.config['reconnect']:
            pause(2)
            if self.config['verbose']:
                print("Opening new connection...")
            return True
        else:
            self.ERROR = 0

    def connect(self) -> None:
        '''
        Connects to the IRC server with the options defined in `config`
        '''
        while True:
            self.isupport = {}
            self.ulist = {}
            self._connect()

            try:
                self._listen()
            except (KeyboardInterrupt, SystemExit):
                pass
            except socket.error:
                if not self._quitting:
                    raise Exception(
                        "Unexpected socket error. Resetting connection."
                    )
            except:
                print(" ")
                print("Exception occured:", sys.exc_info()[1])
                print(" ")
                print_tb(sys.exc_info()[2])
                print(" ")
                f = open('{0} - BotLog.txt'.format(self.config['name']), 'a')
                f.write("\r\n")
                f.write(now())
                f.write("\r\nConnection: {0}\r\n".format(self.config['host']))
                print_exc(None, f)
                f.write("\r\n")
                f.close()
                if self.reconnect() is True:
                    continue
            finally:
                self._close()
                break

    def _connect(self) -> None:
        """Sets socket connection and sends initial info to the server."""
        self.socket = socket.socket()
        self.socket.connect((self.config['host'], self.config['port']))
        self.socket.settimeout(1.0)
        if self.config['verbose']:
            print("({0}: {1}) Connection successful".format(
                self.config['name'],
                self.config['host']
            ))
        self._cmd('CAP LS')
        self._cmd('NICK', self.config['nick'])
        self._cmd('USER', self.config['ident'], config['host'], '0', self.config['realname'])
        self._cmd('CAP REQ :multi-prefix')
        self._cmd('CAP END')

    def _close(self, runhooks: bool=True) -> None:
        if 'thread' in self._hooks:
            for thread in self._hooks['thread']:
                thread.shutdown()
        if self.socket:
            self.socket.shutdown(socket.SHUT_RDWR)
            self.socket.close()
            self.socket = None
        if runhooks:
            if 'close' in self._hooks:
                for func in self._hooks['close']:
                    func(self)

    @hook.queue()
    def close(self) -> NoReturn:
        if self.config['verbose']:
            print("Closing connection and thread for {0}:{1}".format(
                self.config['name'],
                self.config['host']
            ))
        raise SystemExit()


class Bot(Base):
    """
    This class is a high-level wrapper for the base bot to allow for dynamic reloading of hooks.

    Config Vars

    host            (string)    : address to connect to
    port            (integer)   : port to connect with
    name            (string)    : bot's original name
    ident           (string)    : the 'user' part of 'nick!user@host * name'
    nick            (string)    : the 'nick' part of 'nick!user@host * name'; bot's temporary name
    realname        (string)    : the 'name' part of 'nick!user@host * name'
    channels        (list)      : a list of channels to autojoin on successful connect
    command         (string)    : a (sequence of) character(s) the bot will respond to for a command
    passphrase      (string)    : passed to nickserv for authentication
    break_on_match  (bool)      : determines whether multiple matches are allowed per recieved line
    verbose         (bool)      : determines whether debug info is printed to the console
    reconnect       (bool)      : determines whether to automatically reconnect if an error/exception occurs   
    replace         (dict)      : dictionary for custom regex variable replacement; form of ':key:';
                                    if key does not exist in the dict, :key: is removed from the regex
    hookscripts     (list)      : a list of module names that contain custom hooks
    reload_regex    (string)    : custom regex to be used in the default module reload implementation
    reload_func     (callable)  : custom func to be used in the default module reload implementation
    reload_override (bool)      : determines whether the default module implementation is used
    ref             (callable)  : optional config to allow reference to a parent BotGroup class to grant 
                                    interaction with other connections
    """

    def __init__(self, host: str, **kwargs) -> None:

        super(Bot, self).__init__(host, {
            'hookscripts': [],
            'reload_override': False,
            'ref': None
        }, **kwargs)

        self.load_hooks()

        if not self.config['reload_override']:
            self.config.setdefault(
                'reload_regex',
                '^:(\S+) PRIVMSG (\S+) :{0}reload$'.format(
                    self.config['command']
                )
            )
            self.config.setdefault('reload_func', self.load_hooks)
            self._add_raw_listener(
                self.config['reload_regex'],
                self.config['reload_func']
            )

    def load_hooks(self) -> None:
        if callable(self.config['hookscripts']):
            try:
                scripts = iter(self.config['hookscripts'])
            except TypeError:
                scripts = self.config['hookscripts']()
        elif isinstance(self.config['hookscripts'], basestring):
            scripts = [self.config['hookscripts']]
        else:
            scripts = list(self.config['hookscripts'])

        old_funcs = [(k, v) for k, v in self.__dict__.items()
                     if hasattr(v, '_type')]

        if len(old_funcs) and self.config['verbose']:
            print("\n({0}: {1}) Unloading old hooks...".format(
                self.config['name'],
                self.config['host']
            ))
            print("----------------------")

        for k, v in old_funcs:
            delattr(self, k)
            if self.config['verbose']:
                print("({0}: {1})   -'{2}' successfully removed.".format(
                    self.config['name'],
                    self.config['host'],
                    k
                ))

        if self.config['verbose']:
            print("\n({0}: {1}) Loading hooks...".format(
                self.config['name'],
                self.config['host']
            ))
            print("----------------------")

        for script in scripts:
            try:
                if script in sys.modules:
                    reload(sys.modules[script])
                else:
                    sys.modules[script] = __import__(script)

                if self.config['verbose']:
                    print("\n({0}: {1}) '{2}' successfully imported.".format(
                        self.config['name'],
                        self.config['host'],
                        script
                    ))
            except:
                if self.config['verbose']:
                    print("\n({0}: {1}) Error: >>>{2}".format(
                        self.config['name'],
                        self.config['host'],
                        str(sys.exc_info()[1])
                    ))
                    print_tb(sys.exc_info()[2])
                    print("({0}: {1}) >>>Unable to import '{2}'. Skipping...".format(
                        self.config['name'],
                        self.config['host'],
                        script
                    ))
            else:
                for k, v in sys.modules[script].__dict__.items():
                    if hasattr(v, '_type'):
                        setattr(self, k, v)
                        if self.config['verbose']:
                            print("({0}: {1})   -'{2}' successfully added.".format(
                                self.config['name'],
                                self.config['host'],
                                k
                            ))
        print(" ")
        super(Bot, self).load_hooks()

    def ns(self, message: str) -> None:
        self.message("NickServ", message)

    def cs(self, message: str) -> None:
        self.message("ChanServ", message)


T_Base = TypeVar('T_Base', bound=Base)


class BotGroup(object):
    def __init__(self, ref: T_Base=Bot, interval: int=0) -> None:
        """
        Constructor

        ref = custom class reference to use for the bot instance.
        interval = time in seconds the bot instance threads are 
            checked for crash recovery. If zero, thread recovery 
            is disabled.
        """
        self._bots = {}
        self.rethread = interval
        self.monitor = None
        self.ref = ref

    def __getitem__(self, host: str) -> str:
        """
        Convenince method to access bot instances via connected host.
        """
        return self._bots[host]['instance']

    def network(self, host: str, ref: Optional[T_Base]=None, **kwargs) -> None:
        """
        Method to declare/re-declare a network connection.

        host = name of the host to connect to
        ref = optional custom reference to use for the bot instance
        kwargs = keyword arguements to be used for the bot's 
            configuration variables.
        """
        if ref is None:
            ref = self.ref
        self._bots[host] = {}
        self._bots[host]['instance'] = ref(host, ref=self, **kwargs)
        self._bots[host]['thread'] = Thread(
            None,
            self._bots[host]['instance'].connect,
            name=host
        )

    def copy_network(self, old: str, new: Optional[str]=None, ref: Optional[T_Base]=None) -> None:
        """
        Convenince method that duplicates the config data 
            from an existing host to a new host.
        """
        if not new:
            new = old
        if old in self._bots:
            bot = self._bots[old]['instance']
            kwargs = bot.config
            if (ref is None):
                ref = bot.__class__
            return ref(host, ref=self, **kwargs)

    def get(self, host: str) -> Optional[T_Base]:
        return self._bots.get(host, None)

    def get_all(self, by: Optional[str]=None) -> List[Any]:
        """
        Conveneince method for accessing the bot dictionary via list.
        """
        if by == 'hosts':
            return [k for k in self._bots.keys()]
        elif by == 'bots':
            return [v for v in self._bots.values()]
        else:
            return [(k, v) for k, v in self._bots.items()]

    def connect(self, contain: bool=False) -> None:
        """
        Method called to start the bot instance threads.
        Initialzes optional thread manager thread if specified.
        If True is passed as an argument, the class takes control
                of the main thread by sending it directly to the console
        """
        for bot in self.get_all('bots'):
            bot['thread'].start()
        else:
            if self.rethread:
                self.monitor = Timer(
                    self.rethread,
                    self.thread_check,
                    name='BotStatusMonitor'
                )
                self.monitor.start()
        if contain:
            console(self)

    def load_hooks(self):
        """
        Convenince method to reload all hooks and restart
            all threads for each bot instance.
        """
        for x in self.get_all('bots'):
            x['instance'].load_hooks()
            x['instance']._runthreads()

    def thread_check(self):
        """
        Method to check if bot instance threads have been killed.
        Restarts thread with fresh instance if so.
        """
        for host, bot in self.get_all():
            thread = bot['thread']
            if not thread.is_alive():
                if (bot['instance'].config['verbose']):
                    print(
                        'Bot thread for {0} died (see stack trace). Rebooting...'.format(host))
                bot['instance'].close()
                while bot['instance'].socket:
                    pass
                new_bot = self.copy_network(
                    bot['instance'].config['host'], bot['instance'].config['host'], bot['instance'].__class__)
                new_thread = Thread(
                    None,
                    new_bot.connect,
                    name=thread.name
                )
                del self._bots[host]['thread']
                del self._bost[host]['instance']
                self._bots[host]['thread'] = new_thread
                self._bots[host]['instance'] = new_bot
                self._bots[host]['thread'].start()


T_Group = TypeVar('T_Group', BotGroup)


def console(bot: Optional[Union[T_Base, T_Group]]=None, **kwargs) -> None:
    """
    Function for direct interaction via terminal.
    Useful for testing, not advised for production code

    Params:
    -bot = Instance of the bot/botgroup you wish to control via console.
    -kwargs = dict of global variables defined in the __main__ module give the console access to.
    """

    if kwargs:
        # Define global access for variables passed to the function
        for x, y in kwargs.items():
            globals()[x] = y

    main = __import__('__main__')
    for x, y in main.__dict__.items():
        if x != 'bot' and (isinstance(y, BotGroup) or isinstance(y, Base)):
            # Creates local variable for the relevant variables from the __main__ module
            locals()[x] = y
            if x.lower() not in main.__dict__ \
                or not (
                isinstance(main.__dict__[x.lower()], BotGroup) or
                isinstance(main.__dict__[x.lower()], Base)
            ):
                # Alternate local variabe with all lowercase as the variable name
                # as long as a variable by the same name won't be imported
                locals()[x.lower()] = y

    while True:  # Control loop
        try:
            a = raw_input()
            print('===============')
            print(eval(a))
            print('===============')
        except:
            # Catch for exceptions to allow the console to continue operating.
            print('>>>Exception occured: {0}'.format(sys.exc_info()[1]))
            print_tb(sys.exc_info()[2])
            print('===============')


def modload(*modlist) -> None:
    """
    Convenince function for (re)loading custom modules.
    """
    for x in modlist:
        # If exists, reload
        if x in sys.modules:
            reload(sys.modules[x])
            print(x + ' has been reloaded.')
        else:
            # If not exists, import
            sys.modules[x] = __import__(x)
            print(x + ' has been loaded.')
