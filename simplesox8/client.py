import abc
import logging
import socket
import threading
from time import sleep

log = logging.getLogger(__name__)


class _Observable:
    def __init__(self):
        self._observers = []

    @property
    def observers(self):
        return self._observers[:]

    def register_observer(self, observer):
        if observer in self._observers:
            log.warning(f"{observer.__class__.__name__} already registered.")
        else:
            self._observers.append(observer)
            log.info(f"Registered observer {observer.__class__.__name__}")

    def unregister_observer(self, observer):
        name = observer.__class__.__name__
        if observer in self._observers:
            self._observers.remove(observer)
            log.info(f"Unregistered observer {name}")
        else:
            log.warning(f"{name} was not a registered observer")

    def notify_observers(self, *args, **kwargs):
        for observer in self._observers:
            observer.notify(self, *args, **kwargs)


class ClientObserverAbstract(abc.ABC):
    def __init__(self, observable=None):
        if observable:
            observable.register_observer(self)

    @abc.abstractmethod
    def notify(self, observable, client_thread, message):
        raise NotImplementedError("notify not implemented")


class EchoObserver(ClientObserverAbstract):

    def notify(self, observable, client_thread, message):
        print(message)


class LogDebugObserver(ClientObserverAbstract):

    def notify(self, observable, client_thread, message):
        log.debug(f"Observer message: {message}")


class LogInfoObserver(ClientObserverAbstract):

    def notify(self, observable, client_thread, message):
        log.info(f"Observer message: {message}")


class ClientThread(threading.Thread):

    def __init__(self, client, daemon=None):
        threading.Thread.__init__(self)
        self.setDaemon(daemon or False)
        self.log = logging.getLogger(f"{self.__class__.__name__}")

        self.name = f"Client.{self.name}"
        self._client = client

        self._continue = True

        log.info(f"Client connected to server: {self.client.server_address}")

    @property
    def client(self):
        return self._client

    def interrupt(self):
        self._continue = False

    def run(self):
        log.info(f"Client listening to server: {self.client.server_address}")
        try:
            while self._continue:
                try:
                    data = self.client.socket.recv(
                        self.client.receive_buffer_size)
                    if data == b"":
                        break

                    msg = data.decode()
                    self.client.notify_observers(self, msg)
                    log.debug(f"Data from server: {msg}")
                except socket.timeout:
                    # used to check the interrupt (while self._continue)
                    pass
        finally:
            log.info(f"Client disconnected from server " +
                     f"{self.client.server_address}")
            if not self.client.is_shutting_down:
                self.client.connect()


class Client(_Observable):

    def __init__(self, server=None, port=None, timeout=None):
        super().__init__()
        self._server = server or "127.0.0.1"
        self._port = port or 4000
        self._timeout = timeout or 0.5
        self._socket = None
        self._thread = None
        self._continue = True
        self._is_shutting_down = False

        self.receive_buffer_size = 2048

    @property
    def server(self):
        return self._server

    @property
    def port(self):
        return self._port

    @property
    def server_address(self):
        return self.server, self.port

    @property
    def is_shutting_down(self):
        return self._is_shutting_down

    @property
    def socket(self):
        return self._socket

    @property
    def timeout(self):
        return self._timeout

    @property
    def thread(self):
        return self._thread

    def interrupt(self):
        self._continue = False

    def connect_socket(self):
        log.info(f"Creating socket to server {self.server_address}")
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect(self.server_address)
        self.socket.settimeout(self.timeout)

    def start_thread(self):
        log.info("Creating ClientThread")
        self._thread = ClientThread(self, daemon=True)
        log.info("Starting ClientThread")
        self.thread.start()

    def connect(self):
        while True:
            try:
                log.info(f"Connecting to server {self.server_address}")
                self.connect_socket()
                self.start_thread()
                break
            except Exception as e:
                log.exception(e)
                sleep(5)

    def start(self, execute, *args, **kwargs):
        try:
            self.connect()
            execute(self, *args, *kwargs)
        finally:
            self.shutdown()

    def start_forever(self, execute, *args, **kwargs):
        try:
            self.connect()
            while self._continue:
                okay = execute(self, *args, **kwargs)
                if not okay:
                    self.interrupt()
        finally:
            self.shutdown()

    def send(self, data):
        self.socket.sendall(bytes(data, 'UTF-8'))

    def shutdown(self):
        log.info(f"Client shutting down...")
        self._is_shutting_down = True
        self.interrupt()
        log.info(f"Closing connection to server {self.server_address}")
        if self.thread:
            self.thread.interrupt()
            self.thread.join()

        self.socket.close()
        log.info(f"Client shutdown COMPLETE")


def execute_input(client):
    data = input('>')
    err_count = 0
    while True:
        try:
            client.send(data)
            break
        except Exception:
            if err_count >= 60:
                raise

            err_count += 1
            sleep(10)

    return True


def client_main(
        host_server=None,
        port=None,
        timeout=None,
        execute=None,
        observers=None,
        logging_config=None
):
    try:
        if logging_config:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s | %(levelname)-8s | %(name)-30s | " +
                       "%(threadName)-15s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )

        client = Client(
            server=host_server,
            port=port,
            timeout=timeout
        )
        observers = observers or [
            EchoObserver(),
            LogDebugObserver()
        ]
        for observer in observers:
            client.register_observer(observer)

        client.start_forever(execute or execute_input)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    client_main()
