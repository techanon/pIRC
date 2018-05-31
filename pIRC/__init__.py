import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import socket
import re
from os import environ
from time import sleep as pause
from time import ctime as now
from traceback import print_tb, print_exc
from threads import JobThread
import hooks as hook
from threading import Thread, Timer
from typing import Dict, Tuple, List, Set, Mapping, Iterator, TypeVar, Generic, Optional, Any, NoReturn



class Base(object):
    def __init__(self, host: str, **kwargs) -> None:
        """
        Constructor

        Initializes a new pIRC.Base with provided config variables.
        """
        nick = "pIRCBot" if self.__class__ == Base else self.__class__.__name__
        password = environ.get('PASSWORD', None)

        self.config = dict(kwargs)
        # Host to connect.
        self.config.setdefault('host', host)
        # Port to connect.
        self.config.setdefault('port', 6667)
        # Name visable to the server
        self.config.setdefault('nick', nick)
        # List of names that the bot will respond to on a command hook
        self.config.setdefault('names', [self.config['nick']])
        #
        self.config.setdefault('ident', nick.lower())
        self.config.setdefault('name', self.config['nick'])
        self.config.setdefault('realname', "pIRC Bot")
        self.config.setdefault('channels', [])
        self.config.setdefault('command', '!')
        self.config.setdefault('password', password)
        self.config.setdefault('break_on_match', True)
        self.config.setdefault('verbose', True)
        self.config.setdefault('replace', {})
        self.config.setdefault('reconnect', True)
        self.config.setdefault('auth', {})

        self._inbuffer = ""
        self.socket = None
        self.listeners = {}
        self.queued = []
        self.ERROR = 0
        self.ulist = {}
        self.isupport = {}
        self._quitting = False
        self._running = False

        # init funcs
        self._add_listeners()
        self._compile_strip_prefix()
        if self.__class__ == Base:
            self.load_hooks()

    def _compile_strip_prefix(self) -> None:
        """
        regex example:
        ^(((BotA|BotB)[,:]?\s+)|%)(.+)$

        names = [BotA, BotB]
        command = %
        """
        name_regex_str = r'^(?:(?:(%s)[,:]?\s+)|%s)(.+)$' %\
            (re.escape("|".join(self.config['names'])),
             re.escape(self.config['command']))
        self._name_regex = re.compile(name_regex_str, re.IGNORECASE)

    def load_hooks(self) -> None:
        access = self.__class__
        if 'hookscripts' in self.config:
            access = self
        self._hooks = {}
        for func in access.__dict__.values():
            if callable(func) and hasattr(func, '_type'):
                self._hooks.setdefault(func._type.lower(), [])
                if func._type == 'THREAD':
                    self._hooks[func._type.lower()].append(
                        JobThread(func, self))
                else:
                    self._hooks[func._type.lower()].append(func)
        if 'load' in self._hooks:
            for func in self._hooks['load']:
                func(self)

    def _add_listeners(self) -> None:
        self._listener(r'^(.*)$', self._filterraw)
        self._listener(r'^:\S+ (\d{3}) \S+ :?(.*)', self._filtercode)
        self._listener(r'^:(\S+) NOTICE (\S+) :(.*)', self._filternotice)
        self._listener(r'^:(\S+) PRIVMSG (\S+) :(.*)', self._filtermsg)
        self._listener(
            r'^:(?P<user>\S+) (?P<action>JOIN|PART|NICK|QUIT) :?(?P<args>.*)', self._manage_ulist)
        self._listener(
            r'^:\S+ (?P<action>MODE) (?P<channel>\S+) (?P<modes>[+\-]\w+) (?P<args>.*)', self._ulist_modes)
        self._listener(r'^:\S+ PONG \S+ :_init_', self._init)
        self._listener(r'^PING :(.*)', self._ping)
        self._listener(r'^PONG :(.*)', self._pong)
        self._listener(r'^ERROR (.*)', self._error)
        self._code_listener(1, self._init_ping)
        self._code_listener(5, self._compile_isupport)
        self._listener(r'^:\S+ 353 \S+ \S (\#\w+) :(.*)', self._compile_ulist)
        self._code_listener(443, self._alt_nick)

    def _listener(self, regex: str, func: Callable, temp: bool=False) -> None:
        array = self.listeners.setdefault(
            re.compile(regex),
            {'temp': temp, 'funcs': []}
        )
        array['funcs'].append(func)

    def _raw_listener(self, regex: str, func: Callable, temp: bool=False) -> None:
        self._listener(r'%s' % regex, func, temp)

    def _code_listener(self, num: int, func: Callable, temp: bool=False) -> None:
        self._listener(r'^:\S+ %03d \S+ :?(.*)' % num, func, temp)

    def _strip_prefix(self, message: str) -> Optional[str]:
        """
        Checks if the bot was called by a user.
        Returns the suffix if so.

        Prefixes include the bot's nick as well as a set symbol.
        """

        search = self._name_regex.search(message)
        if search:
            return search.groups()[1]
        return None

    def _filtermsg(self, sender: str, target: str, line: str) -> None:
        line = line.strip()
        suffix = self._strip_prefix(line)
        to_continue = True
        if suffix:
            if target.startswith('#'):
                if 'chancommand' in self._hooks:
                    if to_continue:
                        to_continue = self._parsemsgs(
                            target,
                            sender,
                            suffix,
                            self._hooks['chancommand']
                        )
            else:
                if 'privcommand' in self._hooks:
                    if to_continue:
                        to_continue = self._parsemsgs(
                            target,
                            sender,
                            suffix,
                            self._hooks['privcommand']
                        )

            if 'command' in self._hooks:
                if to_continue:
                    to_continue = self._parsemsgs(
                        target,
                        sender,
                        suffix,
                        self._hooks['command']
                    )
        if 'action' in self._hooks:
            if to_continue:
                to_continue = self._parseactions(
                    target,
                    sender,
                    line,
                    self._hooks['action']
                )
        if target.startswith('#'):
            # if allowed to continue
            if 'channel' in self._hooks:
                if to_continue:
                    to_continue = self._parsemsgs(
                        target,
                        sender,
                        line,
                        self._hooks['channel']
                    )
        else:
            # if allowed to continue
            if 'private' in self._hooks:
                if to_continue:
                    to_continue = self._parsemsgs(
                        target,
                        sender,
                        line,
                        self._hooks['private']
                    )
        if 'text' in self._hooks:
            if to_continue:
                to_continue = self._parsemsgs(
                    target,
                    sender,
                    line,
                    self._hooks['text']
                )

    def _filternotice(self, sender: str, target: str, line: str) -> None:
        if 'notice' in self._hooks:
            for func in self._hooks['notice']:
                groups = self._parsematch(func._matcher, line.strip())
                if groups is not None:
                    if isinstance(groups, dict):
                        func(self, **groups)
                    else:
                        func(self, *groups)
                    if self.config['break_on_match']:
                        break

    def _parsemsgs(self, target: str, sender: str, line: str, funcs: List[Callable]) -> bool:
        for func in funcs:
            if isinstance(line, basestring):
                line = line.strip()
            groups = self._parsematch(func._matcher, line.strip())
            if groups is not None:
                if isinstance(groups, dict):
                    func(self, target, sender, **groups)
                else:
                    func(self, target, sender, *groups)
                if self.config['break_on_match']:
                    return False
        return True

    def _parseactions(self, target: str, sender: str, line: str, funcs: List[Callable]) -> bool:
        for func in funcs:
            action = re.compile("ACTION (.*)").search(line.strip())
            if action:
                line = action.group(1)
                groups = self._parsematch(func._matcher, line.strip())
                if groups is not None:
                    if isinstance(groups, dict):
                        func(self, target, sender, **groups)
                    else:
                        func(self, target, sender, *groups)
                    if self.config['break_on_match']:
                        return False
        return True

    def _filtercode(self, code: int, line: str) -> None:
        if 'code' in self._hooks:
            for func in self._hooks['code']:
                if int(code) == func._code:
                    groups = self._parsematch(func._matcher, line.strip())
                    if groups is not None:
                        if isinstance(groups, dict):
                            func(self, **groups)
                        else:
                            func(self, *groups)
                        if self.config['break_on_match']:
                            break

    def _filterraw(self, line: str) -> None:
        if 'raw' in self._hooks:
            for func in self._hooks['raw']:
                groups = self._parsematch(func._matcher, line.strip())
                if groups is not None:
                    if isinstance(groups, dict):
                        func(self, **groups)
                    else:
                        func(self, *groups)
                    if self.config['break_on_match']:
                        break

    def _parsematch(self, matcher: str, line: str) -> Union[Dict, Tuple]:
        matcher = re.sub(':(\w*):', self._match_replace, matcher)
        match = re.compile(matcher).search(line)
        if match:
            group_dict = match.groupdict()
            groups = match.groups()
            if group_dict and (len(groups) > len(group_dict)):
                # match.groups() also returns named parameters
                raise Exception(
                    "You cannot use both named and unnamed parameters"
                )
            elif group_dict:
                return group_dict
            else:
                return groups
        return None

    def _match_replace(self, match) -> Any:
        if match.group(1) in self.config['replace']:
            return eval(self.config['replace'][match.group(1)])
        else:
            return ''

    def _alt_nick(self) -> None:
        self.config['nick'] += '_'
        self.nick(self.config['nick'])

    def _error(self, line: str) -> None:
        if not self._quitting:
            self.ERROR += 1
            raise Exception(str(line))
        else:
            self._quitting = False

    def _ping(self, line: str -> None):
        self._cmd("PONG :%s" % line)
        if 'ping' in self._hooks:
            for func in self._hooks['ping']:
                func(line)

    def _pong(self, line: str) -> None:
        if 'pong' in self._hooks:
            for func in self._hooks['pong']:
                func(line)

    def _compile_isupport(self, args: str) -> None:
        isupport = {}
        for arg in args.split():
            if arg[0] == ':':
                break
            x = arg.split('=')
            if len(x) == 1:
                x.append(True)
            isupport[x[0]] = x[1]
        if 'PREFIX' in isupport:
            if 'PREFIX' not in self.isupport:
                self.isupport['PREFIX'] = []
            match = re.match('\((\w+)\)(\S+)', isupport['PREFIX'])
            self.isupport['PREFIX'].extend(zip(match.group(1), match.group(2)))

    def _compile_ulist(self, channel: str, args: str) -> None:
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

    def _ulist_modes(self, action: str, channel: str, modes: str, args: str) -> None:
        self._manage_ulist(channel, action, args, modes)

    def _manage_ulist(self, user: str, action: str, args: str, modes: Optional[str]=None) -> None:
        if action == 'MODE':
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
        else:
            u = user.split('!')[0]
            if ':' in args:
                args = args.split(':')[0]
            args = args.strip()
            if action == 'JOIN':
                self.ulist.setdefault(u, {})
                self.ulist[u].update({args: ''})
                if 'join' in self._hooks:
                    for func in self._hooks['join']:
                        func(user, args)
            elif action == 'NICK':
                if u in self.ulist:
                    self.ulist[args] = self.ulist[u]
                    del self.ulist[u]
                if self.config['nick'] == u:
                    self.config['nick'] = args
                if 'nick' in self._hooks:
                    for func in self._hooks['nick']:
                        func(user, args)
            elif action == 'PART':
                if u == self.config['nick']:
                    for u in [x for x in self.ulist.iterkeys()]:
                        del self.ulist[u][args]
                        if not len(self.ulist[u]):
                            del self.ulist[u]
                else:
                    del self.ulist[u][args]
                    if not len(self.ulist[u]):
                        del self.ulist[u]
                if 'part' in self._hooks:
                    for func in self._hooks['part']:
                        func(user, args)
            elif action == 'QUIT':
                del self.ulist[u]
                if 'quit' in self._hooks:
                    for func in self._hooks['quit']:
                        func(user)

    def _init_ping(self, message: str) -> None:
        self.ping("_init_")

    def _init(self) -> None:
        if self.config['password']:
            self._cmd(
                "PRIVMSG NickServ :identify %s" %
                self.config['password']
            )

        self.ERROR = 0

        # Initialize (join rooms and start threads) if the bot is not
        # auto-identifying, or has just identified.
        if self.config['channels']:
            self.join(*self.config['channels'])
        # TODO: This doesn't ensure that threads run at the right time, e.g.
        # after the bot has joined every channel it needs to.
        self._runthreads()
        if 'connect' in self._hooks:
            for func in self._hooks['connect']:
                func(self)

    def _runthreads(self) -> True:
        if 'thread' in self._hooks:
            for n, thread in enumerate(self._hooks['thread']):
                if thread.is_shutdown() or thread.is_alive():
                    self._hooks[n] = thread.copy()
                    self._hooks[n].start()
                else:
                    thread.start()
            else:
                return True

    def queue(self, func: Callable, *args, **kwargs) -> None:
        self.queued.append((func, args, kwargs))

    def _cmd(self, raw_line: str) -> None:
        if self.config['verbose']:
            print("(%s: %s) > %s" % (
                self.config['name'],
                self.config['host'],
                "".join([x if ord(x) < 128 else '?' for x in raw_line])
            ))
        try:
            self.socket.send(raw_line+"\r\n")
        except socket.timeout:
            print(">>>Socket timed out.")

    @hook.queue()
    def message(self, targets: Union[List[str], str], messages: Union[List[Tuple[str, int]], List[str], str]) -> None:
        if isinstance(targets, basestring):
            targets = [targes]
        if isinstance(messages, basestring):
            messages = [messages]
        for x in target:
            for y in messages:
                if isinstance(y, tuple) and len(y) == 2:
                    y, z = y
                else:
                    z = 1
                self._cmd("PRIVMSG %s :%s" % (x, str(y)))
                pause(z)

    @hook.queue()
    def notice(self, targets: Union[List[str], str], messages: Union[List[Tuple[str, int]], List[str], str]) -> None:
        if isinstance(targets, basestring):
            targets = [targes]
        if isinstance(messages, basestring):
            messages = [messages]
        for x in target:
            for y in messages:
                if isinstance(y, tuple) and len(y) == 2:
                    y, z = y
                else:
                    z = 1
                self._cmd("NOTICE %s :%s" % (x, str(y)))
                pause(z)

    @hook.queue()
    def me(self, targets: Union[List[str], str], messages: Union[List[Tuple[str, int]], List[str], str]) -> None:
        if isinstance(targets, basestring):
            targets = [targes]
        if isinstance(messages, basestring):
            messages = [messages]
        for x in target:
            for y in messages:
                if isinstance(y, tuple) and len(y) == 2:
                    y, z = y
                else:
                    z = 1
                self._cmd("PRIVMSG %s : ACTION %s" % (x, str(y)))
                pause(z)

    @hook.queue()
    def join(self, *channels: Tuple[str]) -> None:
        for x in channels:
            self._cmd("JOIN %s" % x)
            self._cmd("MODE %s" % x)

    @hook.queue()
    def part(self, *channels: Tuple[str]) -> None:
        for x in channels:
            self._cmd("PART %s" % x)

    @hook.queue()
    def nick(self, nick: Optional[str]=None) -> None:
        if nick is None:
            nick = self.config['name']
        self._cmd("NICK %s" % nick)

    @hook.queue()
    def ping(self, line: str="timeout") -> None:
        self._cmd("PING :%s" % str(line))

    @hook.queue()
    def quit(self, message: str="Connection Closed") -> None:
        self._cmd("QUIT :%s" % message)
        self._quitting = True
        self._close()

    @hook.queue()
    def pause(self, time: int=1) -> None:
        pause(time)

    def color(self, matcher) -> str:
        return re.sub(':(\d)(?:,(\d))?:', _color_replace, matcher)

    def _color_replace(self, match):
        if len(match.groups()) > 1:
            if int(match.group(1)) < 16 and int(match.group(2)) < 16:
                return '\x02%s,%s' % (match.group(1), match.group(2))

        if len(match.groups()) > 0:
            if int(match.group(1)) < 16:
                return '\x02%s' % match.group(1)

        return ''

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
            print("--- %s: %s ---" % (
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
            print("Error occurred (see stack trace). Waiting %d seconds to reconnect." %
                  (30*self.ERROR+30))
            pause(30*self.ERROR+30)
        elif self.config['reconnect']:
            # raw_input()
            if self.config['verbose']:
                print("Waiting 10 seconds to reconnect...")
            pause(8)

        if self.config['reconnect']:
            pause(2)
            if self.config['verbose']:
                print("Opening new connection...")
            self.connect()
        else:
            self.ERROR = 0

    def connect(self) -> None:
        '''
        Connects to the IRC server with the options defined in `config`
        '''
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
            f = open('%s - BotLog.txt' % self.config['name'], 'a')
            f.write("\r\n")
            f.write(now())
            f.write("\r\nConnection: %s\r\n" % self.config['host'])
            print_exc(None, f)
            f.write("\r\n")
            f.close()
            self.reconnect()
        finally:
            self._close()

    def _connect(self) -> None:
        """Sets socket connection and sends initial info to the server."""
        self.socket = socket.socket()
        self.socket.connect((self.config['host'], self.config['port']))
        self.socket.settimeout(1.0)
        if self.config['verbose']:
            print("(%s: %s) Connection successful" % (
                self.config['name'],
                self.config['host']
            ))
        self._cmd("CAP LS")
        self._cmd("NICK %s" % self.config['nick'])
        self._cmd("USER %s %s 0 :%s" % (
            self.config['ident'],
            self.config['host'],
            self.config['realname']
        ))
        self._cmd("CAP REQ :multi-prefix")
        self._cmd("CAP END")

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
            print("Closing connection and thread for %s:%s" %
                  (self.config['name'], self.config['host']))
        raise SystemExit()

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
                    self._inbuffer = self._inbuffer + self.socket.recv(2048)
                except socket.timeout:
                    pass
                # Some IRC daemons disregard the RFC and split lines by \n rather than \r\n.
                temp = self._inbuffer.split("\n")
                self._inbuffer = temp.pop()

                for line in temp:
                    # Strip \r from \r\n for RFC-compliant IRC servers.
                    line = line.rstrip('\r')
                    if self.config['verbose']:
                        print("(%s: %s) %s" % ()
                              self.config['name'],
                              self.config['host'],
                              line
                              )
                    self._running = True
                    self._run_listeners(line)
                if self.queue:
                    self._running = True
                    self._run_queue()
                self._running = False

    def _run_listeners(self, line: str) -> None:
        """
        Each listener's associated regular expression is matched against raw IRC
        input. If there is a match, the listener's associated function is called
        with all the regular expression's matched subgroups.
        """
        for regex, dict in [(x, y) for x, y in self.listeners.iteritems()]:
            temp = dict['temp'] is True
            callbacks = dict['funcs']
            match = regex.match(line)

            if not match:
                continue

            for callback in callbacks:
                callback(*match.groups())
            if temp:
                del self.listeners[regex]

        if 'once' in self._hooks:
            for n, func in [(x, y) for x, y in enumerate(self._hooks['once'])]:
                groups = self._parsematch(func._matcher, line.strip())
                if groups is not None:
                    if isinstance(groups, dict):
                        func(**groups)
                    else:
                        func(*groups)
                    del self._hooks['once'][n]

    def _run_queue(self) -> None:
        while len(self.queued) > 0:
            func, args, kwargs = self.queued.pop(0)
            func(*args, **kwargs)


class Bot(Base):
    """
    This class is a high-level wrapper for the base bot to allow for dynamic reloading of hooks.

    Config Vars

    host            (string)    : address to connect to
    port            (integer)   : port to connect with
    name            (string)    : bot's original name
    names           (list)      : a list of names that the bot will respond to for a command
    ident           (string)    : the 'user' part of 'nick!user@host * name'
    nick            (string)    : the 'nick' part of 'nick!user@host * name'; bot's temporary name
    realname        (string)    : the 'name' part of 'nick!user@host * name'
    channels        (list)      : a list of channels to autojoin on successful connect
    command         (string)    : a (sequence of) character(s) the bot will respond to for a command
    password        (string)    : passed to nickserv for authentication
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

        super(Bot, self).__init__(host, **kwargs)
        self.config.setdefault('hookscripts', [])
        self.config.setdefault('reload_override', False)
        self.config.setdefault('ref', None)

        self.load_hooks()

        if not self.config['reload_override']:
            self.config.setdefault(
                'reload_regex', '^:(\S+) PRIVMSG (\S+) :\%sreload$' %
                self.config['command']
            )
            self.config.setdefault('reload_func', self.load_hooks)
            self._add_raw_listener(
                r'%s' %
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

        old_funcs = [(k, v) for k, v in self.__dict__.iteritems()
                     if hasattr(v, '_type')]

        if len(old_funcs) and self.config['verbose']:
            print("\n(%s: %s) Unloading old hooks..." % (
                self.config['name'],
                self.config['host']
            ))
            print("----------------------")

        for k, v in old_funcs:
            delattr(self, k)
            if self.config['verbose']:
                print("(%s: %s)   -'%s' successfully removed." % (
                    self.config['name'],
                    self.config['host'],
                    k
                ))

        if self.config['verbose']:
            print("\n(%s: %s) Loading hooks..." % (
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
                    print("\n(%s: %s) '%s' successfully imported." % (
                        self.config['name'],
                        self.config['host'],
                        script
                    ))
            except:
                if self.config['verbose']:
                    print("\n(%s: %s) Error: >>>%s" % (
                        self.config['name'],
                        self.config['host'],
                        str(sys.exc_info()[1])
                    ))
                    print_tb(sys.exc_info()[2])
                    print("(%s: %s) >>>Unable to import '%s'. Skipping..." % (
                        self.config['name'],
                        self.config['host'],
                        script
                    ))
            else:
                for k, v in sys.modules[script].__dict__.iteritems():
                    if hasattr(v, '_type'):
                        setattr(self, k, v)
                        if self.config['verbose']:
                            print("(%s: %s)   -'%s' successfully added." % (
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

    def network(self, host:str, ref: Optional[T_Base]=None, **kwargs) -> None:
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
            if (ref is None)
                ref = bot.__class__
            return ref(host, ref=self, **kwargs)

    def get(self, host: str) -> Optional[T_Base]:
        return self._bots.get(host, None)

    def list(self, by: Optional[str]=None) -> List[Any]:
        """
        Conveneince method for accessing the bot dictionary via list.
        """
        if by == 'hosts':
            return [k for k in self._bots.iterkeys()]
        elif by == 'bots':
            return [v for v in self._bots.itervalues()]
        else:
            return [(k, v) for k, v in self._bots.iteritems()]

    def connect(self, contain: bool=False) -> None:
        """
        Method called to start the bot instance threads.
        Initialzes optional thread manager thread if specified.
        If True is passed as an argument, the class takes control
                of the main thread by sending it directly to the console
        """
        for bot in self.list('bots'):
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
        for x in self.list('bots'):
            x['instance'].load_hooks()
            x['instance']._runthreads()

    def thread_check(self):
        """
        Method to check if bot instance threads have been killed.
        Restarts thread with fresh instance if so.
        """
        for host, bot in self.list():
            thread = bot['thread']
            if not thread.is_alive():
                if (bot['instance'].config['verbose'])
                    print(
                        'Bot thread for %s died (see stack trace). Rebooting...' % host)
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


def console(bot: Optional[Union[T_Base, T_Group]]=None, **vars) -> None:
    """
    Function for direct interaction via terminal.
    Useful for testing, not advised for production code

    Params:
    -bot = Instance of the bot/botgroup you wish to control via console.
    -vars = kwarg dict of global variables defined in the __main__ module give the console access to.
    """

    if vars:
        # Define global access for variables passed to the function
        for x, y in vars.iteritems():
            globals()[x] = y

    main = __import__('__main__')
    for x, y in main.__dict__.iteritems():
        if x != 'bot' and (isinstance(y, BotGroup) or isinstance(y, Base)):
            # Creates local variable for the relevant variables from the __main__ module
            locals()[x] = y
            if x.lower() not in main.__dict__ or\
                    not (
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
            print('>>>Exception occured: %s' % sys.exc_info()[1])
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