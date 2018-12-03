# About
This is a personal two-way hack.chat-to-Telegram bridge that forwards any messages sent to it.
It is designed to be used by a single user on the Telegram side and thus might not work when used in Telegram group chats.

# Installation

0. Install all necessary dependencies
1. Clone the repository
2. Create a bot on Telegram by messaging @BotFather and following the instructions.
3. Copy `config.py.sample` to `config.py`
4. Change the hack.chat username, password, channel, and the Telegram API token in `config.py`
5. Change the Telegram chat ID by following the instructions in `config.py`

# Dependencies

0. Python package `websocket-client`

# Usage

To start the bridge, run `python control.py`.
The reconnect feature is based on `SIGALRT` and thus might not work on Windows.

The bridge will automatically log all events to the logfile specified in `config.py`.
It also supports the following console commands:
- `quit`: Gracefully shuts down both bots.
- `kill`: Disconnects the hack.chat WebSocket connection. You can use this to test the reconnect feature.
