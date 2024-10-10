import zmq


class Socket:
    def __init__(self, socket_type):
        self.socket = zmq.Context().socket(socket_type)
        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def send(self, msg):
        self.socket.send_pyobj(msg)

    def receive(self):
        return self.socket.recv_pyobj()

    def send_wait(self, msg):
        self.send(msg)
        return self.receive()

    """
    From https://stackoverflow.com/questions/17174001/stop-pyzmq-receiver-by-keyboardinterrupt
    """

    def poll_socket(self, timetick=100):
        try:
            while True:
                obj = dict(self.poller.poll(timetick))
                if self.socket in obj and obj[self.socket] == zmq.POLLIN:
                    yield self.socket.recv_pyobj()
        except KeyboardInterrupt:
            pass
