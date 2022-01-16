from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Message
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Updater, CallbackContext
import logging
import os
import yt_dlp
from uuid import uuid4

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
HEROKU = os.getenv('HEROKU')
PORT = os.getenv('PORT', 5000)

# error if there is no bot token set
if None in (BOT_TOKEN, HEROKU):
    logger.error("BOT_TOKEN or heroku is not set, exiting.")
    exit(1)


def is_supported(url):
    """
    Checks whether the URL type is eligible for yt_dlp.\n
    Returns True or False.
    """
    extractors = yt_dlp.extractor.gen_extractors()
    for e in extractors:
        if e.suitable(url) and e.IE_NAME != 'generic':
            return True
    return False


def start(update: Update, context: CallbackContext):
    assert isinstance(update.effective_message, Message)
    update.effective_message.reply_text(
        "")


def help_text(update: Update, context: CallbackContext):
    help_text = '''TEST'''
    assert isinstance(update.effective_message, Message)
    update.effective_message.reply_text(help_text)


def extractYt(yturl: str) -> tuple[str, str]:
    ydl = yt_dlp.YoutubeDL()
    with ydl:
        r = ydl.extract_info(yturl, download=False)
        assert isinstance(r, dict)
        return r['title'], r['thumbnail']


def catch_url(update: Update, context: CallbackContext):
    """
    Invoked on every user message to create an interactive inline conversation.
    """

    try:
        assert isinstance(context.user_data, dict)
        url: str = "".join(context.args) if context.args is not None else ""
        if is_supported(url):
            # save url to user context
            context.user_data["url"] = url
            keyboard = [[
                InlineKeyboardButton("Audio", callback_data=f"format_mp3"),
                InlineKeyboardButton("Video", callback_data="format_mp4"),
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text("Apa yang Anda ingin saya unduh?",
                                      reply_markup=reply_markup)
        else:
            keyboard1 = [[
                InlineKeyboardButton("🔍 Cari di Database", callback_data=f"help_text"),
                InlineKeyboardButton("📩 Lapor/REQ", url="https://t.me/otakuindonew"),
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard1)
            update.message.reply_text(f"Mohon maaf, url {url} anda ketik salah, silahkan masukan link yt dengan benar, Seperti dibawah ini \n /yt https://www.youtube.com/watch?v=lpiB2wMc49g)
    except TypeError:
        logger.info("Invalid url requested:")
        update.message.reply_text("Saya tidak dapat mengunduh permintaan Anda")


def download_media(update: Update, context: CallbackContext):
    """
    A stage downloading the selected media and converting it to the desired output format.
    """
    query = update.callback_query
    query.edit_message_text(text="proses...(jika masih begini), silahkan ulang lagi.... atau url kena pembatasan...")
    assert isinstance(context.user_data, dict)
    url = context.user_data["url"]
    logger.info(f"Video URL to download: '{url}'")
    media_type = query.data.split("_")[1]
    name, thumbnail = extractYt(url)
    unique_id = str(uuid4().int)
    ydl_opts = {"outtmpl": f"{unique_id}.%(ext)s", 'noplaylist': True}
    if media_type == "mp3":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }]
    else:
        ydl_opts["format"] = "best"
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }]
    query.edit_message_text(text="Sedang Mendownload..(jika not respond, silahkan ganti link.")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    media_name = unique_id + "." + media_type

    # upload the media file
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Proses Berhasil, Sedang Upload ke telegram...")
    update.callback_query.answer()
    logger.info("Uploading the file..")
    with open(media_name, mode='rb') as video_file:
        assert isinstance(update.effective_message, Message)
        update.effective_message.reply_document(document=video_file,
                                                filename=name + "." +
                                                media_type,
                                                caption=name,
                                                thumb=thumbnail,
                                                quote=True)
    logger.info("Upload finished.")
    if os.path.exists(media_name):
        os.remove(media_name)


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(token=BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler("help", help_text)
    video_handler = CommandHandler("yt", catch_url)
    download_handler = CallbackQueryHandler(callback=download_media,
                                            pattern="^format_mp[34]$")

    dp.add_handler(start_handler)
    dp.add_handler(help_handler)
    dp.add_handler(video_handler)
    dp.add_handler(download_handler)
    if None not in (BOT_TOKEN, HEROKU):
        assert isinstance(BOT_TOKEN, str)
        assert isinstance(HEROKU, str)
        updater.start_webhook(listen="0.0.0.0",
                              port=int(PORT),
                              url_path=BOT_TOKEN,
                              webhook_url=HEROKU + BOT_TOKEN)


if __name__ == '__main__':
    main()
