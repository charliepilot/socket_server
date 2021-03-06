# Socket Server
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Socket Server is a simple TCP Socket server and client.

## Server
The server needs a client handler to process received data.  
Three client handlers are provided:
* **HelloClientHandler** - broadcast to all connected clients "Hello *{data}*!"
* **BroadcastClientHandler** - echos received data to all connected clients
* **SendClientHandler** - echos received data back to the sender only

A custom handler can be created by implementing the abstract class **ClientHandlerAbstract**.
```python
class SaysClientHandler(ClientHandlerAbstract):
    def handle(self, data, request_handler: ThreadedTCPRequestHandler):
        self.log.debug("Starting Says Client Handler...")
        msg = f"{request_handler.thread_name}: Server Says: '{data.strip()}!'"
        request_handler.broadcast(msg)
        # request_handler.send(msg)
        self.log.debug("Finished Says Client Handler.")
```
The original request is available from request_handler.
```python
request_handler.request
```
#### Starting the server
To start the server, call server_main.

**server_main** parameters
> * **host** - dns or ip of the server, default = ""
> * **port** - port server listens for connections, default = 4000
> * **client_handler** - an implementation of *ClientHandlerAbstract*.
> When data is received, the *handle* method is called.
> If *client_handler* is passed the class, each connection will instantiate 
> the class.  If *client_handler* is passed the instantiated 
> object, each connection will share the object. 
> default = *SendClientHandler()*
>* **poll_interval** - number of seconds before the request recv (receive) 
> times out so that it can check for a shutdown.  Then it retries the recv.
> default = 0.5
> * **logging_config** *boolean* If True, logging is configured to display to
> the console. default = False

```python
server_main(
    host="127.0.0.1",
    port=5000,
    client_handler=SaysClientHander,
    poll_interval=1.5,
    logging_config=True
)
```
## Client
The client needs execution code and observer(s).  The execute code sends data
to the server.  The observer(s) are registered to the client to process data 
from the server.  

One execution function is provided:
* **execute_input** - accepts input from the console and sends it to the 
server.

A custom execution function can be provided.  It is a simple function with
one parameter that will contain the **Client** object.  If it returns *False*,
the client shuts down.  If it returns *True*, the function will be called 
again.

The original socket is available from the client parameter.
```python
def execute_hello_world(client):
    client.socket.send("Hello world")
    return True
```

Three observers are provided:
* **EchoObserver** - data is echoed to the console.
* **LogDebugObserver** - data is sent to the logger debug.
* **LogInfoObserver** - data is sent to the logger info.

A custom observer can be created by implementing the abstract class 
**ClientObserverAbstract**.

```python
class LogWarningObserver(ClientObserverAbstract):
    def notify(self, observable, client_thread, message):
        log.warning(f"Observer message: {message}")
```

#### Starting the client
To start the client, call client_main.

**client_main** parameters
> * **host** - dns or ip of the server, default = ""
> * **port** - port server listens for connections, default = 4000
> * **time_out** - number of seconds before the socket recv (receive) 
> times out so that it can check for a shutdown.  Then it retries the recv.
> default = 0.5
> * **execute** - function that is called to send data to the server.
>* **observers** - array of observer to register.  
>default = [EchoObserver(), LogDebugObserver()]
> * **logging_config** *boolean* If True, logging is configured to display to
> the console. default = False
```python
client_main(
    host="127.0.0.1",
    port=5000,
    time_out=1.5,
    execute=execute_hello_world,
    observers=[EchoObserver()],
    logging_config=True
)
```

## License
This project is licensed under the MIT License - see the 
[LICENSE](LICENSE) file for details
