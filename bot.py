import os
from mutagen import File as MutagenFile
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
import lyricsgenius

BOT_TOKEN = os.environ['BOT_TOKEN']
GENIUS_TOKEN = os.environ['GENIUS_TOKEN']
DOWNLOAD_DIR = '/tmp/music_bot_downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

genius = lyricsgenius.Genius(GENIUS_TOKEN)

async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = update.message.audio or update.message.document
    if not file:
        return

    file_name = file.file_name or 'audio'
    msg = await update.message.reply_text('⏳ Downloading file...')

    tg_file = await context.bot.get_file(file.file_id)
    input_path = os.path.join(DOWNLOAD_DIR, file_name)
    await tg_file.download_to_drive(input_path)

    await msg.edit_text('🔍 Reading tags...')
    audio = MutagenFile(input_path, easy=True)
    artist = (audio.get('artist') or audio.get('albumartist') or [''])[0]
    title = (audio.get('title') or [''])[0]
    os.remove(input_path)

    if not artist or not title:
        await msg.edit_text('❌ No tags found in file')
        return

    await msg.edit_text(f'🎵 Found: {artist} — {title}\n⏳ Searching lyrics...')

    try:
        song = genius.search_song(title, artist)
        if song:
            await msg.edit_text(f'🎵 {artist} — {title}\n\n{song.lyrics[:4000]}')
        else:
            await msg.edit_text('❌ Lyrics not found')
    except Exception as e:
        await msg.edit_text(f'❌ Error: {e}')

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.AUDIO | filters.Document.AUDIO, handle_audio))

print('Bot started...')
app.run_polling()
