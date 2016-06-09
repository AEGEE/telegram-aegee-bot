from telegram_bot import bot_core
from telegram_bot.xmlrpc_server import xml_rpc_server
from multiprocessing import Queue
import threading
import logging
try:
    import configparser
except ImportError:
    import ConfigParser as configparser
import argparse

# Logging init and level
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# argument parser
parser = argparse.ArgumentParser()
parser.add_argument("--config", help="Bot config file", required=True)  # mandatory config file as parameter
args = vars(parser.parse_args())

# Read config file
config = configparser.ConfigParser()
config.read(args['config'])

# Init queue and its lock
queueLock = threading.Lock()
workQueue = Queue(10)
threads = []


def main():
    # Allocate and start bot class using token from config file
    bot_thread = bot_core.Bot(workQueue, queueLock, config)
    bot_thread.start()

    # Allocate and start XmlRPC server
    xmlrpc_thread = xml_rpc_server.XmlRPCServer(workQueue, queueLock, config)
    xmlrpc_thread.start()

    # Append threads
    threads.append(bot_thread)
    threads.append(xmlrpc_thread)

    # Wait for all threads to complete
    for t in threads:
        t.join()

    logger.debug('Exiting Main Thread')

if __name__ == '__main__':
    main()
