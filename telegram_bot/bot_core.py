import telegram
from telegram import InlineQueryResultCachedSticker
from telegram.error import NetworkError, Unauthorized
import threading
import logging
from time import sleep, time
from uuid import uuid4

# create logger
module_logger = logging.getLogger(__name__)


class Bot(threading.Thread):
    gp_data = dict()
    run_flag = True
    config = None
    bot = None
    bot_name = None
    lock = None

    def __init__(self, q, lock_obj, config_obj):
        threading.Thread.__init__(self)
        self.thread_name = 'Bot'
        self.bot_name = None
        self.config = config_obj
        self.q = q
        self.lock = lock_obj

    def run(self):
        module_logger.debug('Starting ' + self.thread_name)

        # Telegram Bot Authorization Token
        self.bot = telegram.Bot(self.config.get('bot', 'token'))

        # Save bot name (this is the name given to BotFather for this token)
        self.bot_name = self.bot.get_me().first_name

        # get the first pending update_id, this is so we can skip over it in case
        # we get an "Unauthorized" exception.
        try:
            update_id = self.bot.getUpdates()[0].update_id
        except IndexError:
            update_id = None

        while self.run_flag:
            try:
                update_id = self.serve(update_id)
            except NetworkError:
                sleep(0.2)
            except Unauthorized:
                # The user has removed or blocked the bot.
                update_id += 1

            # Check messages from queue
            self.lock.acquire()
            if not self.q.empty():
                data = self.q.get()

                if data == 'shutdown':
                    self.run_flag = False
                elif data == 'test':
                    print('test')
                else:
                    print('unknown command')

                self.lock.release()
            else:
                self.lock.release()

    def inline_serve(self, update):
        query = update.inline_query.query
        offset = update.inline_query.offset
        results = list()

        module_logger.debug('query: %s, offset: %s' % (query, offset))

        results.append(
            InlineQueryResultCachedSticker(id=uuid4(), sticker_file_id='BQADBAADXwADAtezAg6Zqq6f1-PwAg'))
        results.append(
            InlineQueryResultCachedSticker(id=uuid4(), sticker_file_id='BQADBAADbgADAtezAphXv-ADklTlAg'))
        results.append(
            InlineQueryResultCachedSticker(id=uuid4(), sticker_file_id='BQADBAADmAADAtezAkZHL3xkTt7eAg'))
        results.append(
            InlineQueryResultCachedSticker(id=uuid4(), sticker_file_id='BQADBAADawADAtezAmBkKARLVtZ4Ag'))
        results.append(
            InlineQueryResultCachedSticker(id=uuid4(), sticker_file_id='BQADBAADZwADAtezAh2pt-ijJtUvAg'))
        results.append(
            InlineQueryResultCachedSticker(id=uuid4(), sticker_file_id='BQADBAADZQADAtezAj8CoIX7oxoTAg'))
        results.append(
            InlineQueryResultCachedSticker(id=uuid4(), sticker_file_id='BQADBAADYwADAtezAi67ju8aavYZAg'))
        results.append(
            InlineQueryResultCachedSticker(id=uuid4(), sticker_file_id='BQADBAAD2wADAtezAqLEJmEGiVUhAg'))
        results.append(
            InlineQueryResultCachedSticker(id=uuid4(), sticker_file_id='BQADBAADYQADAtezAnyu634Jm1AVAg'))
        self.bot.answerInlineQuery(update.inline_query.id, results=results, cache_time=3600)

    def gossip_cmd(self, update, first_cmd=False):
        if first_cmd:
            # clear previous remaining data for this chat_id
            self.gossip_clear(update.message.chat_id)

            # set new dict entry for this chat_id
            self.gp_data[update.message.chat_id] = None

            # send message
            self.bot.sendMessage(chat_id=update.message.chat_id, text='Send me your gossip message now...')
        else:
            if self.gp_data[update.message.chat_id] is None:
                # set message
                self.gp_data[update.message.chat_id] = update.message.text

                # show keyboard
                interface = telegram.ReplyKeyboardMarkup([["Yes", "No"]], resize_keyboard=True,
                                                         one_time_keyboard=True)

                self.bot.sendMessage(chat_id=update.message.chat_id, text='Post this message?', reply_markup=interface)
            else:
                if update.message.text == 'Yes':
                    module_logger.debug('Recorded message %s' % self.gp_data[update.message.chat_id])

                    # Hide keyboard
                    interface = telegram.ReplyKeyboardHide(hide_keyboard=True)
                    self.bot.sendMessage(chat_id=update.message.chat_id, text='Message recorded, thanks',
                                         reply_markup=interface)

                # remove dict entry for chat_id
                del self.gp_data[update.message.chat_id]

    def gossip_clear(self, chat_id):
        # clear chat_id entries first
        for index, key in enumerate(self.gp_data):
            if key == chat_id:
                del self.gp_data[chat_id]

    def serve(self, update_id):
        for update in self.bot.getUpdates(offset=update_id, timeout=10):
            update_id = update.update_id + 1
            if not update.message and not update.inline_query:  # weird Telegram update
                continue
            elif not update.message and update.inline_query:  # inline message
                self.inline_serve(update)
                continue

            chat_id = update.message.chat_id
            message = update.message.text
            cmd_message = update.message.text.lower()

            module_logger.debug('%d:%.3f:%s' % (chat_id, time(), message.replace('\n', ' ')))
            # logger.warn('file_id: %s' % update.message.sticker.file_id)

            if update.inline_query:
                print('inline query!')

            if chat_id < 0:
                continue  # bot should not be in a group

            if message.startswith('/'):
                command = cmd_message[1:]
                if command in ("start", "help"):
                    self.start_cmd(update)
                elif command in 'location':
                    for each_section in self.config.sections():
                        if each_section.startswith('location'):
                            self.bot.sendVenue(chat_id=chat_id, title=self.config.get(each_section, 'title'),
                                               address=self.config.get(each_section, 'address'),
                                               latitude=self.config.get(each_section, 'latitude'),
                                               longitude=self.config.get(each_section, 'longitude'))

                elif command in 'gossip':
                    # process gossip command
                    self.gossip_cmd(update, True)
                else:
                    self.bot.sendMessage(chat_id=chat_id, text='Invalid command!')
                continue
            else:
                if self.check_gp_message(chat_id):  # if we are waiting for a message from this chat, process it
                    self.gossip_cmd(update)
                else:
                    self.echo(update)

        return update_id

    def check_gp_message(self, chat_id):
        return True if chat_id in self.gp_data else False

    def echo(self, update):
        if update.message.text:
            # Reply to the message
            self.bot.sendMessage(chat_id=update.message.chat_id, text=update.message.text)

    def start_cmd(self, update):
        self.bot.sendMessage(chat_id=update.message.chat_id, text=self.config.get('bot', 'start_msg'))

    def location_cmd(self, update):
        for each_section in self.config.sections():
            if each_section.startswith('location'):
                self.bot.sendVenue(chat_id=update.message.chat_id, title=self.config.get(each_section, 'title'),
                                   address=self.config.get(each_section, 'address'),
                                   latitude=self.config.get(each_section, 'latitude'),
                                   longitude=self.config.get(each_section, 'longitude'))
