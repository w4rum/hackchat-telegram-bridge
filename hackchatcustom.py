# This module is based on https://github.com/gkbrk/hackchat (MIT License)

import json
import threading
import time
import websocket
import sys
import traceback
import signal

class HackChat:
    """A library to connect to https://hack.chat.
    <on_message> is <list> of callback functions to receive data from
    https://hack.chat. Add your callback functions to this attribute.
    e.g., on_message += [my_callback]
    The callback function should have 3 parameters, the first for the
    <HackChat> object, the second for the message someone sent and the
    third for the nickname of the sender of the message.
    """

    def __init__(self, nick, channel="programming"):
        """Connects to a channel on https://hack.chat.
        Keyword arguments:
        nick -- <str>; the nickname to use upon joining the channel
        channel -- <str>; the channel to connect to on https://hack.chat
        """
        self.nick = nick
        self.channel = channel
        self.online_users = []
        self.on_message = []
        self.on_join = []
        self.on_leave = []

        self.stopped = False

        self._stop = threading.Event()
        # Receiver thread
        self._recv_thread = threading.Thread(target = self._receive)
        self._recv_thread.daemon = True

        # Keepalive thread
        self._ka_thread = threading.Thread(target = self._ping)
        self._ka_thread.daemon = True

    def send_message(self, msg):
        """Sends a message on the channel."""
        self._send_packet({"cmd": "chat", "text": msg})

    def _send_packet(self, packet):
        """Sends <packet> (<dict>) to https://hack.chat."""
        encoded = json.dumps(packet)
        self.ws.send(encoded)

    def run(self):
        """Starts the bot asynchronously."""
        if self.stopped:
            raise ValueError("Can't run a stopped bot.")

        self.ws = websocket.create_connection("wss://hack.chat/chat-ws")
        self._send_packet({"cmd": "join", "channel": self.channel, "nick": self.nick})
        self._recv_thread.start()
        self._ka_thread.start()

    def _receive(self):
        """Waits for data and then sends it to the callback functions.
        Will send a SIGALRM to its own process upon connection loss or crash."""
        try:
            while not self._stop.wait(timeout=0):
                self.ws.settimeout(1)
                try:
                    result_raw = self.ws.recv()
                    #print(result_raw)
                    result = json.loads(result_raw)
                    #print(result)
                    self._handleCommand(result)
                except websocket._exceptions.WebSocketTimeoutException:
                    # Ignore timeouts
                    pass
        except (json.decoder.JSONDecodeError,
                websocket._exceptions.WebSocketConnectionClosedException) as e:
            print("Connection lost!")
            # Signal main thread that bot crashed
            signal.alarm(1)

        except:
            print("Receiver thread crashed!")
            traceback.print_exc()
            # Signal main thread that bot crashed
            signal.alarm(1)

        print("Receiver thread shut down.")

    def _handleCommand(self, result):
        """Will demultiplex incoming packets to their respective callback
        functions."""
        if result["cmd"] == "chat" and not result["nick"] == self.nick:
            for handler in list(self.on_message):
                handler(self, result)
        elif result["cmd"] == "onlineAdd":
            self.online_users.append(result["nick"])
            for handler in list(self.on_join):
                handler(self, result)
        elif result["cmd"] == "onlineRemove":
            self.online_users.remove(result["nick"])
            for handler in list(self.on_leave):
                handler(self, result)
        elif result["cmd"] == "onlineSet":
            for nick in result["nicks"]:
                self.online_users.append(nick)

    def stop(self):
        """Gracefully stops all bot threads and closes WebSocket connection."""
        if self.stopped:
            return

        self._stop.set()
        self._recv_thread.join()
        self._ka_thread.join()
        self.ws.close()
        self.stopped = True

    def _ping(self):
        """Retains the websocket connection."""
        while self.ws.connected \
                and not self._stop.wait(timeout=60):
            self._send_packet({"cmd": "ping"})
            #print("PING")

        print("Keepalive thread shut down.")

