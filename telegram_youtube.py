import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, filters
from telegram import Chat as TGChat
import os
import shutil
import threading
from youtube import *

# Constants
PORT = int(os.environ.get('PORT', 5000))
TOKEN = '7024553219:AAHs4FULEg744a4GanUtNiCwjNfX14xBMPo'

# Conversation states
START_CO, GET_WORD, GET_NUMBER, GET_CHANNEL_URL, GET_URL, CONFIRMATION = range(1, 7)

# Reply keyboards
reply_keyboard_start = [['Download entire channel'], ['Download with searching word'], ['Download one video'], ['See processes'], ['exit']]
markup_start = telegram.ReplyKeyboardMarkup(reply_keyboard_start, resize_keyboard=True, one_time_keyboard=True)

reply_keyboard_back = [['back', '🏠 home', 'exit']]
markup_back = telegram.ReplyKeyboardMarkup(reply_keyboard_back, resize_keyboard=True, one_time_keyboard=True)

reply_keyboard_confirmation = [['I confirm'], ['🏠 home', 'exit']]
markup_confirmation = telegram.ReplyKeyboardMarkup(reply_keyboard_confirmation, resize_keyboard=True, one_time_keyboard=True)

# Start command handler
def start(update, context):
    update.message.reply_text('Choose between options:', reply_markup=markup_start)
    return START_CO

# Start conversation handler
def start_co(update, context):
    user_data = context.user_data
    text = update.message.text

    remake_folder(str(update.effective_user.id))

    if text == 'Download entire channel':
        update.message.reply_text('Enter URL of one video on the channel you want to download:', reply_markup=markup_back)
        return GET_CHANNEL_URL
    elif text == 'Download with searching word':
        update.message.reply_text('Enter a word you want to search:', reply_markup=markup_back)
        return GET_WORD
    elif text == 'Download one video':
        update.message.reply_text('Enter the link of the video:', reply_markup=markup_back)
        return GET_URL

# Get channel URL handler
def get_channel_url(update, context):
    user_data = context.user_data
    text = update.message.text

    if text == 'back':
        update.message.reply_text('Choose:', reply_markup=markup_start)
        return START_CO

    channel_id = find_channel_id(text)
    if channel_id:
        list_of_urls = get_videos_from_channel(channel_id)
        if list_of_urls:
            user_data['list_of_urls'] = list_of_urls
            update.message.reply_text(f'There are {len(list_of_urls)} videos on this channel', reply_markup=markup_confirmation)
            return CONFIRMATION
    else:
        update.message.reply_text('Could not find the channel ID', reply_markup=markup_start)
        return START_CO

# Helper function to download videos
def do_downloading(update, user_data):
    for url in user_data['list_of_urls']:
        try:
            status = Download(url['url'], update.effective_user.id)
            if status:
                update.message.reply_video(video=open(status, 'rb'), caption=url['title'])
            else:
                update.message.reply_text(f"Could not download the video {url['url']}")
        except Exception as e:
            update.message.reply_text(f"Could not download {url['url']}: {str(e)}")

# Confirmation handler
def confirmation(update, context):
    user_data = context.user_data
    user = update.effective_user
    text = update.message.text

    if text != 'I confirm':
        update.message.reply_text('Choose:', reply_markup=markup_start)
        return START_CO

    t = threading.Thread(target=do_downloading, args=(update, user_data))
    t.start()
    user_data.setdefault('threads', []).append(t)

    update.message.reply_text('Starting download process...', reply_markup=markup_start)
    return START_CO

# Stop conversation handler
def stop_conversation(update, context):
    update.message.reply_text('Goodbye!', reply_markup=telegram.ReplyKeyboardRemove())
    return ConversationHandler.END

# Cancel handler
def cancel(update, context):
    update.message.reply_text('Cancelled.', reply_markup=telegram.ReplyKeyboardRemove())
    return ConversationHandler.END

# Timeout handler
def timeout(update, context):
    user = update.effective_user
    try:
        remake_folder(str(user.id))
    except Exception as e:
        print(f"Error while handling timeout: {str(e)}")

    update.message.reply_text('The session has timed out.', reply_markup=telegram.ReplyKeyboardRemove())

# Error handler
def error(update, context):
    print(f"Update {update} caused error {context.error}")

# Main function
def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            START_CO: [MessageHandler(Filters.regex('^Download entire channel$|^Download with searching word$|^Download one video$|^See processes$'), start_co)],
            GET_WORD: [MessageHandler(Filters.text & ~Filters.command, get_channel_url)],
            GET_NUMBER: [MessageHandler(Filters.text & ~Filters.command, get_number_of_videos)],
            GET_CHANNEL_URL: [MessageHandler(Filters.text & ~Filters.command, get_channel_url)],
            GET_URL: [MessageHandler(Filters.text & ~Filters.command, one_video_download)],
            CONFIRMATION: [MessageHandler(Filters.regex('^I confirm$'), confirmation)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start), MessageHandler(Filters.regex('^exit$'), stop_conversation), MessageHandler(Filters.regex('^🏠 home$'), start)],
        conversation_timeout=50000
    )

    dp.add_handler(conv_handler)
    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()





# Helper function to remake folder
def remake_folder(folder_name):
    folder_name = f'Downloads/{folder_name}'
    if os.path.exists(folder_name):
        shutil.rmtree(folder_name)
    os.makedirs(folder_name)

if __name__ == '__main__':
    main()
