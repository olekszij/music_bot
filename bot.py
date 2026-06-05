import os
from mutagen import File as MutagenFile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import lyricsgenius
from groq import Groq

BOT_TOKEN = os.environ['BOT_TOKEN']
GENIUS_TOKEN = os.environ['GENIUS_TOKEN']
GROQ_TOKEN = os.environ['GROQ_TOKEN']
DOWNLOAD_DIR = '/tmp/music_bot_downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

genius = lyricsgenius.Genius(GENIUS_TOKEN)
groq_client = Groq(api_key=GROQ_TOKEN)

async def search_lyrics(msg, artist, title):
    await msg.edit_text(f'🎵 Found: {artist} — {title}\n⏳ Searching lyrics...')
    try:
        song = genius.search_song(title, artist)
        if song:
            await msg.edit_text(f'🎵 {artist} — {title}\n\n{song.lyrics[:4000]}')
        else:
            await msg.edit_text('❌ Lyrics not found')
    except Exception as e:
        await msg.edit_text(f'❌ Error: {e}')

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

    await search_lyrics(msg, artist, title)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    voice = update.message.voice
    msg = await update.message.reply_text('⏳ Downloading voice...')

    tg_file = await context.bot.get_file(voice.file_id)
    input_path = os.path.join(DOWNLOAD_DIR, 'voice.ogg')
    await tg_file.download_to_drive(input_path)

    await msg.edit_text('🎤 Transcribing...')
    with open(input_path, 'rb') as f:
        transcription = groq_client.audio.transcriptions.create(
            file=('voice.ogg', f),
            model='whisper-large-v3'
        )
    os.remove(input_path)

    text = transcription.text.strip()

    if ' ' in text:
        parts = text.split(' ', 1)
        artist, title = parts[0], parts[1]
        context.user_data['artist'] = artist
        context.user_data['title'] = title
    else:
        await msg.edit_text('❌ Could not parse. Say: "Artist Title"')
        return

    keyboard = [[
        InlineKeyboardButton("✅ Yes", callback_data='confirm_yes'),
        InlineKeyboardButton("❌ No, retry", callback_data='confirm_no')
    ]]
    await msg.edit_text(
        f'🎤 Heard: "{text}"\nSearch lyrics for *{artist} — {title}*?',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'confirm_yes':
        artist = context.user_data.get('artist')
        title = context.user_data.get('title')
        await search_lyrics(query.message, artist, title)
    else:
        await query.edit_message_text('🎤 Send another voice message')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if ' ' not in text:
        await update.message.reply_text('❌ Send: Artist Title\nExample: Oasis Wonderwall')
        return

    parts = text.split(' ', 1)
    artist, title = parts[0], parts[1]

    msg = await update.message.reply_text(f'⏳ Searching: {artist} — {title}...')
    await search_lyrics(msg, artist, title)

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.AUDIO | filters.Document.AUDIO, handle_audio))
app.add_handler(MessageHandler(filters.VOICE, handle_voice))
app.add_handler(CallbackQueryHandler(handle_confirm))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print('Bot started...')
app.run_polling()