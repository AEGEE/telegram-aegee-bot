import telegram
from telegram import InlineQueryResultCachedSticker
from telegram.error import NetworkError, Unauthorized
from multiprocessing import Queue
from time import sleep, time
import threading
import logging
import configparser
import argparse
from uuid import uuid4
from xmlrpc.server import SimpleXMLRPCServer


class Bot(threading.Thread):
    """Bot Class"""
    gp_data = dict()
    run_flag = 1
    config = None

    def __init__(self, q, config_obj):
        threading.Thread.__init__(self)
        self.thread_name = 'Bot'
        self.bot_name = None
        self.config = config_obj
        self.q = q

    def run(self):
        print('Starting ' + self.thread_name)

        # Telegram Bot Authorization Token
        bot = telegram.Bot(self.config.get('bot', 'token'))

        # get the first pending update_id, this is so we can skip over it in case
        # we get an "Unauthorized" exception.
        try:
            update_id = bot.getUpdates()[0].update_id
        except IndexError:
            update_id = None

        while self.run_flag:
            try:
                update_id = self.serve(bot, update_id)
            except NetworkError:
                sleep(0.2)
            except Unauthorized:
                # The user has removed or blocked the bot.
                update_id += 1

            # Check messages from queue
            queueLock.acquire()
            if not self.q.empty():
                data = self.q.get()

                if data == 'shutdown':
                    self.run_flag = 0
                elif data == 'test':
                    print('test')
                else:
                    print('unknown command')

                queueLock.release()
            else:
                queueLock.release()

    def serve(self, bot, update_id):
        for update in bot.getUpdates(offset=update_id, timeout=10):
            update_id = update.update_id + 1
            if not update.message and not update.inline_query:  # weird Telegram update with only an update_id and no inline
                continue
            elif not update.message and update.inline_query: # inline message
                query = update.inline_query.query
                offset = update.inline_query.offset
                results = list()

                logger.warn('query: %s, offset: %s' % (query, offset))

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
                bot.answerInlineQuery(update.inline_query.id, results=results, cache_time=3600)
                continue

            chat_id = update.message.chat_id
            message = update.message.text
            cmd_message = update.message.text.lower()

            logger.warn('%d:%.3f:%s' % (chat_id, time(), message.replace('\n', ' ')))
            #logger.warn('file_id: %s' % update.message.sticker.file_id)

            if update.inline_query:
                print('inline query!')

            if chat_id < 0:
                continue  # bot should not be in a group

            if message.startswith('/'):
                command = cmd_message[1:]
                if command in ("start", "help"):
                    self.start_help(bot, chat_id)
                elif command in 'location':
                    for each_section in self.config.sections():
                        if each_section.startswith('location'):
                            bot.sendVenue(chat_id=chat_id, title=self.config.get(each_section, 'title'),
                                          address=self.config.get(each_section, 'address'),
                                          latitude=self.config.get(each_section, 'latitude'),
                                          longitude=self.config.get(each_section, 'longitude'))

                elif command in 'gossip':
                    # clear chat_id entries first
                    for index, key in enumerate(self.gp_data):
                        if key == chat_id:
                            del self.gp_data[chat_id]

                    # set new dict entry
                    self.gp_data[chat_id] = None

                    bot.sendMessage(chat_id=chat_id, text='Send me your gossip message now...')
                else:
                    bot.sendMessage(chat_id=chat_id, text='Invalid command!')
                continue
            else:
                if self.check_gp_message(chat_id):

                    if self.gp_data[chat_id] is None:
                        # set message
                        self.gp_data[chat_id] = message

                        # show keyboard
                        interface = telegram.ReplyKeyboardMarkup([["Yes", "No"]], resize_keyboard=True,
                                                                 one_time_keyboard=True)

                        bot.sendMessage(chat_id=chat_id, text='Post this message?', reply_markup=interface)
                    else:
                        if message == 'Yes':
                            logger.warn('Recorded message %s' % self.gp_data[chat_id])

                            # Hide keyboard
                            interface = telegram.ReplyKeyboardHide(hide_keyboard=True)
                            bot.sendMessage(chat_id=chat_id, text='Message recorded, thanks', reply_markup=interface)

                        del self.gp_data[chat_id]
                else:
                    self.echo(bot, chat_id, message)

        return update_id

    def check_gp_message(self, chat_id):
        if chat_id in self.gp_data:
            return True
        else:
            return False

    def echo(self, bot, chat_id, message):
        if message:
            # Reply to the message
            bot.sendMessage(chat_id=chat_id, text=message)

    def start_help(self, bot, chat_id):
        text = ("Send me the numbers of a surah and ayah, for example:"
                " 2 255. Then I respond with that ayah from the Noble "
                "Quran. Or type: random.")

        bot.sendMessage(chat_id=chat_id, text=text)


class XmlRPCServer(threading.Thread):
    run_flag = 1

    def __init__(self, q, host, port):
        threading.Thread.__init__(self)
        self.thread_name = 'XMLRPCServer'
        self.q = q

        self.server = SimpleXMLRPCServer((host, port), logRequests=True, allow_none=True)
        self.server.register_introspection_functions()
        self.server.register_function(self.shutdown)
        self.server.register_function(self.test)

    def run(self):
        print('Starting ' + self.thread_name)

        while self.run_flag:
            self.server.handle_request()

    def test(self):
        print('running test')
        queueLock.acquire()
        self.q.put('test')
        queueLock.release()

    def shutdown(self):
        print('shutdown')
        # send close message to other thread
        queueLock.acquire()
        self.q.put('shutdown')
        queueLock.release()
        # close RPC server
        self.run_flag = 0


# Logging init and level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# argument parser
parser = argparse.ArgumentParser()
parser.add_argument("--config", help="Bot config file", required=True)
args = vars(parser.parse_args())

# Read config file
config = configparser.ConfigParser()
config.read(args['config'])

queueLock = threading.Lock()
workQueue = Queue(10)
threads = []


def main():
    # Allocate and start bot class using token from config file
    bot_thread = Bot(workQueue, config)
    bot_thread.start()

    # Allocate and start XmlRPC server
    xmlrpc_thread = XmlRPCServer(workQueue, config.get('rpc-server', 'host'), config.getint('rpc-server', 'port'))
    xmlrpc_thread.start()

    # Append threads
    threads.append(bot_thread)
    threads.append(xmlrpc_thread)

    # Wait for all threads to complete
    for t in threads:
        t.join()

    print('Exiting Main Thread')

if __name__ == '__main__':
    main()
