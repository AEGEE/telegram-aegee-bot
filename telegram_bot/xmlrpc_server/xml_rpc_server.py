try:
    from xmlrpc.server import SimpleXMLRPCServer
except ImportError:
    import xmlrpclib
import threading
import logging

# create logger
module_logger = logging.getLogger(__name__)


class XmlRPCServer(threading.Thread):
    run_flag = True
    config = None
    lock = None

    def __init__(self, q, lock_obj, config_obj):
        threading.Thread.__init__(self)
        self.thread_name = 'XMLRPCServer'
        self.q = q
        self.config = config_obj
        self.lock = lock_obj

        self.server = SimpleXMLRPCServer((self.config.get('rpc-server', 'host'),
                                          self.config.getint('rpc-server', 'port')), logRequests=False, allow_none=True)
        self.server.register_introspection_functions()
        self.server.register_function(self.shutdown)
        self.server.register_function(self.test)

    def run(self):
        module_logger.debug('Starting ' + self.thread_name)

        while self.run_flag:
            self.server.handle_request()

    def test(self):
        module_logger.debug('running test')
        self.lock.acquire()
        self.q.put('test')
        self.lock.release()

    def shutdown(self):
        module_logger.debug('shutdown')
        # send close message to other thread
        self.lock.acquire()
        self.q.put('shutdown')
        self.lock.release()
        # close RPC server
        self.run_flag = False
