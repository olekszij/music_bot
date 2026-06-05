import os
import re
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

genius = lyricsgenius.Genius(GENIUS_TOKEN, timeout=15, retries=1, sleep_time=0)
groq_client = Groq(api_key=GROQ_TOKEN)

def clean_lyrics(lyrics):
    lyrics = re.sub(r'\d+Embed$', '', lyrics)
    lyrics = re.sub(r'See.*?LiveGet tickets.*?\n', '', lyrics)
    return lyrics.strip()

async def search_lyrics(msg, query):
    try:
        results = genius.search_songs(query)
        if not results or 'hits' not in results or not results['hits']:
            await msg.edit_text('❌ Nothing found')
            return

        hits = results['hits'][:3]

        if len(hits) == 1:
            r = hits[0]['result']
            await msg.edit_text(f"⏳ Loading: {r['primary_artist']['name']} — {r['title']}...")
            song = genius.search_song(r['title'], r['primary_artist']['name'])
            if not song:
                await msg.edit_text('❌ Lyrics not found')
                return
            lyrics = clean_lyrics(song.lyrics)
            await msg.edit_text(f"🎵 {r['primary_artist']['name']} — {r['title']}\n\n{lyrics[:4000]}")
            return

        keyboard = [[
            InlineKeyboardButton(
                f"{r['result']['primary_artist']['name']} — {r['result']['title']}",
                callback_data=f"song_{r['result']['id']}"
            )
        ] for r in hits]

        await msg.edit_text('Which one?', reply_markup=InlineKeyboardMarkup(keyboard))

    except Exception as e:
        await msg.edit_text(f'❌ Error: {e}')

async def handle_song_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    song_id = int(query.data.replace('song_', ''))
    await query.edit_message_text('⏳ Loading lyrics...')

    try:
        song = genius.search_song(song_id=song_id)
        if song:
            lyrics = clean_lyrics(song.lyrics)
            await query.edit_message_text(f'🎵 {song.artist} — {song.title}\n\n{lyrics[:4000]}')
        else:
            await query.edit_message_text('❌ Lyrics not found')
    except Exception as e:
        await query.edit_message_text(f'❌ Error: {e}')

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

    await msg.edit_text(f'🔍 Searching: {artist} — {title}...')
    await search_lyrics(msg, f'{artist} {title}')

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
    context.user_data['query'] = text

    keyboard = [[
        InlineKeyboardButton("✅ Yes", callback_data='confirm_yes'),
        InlineKeyboardButton("❌ No, retry", callback_data='confirm_no')
    ]]
    await msg.edit_text(
        f'🎤 Heard: *"{text}"*\nSearch lyrics?',
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'confirm_yes':
        q = context.user_data.get('query')
        await search_lyrics(query.message, q)
    elif query.data == 'confirm_no':
        await query.edit_message_text('🎤 Send another voice message')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    msg = await update.message.reply_text(f'⏳ Searching: {text}...')
    await search_lyrics(msg, text)

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(MessageHandler(filters.AUDIO | filters.Document.AUDIO, handle_audio))
app.add_handler(MessageHandler(filters.VOICE, handle_voice))
app.add_handler(CallbackQueryHandler(handle_confirm, pattern='^confirm_'))
app.add_handler(CallbackQueryHandler(handle_song_choice, pattern='^song_'))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

print('Bot started...')
app.run_polling()