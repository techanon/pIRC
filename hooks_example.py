from pIRC import hooks

"""
The hooks module is used for wrapping functions to prep the for use 
by the 'Bot' or 'Base' classes.

There are 5 hook types currently avaliable.

hooks.raw(regex)
    This hook matches the given regex to each raw line recieved from the server.
    1 - The executing bot's instance reference as self
    2 - The capture field values returned from the regex match.
        + If the regex used named capture fields, use **kwargs.
        + Otherwise use *args
    
hooks.code(int, regex)
    This hook matches the given regex to each line that matches the three 
    digit IRC code number given.
    FUNCTION ARGUMENTS:
    1 - The executing bot's instance reference as self
    2 - The remaining *args or **kwargs returned from the regex match.
        + If the regex used named capture fields, use **kwargs.
        + Otherwise use *args
    
hooks.msg(regex)
    This hook matches the given regex to each line that is a PRIVMSG 
    (messages from channels and users)
    FUNCTION ARGUMENTS:
    1 - The executing bot's instance reference as self
    2 - The location from where the message came from (channels start with #)
    3 - The name of the user who send the message (form of nick!user@host.name)
    4 - The remaining *args or **kwargs returned from the regex match.
        + If the regex used named capture fields, use **kwargs.
        + Otherwise use *args
    
hooks.command(regex)
    Similar to .msg(), this hook matches the given regex to each PRIVMSG,
    but requires the message to be prefixed with either the 'command'
    defined in the bot's configuration, or one of the 'names' listed in
    the bot's configuration.
    If no regex is given, it matches just the 'command' or 'names' prefix
    and returns the rest of the line as argument 4.
    FUNCTION ARGUMENTS:
    1 - The executing bot's instance reference as self
    2 - The location from where the message came from (channels start with #)
    3 - The name of the user who send the message (form of nick!user@host.name)
    4 - The remaining *args or **kwargs returned from the regex match.
        + If the regex used named capture fields, use **kwargs.
        + Otherwise use *args
    
hooks.interval(int)
    This hook executes the wrapped function every given number of milliseconds
    (1000 milliseconds is 1 second)
    FUNCTION ARGUMENTS:
    1 - The executing bot's instance reference as self
"""


@hooks.command('^repeat (.*)$')
def repeat(self, target, sender, *args):
    """
    This function will execute when a recieved PRIVMSG contains 
    the command character followed by the matched regex.
    
    EX: self.config['command'] = '!'
        <<< :nick!user@host.name PRIVMSG #chan-chan :!repeat What a glorious day
        >>> PRIVMSG #chan-chan :nick!user@host.name says What a glorious day
    """
    self.message(target, "%s says %s"%(sender,args[1]))

@hooks.msg('^how are you doing today Botty\?')
def greeting_reply(self, target, sender, *args):
    """
    This function will execute when a recieved PRIVMSG contains 
    the matched regex.
    
    EX: <<< :nick!user@host.name PRIVMSG #chan-chan :how are you doing today Botty?
        >>> PRIVMSG #chan-chan :I'm doing just fine, nick!user@host.name.
    """
    self.message(target, "I'm doing just fine, %s."%sender)
    
@hooks.interval(15000)
def promos(self):
    """
    This function will execute every 15 seconds
    """
    chans = ['#chan1','#chan2','#chan3']
    for chan in chans:
        self.message(chan,"This is a promo message, get used to it.")
    
@hooks.raw('^:\S+ PING \S+ :YOU LOSE$')
def game_over(self, *args):
    """
    This function will execute when a recieved line is a PING message 
    and contains the message 'YOU LOSE'.
    """
    self.quit("I lost the game...")
    self.pause(5)
    self.reconnect()
    
    
    