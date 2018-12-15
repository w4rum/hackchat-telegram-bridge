#!/bin/python

import datetime
import sys
import time
import threading
import traceback
import signal
import logging
import html

# Custom scripts
import hackchatcustom as hackchat
import telegrambot

# Config
import config

# Constants
CONFIG_FILE     = "config.py"

# Global variables holding both bots
hcBot           = None
tgBot           = None

### General
def log(s, suppress_console=True):
    """Writes a message to the channel's logfile.
    Will also output to the console if suppress_console is False."""
    # Write to logfile
    with open(config.LOG_FILENAME, "a") as f:
        f.write("%s %s\n" % (datetime.datetime.now().isoformat(), s))
    # Send via TG-Bot
    if not suppress_console:
        print(s)

def mdescape(s):
    """Hacky escapes for Telegrams Markdown parser.
    Should really replace this with HTML."""
    special = '*[`_'
    for x in special:
        s = s.replace(x, "\\" + x)
    return s

def htmlescape(s):
    return html.escape(s)

### HV-Bot
def getUser(update):
    """Convenience function that extracts a nick and tripcode (if any) from
    an update object and returns the nickname in the following format:
        If there is not tripcode: nick
        If there is a tripcode: nick#tripcode"""
    nick = update["nick"]
    trip = 'null'
    if "trip" in update:
        trip = update["trip"]

    if trip == 'null':
        return nick
    else:
        return "%s#%s" % (nick, trip)

def onMessage(chat, update):
    """Callback function handling users submitting messages to the channel."""
    message = update["text"]
    nick = update["nick"]
    trip = 'null'
    if "trip" in update:
        trip = update["trip"]
    sender = getUser(update)

    log("[%s] %s" % (sender, message))
    if nick != config.USER:
        if trip == 'null':
            toTG("[<b>%s</b>] %s" % (htmlescape(nick), htmlescape(message)))
        else:
            toTG("[<b>%s</b>#%s] %s" % (htmlescape(nick), trip, htmlescape(message)))

def onJoin(chat, update):
    """Callback function handling users joining the channel."""
    user = getUser(update)
    log("# %s joined" % user)
    toTG("# %s joined" % htmlescape(user))

def onLeave(chat, update):
    """Callback function handling users leaving the channel."""
    user = getUser(update)
    log("# %s left" % user)
    toTG("# %s left" % htmlescape(user))

def onEmote(chat, update):
    """Callback function handling users sending emotes to the channel."""
    text = update["text"]
    log("* %s" % text)
    toTG("* %s" % htmlescape(text))

def onInvite(chat, update):
    """Callback function handling users sending invite to the bot."""
    user = update["from"]
    newChannel = update["invite"]
    log(">>> %s invited you to hack.chat/?%s" % (user, newChannel))
    toTG(">>> %s invited you to hack.chat/?%s" % (htmlescape(user), htmlescape(newChannel)))

def startHCBot():
    """Starts the HC bot."""
    global hcBot
    bot = hackchat.HackChat(config.USER_AND_PASS, config.CHANNEL)
    bot.on_message  += [onMessage]
    bot.on_join     += [onJoin]
    bot.on_leave    += [onLeave]
    bot.on_emote    += [onEmote]
    bot.on_invite   += [onInvite]
    hcBot = bot
    bot.run()

def botCrashed(signum, frame):
    """Recovery routine that restarts the HC bot upon crash.
    This is run automatically when a SIGALRT is received
    (tested on Linux only) and thus relies on the HC bot
    catching any relevant exception and sending a SIGALRT."""
    hcBot.stop()

    log("=!= Bot crashed / lost connection. Retrying in %i seconds..."\
            % config.RECONNECT_DELAY, suppress_console=False)
    toTG("=!= Bot crashed / lost connection. Retrying in %i seconds..."\
            % config.RECONNECT_DELAY)
    time.sleep(config.RECONNECT_DELAY)
    log("Reconnecting...", suppress_console=False)
    toTG("Reconnecting...")
    startHCBot()
    log("Reconnected!", suppress_console=False)
    toTG("Reconnected!")

def kill():
    """Debug command to test reconnect functionality"""
    hcBot.ws.close()

### TG-Bot Config
def onTGMessage(text):
    """Handles receiving messages from the Telegram bot.
    Currently, they are simple forwarded to the HC bot
    which will then send them"""
    hcBot.send_message(text)

def toTG(s):
    """Handles sending messages to the Telegram bot.
    Currently, the TG bot will simply send
    the message with Markdown parsing enabled."""
    tgBot.send(s)

def startTGBot():
    """Starts the Telegram bot and sets the global
    tgBot variable."""
    global tgBot
    tgBot = telegrambot.TGBot()
    tgBot.texthandlers += [onTGMessage]
    tgBot.addCommand("active", cmdActive)
    tgBot.addCommand("online", cmdOnline)
    tgBot.run()

def cmdActive(bot, update):
    """TG command: /active
    Checks wether the HC bot has been stopped.
    This might not work correctly if the HC bot crashed."""
    if not hcBot.stopped:
        tgBot.send("+++ ACTIVE")
    else:
        tgBot.send("--- _not_ active")

def cmdOnline(bot, update):
    """TG command: /online
    Returns the list of users that are in the HC channel.
    Users are listed without their tripcode."""
    users = list(hcBot.online_users)
    users.sort()
    tgBot.send("Users online:\n%s" %
                htmlescape(", ".join(users)))


### Common
def quit():
    """Gracefully shuts down both bots"""
    global should_quit
    hcBot.stop()
    tgBot.stop()
    should_quit = True

### Main
if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG,
    #                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    COMMANDS_CLI    = {
        "kill": kill,
        "quit": quit
        #"online" : cmdOnline
    }

    should_quit = False

    # Interpret SIGALRM as bot crash
    signal.signal(signal.SIGALRM, botCrashed)

    try:
        startTGBot()
        startHCBot()
        while not should_quit:
            cmd = input("> ")
            if not cmd in COMMANDS_CLI:
                print("Unknown command!")
            else:
                COMMANDS_CLI[cmd]()

    except (KeyboardInterrupt, EOFError) as e:
        print("Interrupt received. Shutting down...")
        quit()

    except:
        print("====================")
        print("Main thread crashed!")
        print("====================")
        print()
        traceback.print_exc()


