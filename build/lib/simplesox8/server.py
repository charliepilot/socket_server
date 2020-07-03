import abc

import argparse
import logging
import socket
from socketserver import BaseRequestHandler, ThreadingMixIn, TCPServer
import threading


log = logging.getLogger(__name__)


class ThreadedTCPRequestHandler(BaseRequestHandler):

    client_handler = None

    def __init__(self, *args, **kwargs):
        self.log = logging.getLogger(f"{self.__class__.__name__}")
        super().__init__(*args, **kwargs)

    @property
    def thread_name(self):
        return threading.current_thread().name

    def send(self, data):
        self.log.debug(f"Starting send({data})")
        response = bytes(data, "UTF-8")
        self.request.sendall(response)
        self.log.debug("Finished send")

    def broadcast(self, data):
        self.server.broadcast(data)

    def handle(self):
        self.server.add_request_handler(self)
        self.log.info(f"Client {self.client_address} CONNECTED.")
        # if handler is an instance use it, otherwise instantiate it
        handler = self.client_handler
        if isinstance(handler, type):
            self.log.debug("Creating ClientHandler instance")
            handler = handler()
            handler.server = self.server
        else:
            if not handler.server:
                handler.server = self.server

        try:
            self.request.settimeout(self.server.poll_interval)
            while self.server.server_active:
                try:
                    data = self.request.recv(1024)
                    if data == b"":
                        break

                    msg = str(data, "UTF-8")
                    handler.handle(msg, self)
                except socket.timeout:
                    # used to check if server is active
                    pass
        finally:
            self.server.remove_request_handler(self)
            self.log.info(f"Client {self.client_address} DISCONNECTED.")


class ThreadedTCPServer(ThreadingMixIn, TCPServer):

    allow_reuse_address = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log = logging.getLogger(f"{self.__class__.__name__}")
        self.server_active = True
        self.poll_interval = 0.5
        self.request_handlers = []
        self.mutex = threading.Lock()

    def add_request_handler(self, request_handler):
        with self.mutex:
            if request_handler not in self.request_handlers:
                self.request_handlers.append(request_handler)

    def remove_request_handler(self, request_handler):
        with self.mutex:
            if request_handler in self.request_handlers:
                self.request_handlers.remove(request_handler)

    def loop_request_handlers(self, function, *args, **kwargs):
        with self.mutex:
            for request_handler in self.request_handlers:
                function(request_handler, *args, **kwargs)

    @staticmethod
    def _broadcast(request_handler, data):
        request_handler.send(data)

    def broadcast(self, data):
        self.log.debug("Starting broadcast...")
        self.loop_request_handlers(self._broadcast, data)
        self.log.debug("Finished broadcast")

    def server_close(self):
        log.info("Closing Connections...")
        self.server_active = False
        super().server_close()


class ClientHandlerAbstract(abc.ABC):

    def __init__(self):
        self.log = logging.getLogger(f"{self.__class__.__name__}")
        self.server = None

    @abc.abstractmethod
    def handle(self, data, request_handler: ThreadedTCPRequestHandler):
        pass


class HelloClientHandler(ClientHandlerAbstract):
    def handle(self, data, request_handler: ThreadedTCPRequestHandler):
        self.log.debug("Starting Hello Client Handler...")
        msg = f"{request_handler.thread_name}: Hello {data.strip()}!"
        request_handler.broadcast(msg)
        # request_handler.send(msg)
        self.log.debug("Finished Hello Client Handler.")


class BroadcastClientHandler(ClientHandlerAbstract):
    def handle(self, data, request_handler: ThreadedTCPRequestHandler):
        self.log.debug("Starting Broadcast Client Handler...")
        request_handler.broadcast(data)
        self.log.debug("Finished Broadcast Client Handler.")


class SendClientHandler(ClientHandlerAbstract):
    def handle(self, data, request_handler: ThreadedTCPRequestHandler):
        self.log.debug("Starting Send Client Handler...")
        request_handler.send(data)
        self.log.debug("Finished Send Client Handler.")


def add_arguments(parser: argparse.ArgumentParser):
    # add arguments
    parser.add_argument(
        "--host",
        metavar="H",
        type=int,
        help="- Host IP (Listen)"
    )
    parser.add_argument(
        "--port",
        metavar="P",
        type=int,
        help="- Host Port (Listen)"
    )
    parser.add_argument(
        "--poll_interval",
        metavar="I",
        type=float,
        help="- poll intervals in seconds"
    )
    parser.add_argument(
        "--request_queue_size",
        metavar="L",
        type=int,
        help="- request queues size"
    )


def server_main(
        host=None,
        port=None,
        client_handler=None,
        request_queue_size=None,
        poll_interval=None,
        logging_config=None
):
    if logging_config:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)-30s | " +
                   "%(threadName)-15s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    server_address = (host or "", port or 4000)
    client_handler = client_handler or SendClientHandler()
    log.info(f"Starting Server {server_address}...")
    ThreadedTCPRequestHandler.client_handler = client_handler
    server = ThreadedTCPServer(server_address, ThreadedTCPRequestHandler)
    server.poll_interval = poll_interval or server.poll_interval
    server.request_queue_size = request_queue_size or server.request_queue_size

    with server:
        try:
            # Start a thread with the server -- that thread will then start one
            # more thread for each request
            server_thread = threading.Thread(target=server.serve_forever)
            # Exit the server thread when the main thread terminates
            server_thread.daemon = True
            server_thread.block_on_close = True
            server_thread.start()
            log.info(f"Server {server_address} loop running in thread: " +
                     f"{server_thread.name}")
            server_thread.join()
        except KeyboardInterrupt:
            pass
        finally:
            log.info(f"SHUTTING SERVER DOWN {server_address}...")
            server.server_close()
            server.shutdown()

    log.info(f"Server SHUTDOWN COMPLETE {server_address}...")


if __name__ == "__main__":
    server_main(client_handler=HelloClientHandler(), logging_config=True)
