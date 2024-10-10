import zmq

from util.socket import Socket
from util.util import SERVER_HOST, SERVER_PORT


class GarblerSocket(Socket):
    def __init__(self, endpoint=f"tcp://{SERVER_HOST}:{SERVER_PORT}"):
        super().__init__(zmq.REQ)
        self.socket.connect(endpoint)
