from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Message
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Updater, CallbackContext
import logging
import os
import yt_dlp

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
        "Hello! Send /help if you don't know how to use me!")


def help_text(update: Update, context: CallbackContext):
    help_text = '''Just send me a video link like:
/v <videolink>

e.g:
/v youtube.com/watch?v=mKxu_dyzrj4'''
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
            update.message.reply_text("What do you want me to download?",
                                      reply_markup=reply_markup)
        else:
            update.message.reply_text(f"I can't download your request '{url}'")
    except TypeError:
        logger.info("Invalid url requested:")
        update.message.reply_text("I can't download your request")


def download_media(update: Update, context: CallbackContext):
    """
    A stage downloading the selected media and converting it to the desired output format.
    """
    query = update.callback_query
    query.edit_message_text(text="Downloading..")
    assert isinstance(context.user_data, dict)
    url = context.user_data["url"]
    logger.info(f"Video URL to download: '{url}'")
    media_type = query.data.split("_")[1]
    name, thumbnail = extractYt(url)
    ydl_opts = {"outtmpl": f"{name}.%(ext)s", 'noplaylist': True}
    if media_type == "mp3":
        ydl_opts["format"] = "bestaudio/best"
        ydl_opts["postprocessors"] = [{
            'key': 'FFmpegExtractAudio',
            'preferedformat': 'mp3',
            'preferredquality': '192'
        }]
    else:
        ydl_opts["format"] = "bestvideo[ext=mp4]+bestaudio/best"
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegVideoConvertor',
            'preferedformat': 'mp4'
        }]

    media_name = os.path.splitext(name)[0] + "." + media_type

    # upload the media file
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Uploading..")
    update.callback_query.answer()
    logger.info("Uploading the file..")
    with open(media_name, mode='rb') as video_file:
        assert isinstance(update.effective_message, Message)
        update.effective_message.reply_document(document=video_file,
                                                filename=media_name,
                                                caption=name,
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
    video_handler = CommandHandler("v", catch_url)
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
                              url_path=BOT_TOKEN)
        updater.bot.setWebhook(HEROKU + BOT_TOKEN)


if __name__ == '__main__':
    main()
