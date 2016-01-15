# pIRC

Slim, concise and dynamic python-based IRC bot library.
This library is currently built against python 2.7. 

## Installation

```bash
$ pip install pIRC
```

*The use of hooks is described in more detail in the hooks_example.py file*

## Example Usages
There are 3 pairs of ways to use this library.

The first pair ways is to use the `Base` class for a single contained bot.

You can instantiate it (which doesn't have much functionality on it's own):
```python
import pIRC

if __name__ == '__main__':
    bot = pIRC.Base('irc.website.com', 
                        nick            = 'DaBot',
                        password        = 'thisisnotapassword',
                        names           = ['Hey Bot','Yo Bot'],
                        channels        = ['#Chan-chan'],
                        realname        = 'pIRC Bot',
                        ident           = 'BOT',
                        command         = '$',
                        replace         = dict(
                            me = 'self.config["nick"]'
                            ),
                        verbose         = True,
                        break_on_match  = False,
                        )
    bot.connect()
```
Or inherit it and add custom hooks inside the class (more useful):
```python
import pIRC

class CustomBase(pIRC.Base):

    @pIRC.hooks.msg('^Greetings$')
    def greet(self, target, sender, *args):
        self.message(target, "And a hello to you too, %s"%sender)

if __name__ == '__main__':
    bot = CustomBase('irc.website.com', 
                        nick            = 'DaBot',
                        password        = 'thisisnotapassword',
                        names           = ['Hey Bot','Yo Bot'],
                        channels        = ['#Chan-chan'],
                        realname        = 'pIRC Bot',
                        ident           = 'BOT',
                        command         = '$',
                        replace         = dict(
                            me = 'self.config["nick"]'
                            ),
                        verbose         = True,
                        break_on_match  = False,
                        )
    bot.connect()
```
The next pair is similar to the last, but offers more freedom and stability with controlling the bot by using the `Bot` class with a couple extra config options.

As before, you can instatiate it:
```python
import pIRC

if __name__ == '__main__':
    bot = pIRC.Bot('irc.website.com', 
                        nick            = 'DaBot',
                        password        = 'thisisnotapassword',
                        names           = ['Hey Bot','Yo Bot'],
                        channels        = ['#Chan-chan'],
                        realname        = 'pIRC Bot',
                        ident           = 'BOT',
                        command         = '$',
                        replace         = dict(
                            me = 'self.config["nick"]'
                            ),
                        verbose         = True,
                        break_on_match  = False,
                        hookscripts     = ['custom_hooks'],
                        reload_override = True
                        )
    bot.connect()
```
Or inherit it and add hooks into the class itself:
```python
import pIRC

class CustomBot(pIRC.Bot):

    @pIRC.hooks.msg('^Greetings$')
    def greet(self, target, sender, *args):
        self.message(target, "And a hello to you too, %s"%sender)

if __name__ == '__main__':
    bot = CustomBot('irc.website.com', 
                        nick            = 'DaBot',
                        password        = 'thisisnotapassword',
                        names           = ['Hey Bot','Yo Bot'],
                        channels        = ['#Chan-chan'],
                        realname        = 'pIRC Bot',
                        ident           = 'BOT',
                        command         = '$',
                        replace         = dict(
                            me = 'self.config["nick"]'
                            ),
                        verbose         = True,
                        break_on_match  = False,
                        hookscripts     = ['custom_hooks'],
                        reload_override = True
                        )
    bot.connect()
```
Notice the arguement `hookscripts`. 
This option is a list of extensionless python filenames that contain functions wrapped in a `@pIRC.hooks` descriptor. 
It allows the class to refence and use functions outside of the main file without having to make an interiting class.
Descriptions of the other configuration variables are avaliable in the Bot class' DocString in the source.

The thrid pair of ways give more functionality by allowing management of a single bot connecting to multiple networks by using the `BotGroup` class.
It uses threading for each bot used to recover from crashes and improve bot stability. (or something nerdy like that)

This way is setup a bit differently than the previous 2 pairs. Since it carries multiple network connections, it needs to have each network defined separately.
This is done with the `.network()` method. This method takes the same arguments as does instantiating a `Bot` class instance does

You can instantiate it with the default settings:
```python
import pIRC

if __name__ == '__main__':
    botgroup = pIRC.BotGroup()
    
    botgroup.network('irc.website.com', 
                        nick            = 'DaBot',
                        password        = 'thisisnotapassword',
                        names           = ['Hey Bot','Yo Bot'],
                        channels        = ['#Chan-chan'],
                        realname        = 'pIRC Bot',
                        ident           = 'BOT',
                        command         = '$',
                        replace         = dict(
                            me = 'self.config["nick"]'
                        ),
                        verbose         = True,
                        break_on_match  = False,
                        hookscripts     = ['custom_hooks'],
                        reload_override = True
                    )
    
    botgroup.connect(True)
```
Or you can instantiate it with an arguement that is a custom class that inherits from the `Bot` or `Base` classes to use as the default.
You also have the option to specify a specific custom class per defined network via adding the `ref` keyword arguement to the `.network()` mwthod.
```python
import pIRC

class CustomBot(pIRC.Bot):

    @pIRC.hooks.msg('^Howdy$')
    def greet(self, target, sender, *args):
        self.message(target, "And a howdy to you too, %s"%sender)

if __name__ == '__main__':
    botgroup = pIRC.BotGroup(CustomBase, 60)
    
    botgroup.network('irc.website.com', ref = CustomBot,
                        nick            = 'DaBot',
                        password        = 'thisisnotapassword',
                        names           = ['Hey Bot','Yo Bot'],
                        channels        = ['#Chan-chan'],
                        realname        = 'pIRC Bot',
                        ident           = 'BOT',
                        command         = '$',
                        replace         = dict(
                            me = 'self.config["nick"]'
                        ),
                        verbose         = True,
                        break_on_match  = False,
                        hookscripts     = ['custom_hooks'],
                        reload_override = True
                    )
                    
    botgroup.network('irc.secondwebsite.com', 
                        nick            = 'DaBot',
                        password        = 'thisisnotapassword',
                        names           = ['Hey Bot','Yo Bot'],
                        channels        = ['#Chan-chan'],
                        realname        = 'pIRC Bot',
                        ident           = 'BOT',
                        command         = '$',
                        replace         = dict(
                            me = 'self.config["nick"]'
                        ),
                        verbose         = True,
                        break_on_match  = False,
                        hookscripts     = ['custom_hooks'],
                        reload_override = True
                    )
    
    botgroup.connect(True)
```
The second argument is the interval in seconds which the class uses to check the state of each bot thread and restarts them if they have died.
The argument on the `.connect()` method is for whether or not to contain the main thread in an input loop or not.
If the argement is False (default value) the method returns for further processing if so desired.

Unless there is a function that you want to override, there isn't a need to inherit `BotGroup` into a custom class.


## TODO
* Better and more descriptive documentation
* Add more default IRC controls
* Fork and build against python 3.3
