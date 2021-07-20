from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, ConversationHandler, CommandHandler, Updater, CallbackContext
import logging
import os
import youtube_dl
from hurry.filesize import size

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
# Stages
OUTPUT, STORAGE, DOWNLOAD = range(3)

# Callback data
CALLBACK_MP4 = "mp4"
CALLBACK_MP3 = "mp3"
CALLBACK_BEST_FORMAT = "best"
CALLBACK_SELECT_FORMAT = "select_format"
CALLBACK_ABORT = "abort"


def is_supported(url):
    """
    Checks whether the URL type is eligible for youtube_dl.\n
    Returns True or False.
    """
    extractors = youtube_dl.extractor.gen_extractors()
    for e in extractors:
        if e.suitable(url) and e.IE_NAME != 'generic':
            return True
    return False


def start(update: Update, context: CallbackContext):
    update.effective_message.reply_text(
        "Hello! Send /help if you don't know how to use me!")


def help_text(update: Update, context: CallbackContext):
    help_text = '''Just send me a video link like:
    /v <videolink>

    e.g:
    /v youtube.com/watch?v=mKxu_dyzrj4'''
    update.effective_message.reply_text(help_text)


def video(update: Update, context: CallbackContext):
    """
    Invoked on every user message to create an interactive inline conversation.
    """

    # update global URL object
    try:
        url: str = "".join(context.args)
        if is_supported(url):
            # save url to user context
            context.user_data["url"] = url
            keyboard = [[
                InlineKeyboardButton(
                    "Download Best Format",
                    callback_data=f"format_{CALLBACK_BEST_FORMAT}"),
                InlineKeyboardButton("Select Format",
                                     callback_data=CALLBACK_SELECT_FORMAT),
                # TODO add abort button
                # InlineKeyboardButton("Abort", callback_data=CALLBACK_ABORT),
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            # Send message with text and appended InlineKeyboard
            update.message.reply_text("Do you want me to download?",
                                      reply_markup=reply_markup)
        else:
            update.message.reply_text("I can't download your request '%s' 😤" %
                                      url)
    except TypeError:
        logger.info("Invalid url requested:")
        update.message.reply_text("I can't download your request😤")


def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    """
    Creates an interactive button menu for the user.
    """
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu


def select_source_format(update: Update, context: CallbackContext):
    """
    A stage asking the user for the source format to be downloaded.
    """
    logger.info("select_format")
    query = update.callback_query
    query.answer()
    # get formats
    url = context.user_data["url"]
    ydl_opts = {}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        meta: dict = ydl.extract_info(url, download=False)
        formats = meta.get('formats', [meta])

    # dynamically build a format menu
    formats: dict = sorted(formats, key=lambda k: k['ext'])
    button_list = []
    button_list.append(
        InlineKeyboardButton("Best Quality",
                             callback_data=f"format_{CALLBACK_BEST_FORMAT}"))
    for f in formats:
        # {'format_id': '243', 'url': '...', 'player_url': '...', 'ext': 'webm', 'height': 266, 'format_note': '360p',
        # 'vcodec': 'vp9', 'asr': None, 'filesize': 2663114, 'fps': 24, 'tbr': 267.658, 'width': 640, 'acodec': 'none',
        # 'downloader_options': {'http_chunk_size': 10485760}, 'format': '243 - 640x266 (360p)', 'protocol': 'https',
        # 'http_headers': {'User-Agent': '...',
        # 'Accept-Charset': '...', 'Accept': '...',
        # 'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'en-us,en;q=0.5'}}
        format_text = f"{f['format_note']}, {f['height']}x{f['width']}, type: {f['ext']}, fps: {f['fps']}, {size(f['filesize']) if f['filesize'] else 'None'}"
        button_list.append(
            InlineKeyboardButton(format_text,
                                 callback_data=f"format_{f['format_id']}"))
    reply_markup = InlineKeyboardMarkup(build_menu(button_list, n_cols=1))

    query.edit_message_text(text="Choose Format", reply_markup=reply_markup)


def select_output_format(update: Update, context: CallbackContext):
    """
    A stage asking the user for the desired output media format.
    """
    logger.info("output()")
    query = update.callback_query
    context.user_data[CALLBACK_SELECT_FORMAT] = query.data.split("format_",
                                                                 maxsplit=1)[1]
    query.answer()
    keyboard = [[
        InlineKeyboardButton("Audio",
                             callback_data=f"download_{CALLBACK_MP3}"),
        InlineKeyboardButton("Video",
                             callback_data=F"download_{CALLBACK_MP4}"),
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(text="Do you want the full video or just audio?",
                            reply_markup=reply_markup)


def download_media(update: Update, context: CallbackContext):
    """
    A stage downloading the selected media and converting it to the desired output format.
    """
    query = update.callback_query
    query.edit_message_text(text="Downloading..")
    url = context.user_data["url"]
    logger.info("Video URL to download: '%s'", url)
    selected_format = context.user_data[CALLBACK_SELECT_FORMAT]

    # some default configurations for video downloads
    MP3_EXTENSION = 'mp3'
    YOUTUBE_DL_OPTIONS = {
        'format':
        selected_format,
        'restrictfilenames':
        True,
        'outtmpl':
        '%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': MP3_EXTENSION,
            'preferredquality': '192',
        }],
    }

    with youtube_dl.YoutubeDL(YOUTUBE_DL_OPTIONS) as ydl:
        result = ydl.extract_info("{}".format(url))
        original_video_name = str(ydl.prepare_filename(result))

    raw_media_name = os.path.splitext(original_video_name)[0]
    final_media_name = "%s.%s" % (raw_media_name, MP3_EXTENSION)

    # upload the media file
    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Uploading..")
    logger.info("Uploading the file..")
    with open(final_media_name, mode='rb') as video_file:
        update.effective_message.reply_document(document=video_file,
                                                filename=final_media_name,
                                                caption=final_media_name,
                                                quote=True)
    logger.info("Upload finished.")
    if os.path.exists(final_media_name):
        os.remove(final_media_name)
    update.callback_query.answer()


def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(token=BOT_TOKEN)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler("help", help_text)
    video_handler = CommandHandler("v", video)
    source_handler = CallbackQueryHandler(callback=select_source_format,
                                          pattern="^select_format")
    output_handler = CallbackQueryHandler(callback=select_output_format,
                                          pattern="^format_")
    download_handler = CallbackQueryHandler(callback=download_media,
                                            pattern="^download_")

    dp.add_handler(start_handler)
    dp.add_handler(help_handler)
    dp.add_handler(video_handler)
    dp.add_handler(source_handler)
    dp.add_handler(output_handler)
    dp.add_handler(download_handler)

    updater.start_webhook(listen="0.0.0.0", port=int(PORT), url_path=BOT_TOKEN)
    updater.bot.setWebhook(HEROKU + BOT_TOKEN)


if __name__ == '__main__':
    main()
