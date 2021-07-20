# youtube-telegram-downloader

This is a selfhosted [Telegram](https://telegram.org/) bot which is supposed to download any Videos or Streams compatible with [youtube-dl](https://github.com/ytdl-org/youtube-dl).

# Getting Started

## Create your Telegram bot

Setting up your own Telegram bot is straight forward according to the [Telegram bots documentation](https://core.telegram.org/bots).

Install the [Telegram Messenger](https://telegram.org/) on a system of your choice and search for your bot as a contact to create a conversation.

## Run the Telegram bot

Install [ffmpeg](https://ffmpeg.org/) on your system and make sure it is available in your [system PATH](https://en.wikipedia.org/wiki/PATH_(variable)).

Setup a python3 environment (e.g. with [virtualenv](https://virtualenv.pypa.io/en/stable/)) and source it.:

```
virtualenv -p python3 ~/.venv/youtube-telegram-downloader &&\
source ~/.venv/youtube-telegram-downloader/bin/activate &&\

# Clone the repository and install all dependencies:
git clone https://github.com/hacker-h/youtube-telegram-downloader.git &&\
pip3 install -r ./youtube-telegram-downloader/requirements.txt &&\

# Run the bot:
python3 ./bot.py
```

## Features

* [x] Interact with the user
* [x] Automatically download videos from URL provided via message
    - [x] Code cleanup
    - [ ] Audio Quality selectable
    - [ ] Audio Format selectable
    - [ ] Audio Quality Default Value selectable
    - [ ] Audio Format Default Value selectable
    - [ ] Handle Video Playlists
    - [ ] Handle multiple URLs in one message
    - [ ] Use multiple threads for more performance
