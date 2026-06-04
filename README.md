# 🎵 mp3ToLyrics Bot

A Telegram bot that receives an audio file and returns the song lyrics.

## How it works

1. Send the bot an audio file (MP3, FLAC, M4A, WAV)
2. Bot reads the file tags (artist, title)
3. Searches for lyrics on Genius
4. Returns the lyrics directly in chat

## Stack

- Python
- python-telegram-bot
- lyricsgenius
- mutagen

## Deploy on Railway

1. Fork the repo
2. Create a project on railway.app
3. Add environment variables:
   - `BOT_TOKEN` — token from @BotFather
   - `GENIUS_TOKEN` — token from genius.com/api-clients

## Local run

```bash
pip install -r requirements.txt
python bot.py
```
