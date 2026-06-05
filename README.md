# 🎵 mp3ToLyrics Bot

![logo](assets/cassete.png)

A Telegram bot that finds lyrics for your music. Send a file, type a song name, or record a voice message.

## How it works

**Audio file** — send MP3, FLAC, M4A or WAV → bot reads tags → returns lyrics

**Text** — type `Artist Title` (e.g. `Oasis Wonderwall`) → returns lyrics

**Voice** — record a voice message saying the artist and title → bot transcribes via Whisper → confirms → returns lyrics

## Stack

- Python
- python-telegram-bot
- lyricsgenius
- mutagen
- groq (Whisper voice transcription)

## Deploy on Railway

1. Fork the repo
2. Create a project on railway.app
3. Add environment variables:
   - `BOT_TOKEN` — token from @BotFather
   - `GENIUS_TOKEN` — token from genius.com/api-clients
   - `GROQ_TOKEN` — token from console.groq.com

## Local run

```bash
pip install -r requirements.txt
python bot.py
```
