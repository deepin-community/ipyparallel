(parallel-connections)=

# Connection Diagrams of The IPython ZMQ Cluster

This is a quick summary and illustration of the connections involved in the ZeroMQ based
IPython cluster for parallel computing.

## All Connections

The IPython cluster consists of a Controller, and one or more each of clients and engines.
The goal of the Controller is to manage and monitor the connections and communications
between the clients and the engines. The Controller is no longer a single process entity,
but rather a collection of processes - specifically one Hub, and 4 (or more) Schedulers.

It is important for security/practicality reasons that all connections be inbound to the
controller processes. The arrows in the figures indicate the direction of the
connection.

```{figure} figs/allconnections.png
:align: center
:alt: IPython cluster connections
:width: 432px

All the connections involved in connecting one client to one engine.
```

The Controller consists of 1-5 processes. Central to the cluster is the **Hub**, which monitors
engine state, execution traffic, and handles registration and notification. The Hub includes a
Heartbeat Monitor for keeping track of engines that are alive. Outside the Hub are 4
**Schedulers**. These devices are very small pure-C MonitoredQueue processes (or optionally
threads) that relay messages very fast, but also send a copy of each message along a side socket
to the Hub. The MUX queue and Control queue are MonitoredQueue ØMQ devices which relay
explicitly addressed messages from clients to engines, and their replies back up. The Balanced
queue performs load-balancing destination-agnostic scheduling. It may be a MonitoredQueue
device, but may also be a Python Scheduler that behaves externally in an identical fashion to MQ
devices, but with additional internal logic. stdout/err are also propagated from the Engines to
the clients via a PUB/SUB MonitoredQueue.

### Registration

```{figure} figs/queryfade.png
:align: center
:alt: IPython Registration connections
:width: 432px

Engines and Clients only need to know where the Query `ROUTER` is located to start
connecting.
```

Once a controller is launched, the only information needed for connecting clients and/or
engines is the IP/port of the Hub's `ROUTER` socket called the Registrar. This socket
handles connections from both clients and engines, and replies with the remaining
information necessary to establish the remaining connections. Clients use this same socket for
querying the Hub for state information.

### Heartbeat

```{figure} figs/hbfade.png
:align: center
:alt: IPython Heartbeat connections
:width: 432px

The heartbeat sockets.
```

The heartbeat process has been described elsewhere. To summarize: the Heartbeat Monitor
publishes a distinct message periodically via a `PUB` socket. Each engine has a
`zmq.FORWARDER` device with a `SUB` socket for input, and `DEALER` socket for output.
The `SUB` socket is connected to the `PUB` socket labeled _ping_, and the `DEALER` is
connected to the `ROUTER` labeled _pong_. This results in the same message being relayed
back to the Heartbeat Monitor with the addition of the `DEALER` prefix. The Heartbeat
Monitor receives all the replies via an `ROUTER` socket, and identifies which hearts are
still beating by the `zmq.IDENTITY` prefix of the `DEALER` sockets, which information
the Hub uses to notify clients of any changes in the available engines.

### Schedulers

```{figure} figs/queuefade.png
:align: center
:alt: IPython Queue connections
:width: 432px

Control message scheduler on the left, execution (apply) schedulers on the right.
```

The controller has at least three Schedulers. These devices are primarily for
relaying messages between clients and engines, but the Hub needs to see those
messages for its own purposes. Since no Python code may exist between the two sockets in a
queue, all messages sent through these queues (both directions) are also sent via a
`PUB` socket to a monitor, which allows the Hub to monitor queue traffic without
interfering with it.

For tasks, the engine need not be specified. Messages sent to the `ROUTER` socket from the
client side are assigned to an engine via ZMQ's `DEALER` round-robin load balancing.
Engine replies are directed to specific clients via the IDENTITY of the client, which is
received as a prefix at the Engine.

For Multiplexing, `ROUTER` is used for both in and output sockets in the device. Clients must
specify the destination by the `zmq.IDENTITY` of the `ROUTER` socket connected to
the downstream end of the device.

At the Kernel level, both of these `ROUTER` sockets are treated in the same way as the `REP`
socket in the serial version (except using ZMQStreams instead of explicit sockets).

Execution can be done in a load-balanced (engine-agnostic) or multiplexed (engine-specified)
manner. The sockets on the Client and Engine are the same for these two actions, but the
scheduler used determines the actual behavior. This routing is done via the `zmq.IDENTITY` of
the upstream sockets in each MonitoredQueue.

### IOPub

```{figure} figs/iopubfade.png
:align: center
:alt: IOPub connections
:width: 432px

stdout/err are published via a `PUB/SUB` MonitoredQueue
```

On the kernels, stdout/stderr are captured and published via a `PUB` socket. These `PUB`
sockets all connect to a `SUB` socket input of a MonitoredQueue, which subscribes to all
messages. They are then republished via another `PUB` socket, which can be
subscribed by the clients.

### Client connections

```{figure} figs/queryfade.png
:align: center
:alt: IPython client query connections
:width: 432px

Clients connect to an `ROUTER` socket to query the hub.
```

The hub's registrar `ROUTER` socket also listens for queries from clients as to queue status,
and control instructions. Clients connect to this socket via an `DEALER` during registration.

```{figure} figs/notiffade.png
:align: center
:alt: IPython Registration connections
:width: 432px

Engine registration events are published via a `PUB` socket.
```

The Hub publishes all registration/unregistration events via a `PUB` socket. This
allows clients to stay up to date with what engines are available by subscribing to the
feed with a `SUB` socket. Other processes could selectively subscribe to just
registration or unregistration events.
