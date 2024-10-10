import zmq

from util.socket import Socket
from util.util import LOCAL_PORT


class EvaluatorSocket(Socket):
    def __init__(self, endpoint=f"tcp://*:{LOCAL_PORT}"):
        super().__init__(zmq.REP)
        self.socket.bind(endpoint)
