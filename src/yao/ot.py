import hashlib
import logging
import pickle

from yao.primeGroup import PrimeGroup
from util import util
from util.util import append_to_file
from util.util import truncate_file

from yao import yao


class ObliviousTransfer:
    def __init__(self, socket, enabled=True):
        self.socket = socket
        self.enabled = enabled
        self.log_flag = False

    def get_result(self, a_inputs, b_keys):
        """Send Alice's inputs and retrieve Bob's result of evaluation.

        Args:
            a_inputs: A dict mapping Alice's wires to (key, encr_bit) inputs.
            b_keys: A dict mapping each Bob's wire to a pair (key, encr_bit).

        Returns:
            The result of the yao circuit evaluation.
        """
        logging.debug("Sending inputs to Bob")
        self.socket.send(a_inputs)

        for _ in range(len(b_keys)):
            w = self.socket.receive()  # receive gate ID where to perform OT
            logging.debug(f"Received gate ID {w}")

            if self.enabled:  # perform oblivious transfer
                pair = (pickle.dumps(b_keys[w][0]), pickle.dumps(b_keys[w][1]))
                self.ot_garbler(pair)
            else:
                to_send = (b_keys[w][0], b_keys[w][1])
                self.socket.send(to_send)
        return self.socket.receive()

    def send_result(self, circuit, g_tables, pbits_out, b_inputs):
        """Evaluate circuit and send the result to Alice.

        Args:
            circuit: A dict containing circuit spec.
            g_tables: Garbled tables of yao circuit.
            pbits_out: p-bits of outputs.
            b_inputs: A dict mapping Bob's wires to (clear) input bits.

        Returns:
            The result of the yao circuit evaluation.
        """
        # map from Alice's wires to (key, encr_bit) inputs
        a_inputs = self.socket.receive()
        # map from Bob's wires to (key, encr_bit) inputs
        b_inputs_encr = {}

        logging.debug("Received Alice's inputs")

        for w, b_input in b_inputs.items():
            logging.debug(f"Sending gate ID {w}")
            self.socket.send(w)

            if self.enabled:
                b_inputs_encr[w] = pickle.loads(self.ot_evaluator(b_input))
            else:
                pair = self.socket.receive()
                logging.debug(f"Received key pair, key {b_input} selected")
                b_inputs_encr[w] = pair[b_input]
        result = yao.evaluate(circuit, g_tables, pbits_out, a_inputs,
                              b_inputs_encr)

        logging.debug("Sending circuit evaluation")
        self.socket.send(result)
        return result

    def ot_garbler(self, msgs):
        """Oblivious transfer, Alice's side.

        Args:
            msgs: A pair (msg1, msg2) to suggest to Bob.
        """
        logging.debug("OT protocol started")
        G = PrimeGroup()
        self.socket.send_wait(G)

        # OT protocol based on Nigel Smart’s "Cryptography Made Simple"
        c = G.gen_pow(G.rand_int())
        h0 = self.socket.send_wait(c)
        h1 = G.mul(c, G.inv(h0))
        k = G.rand_int()
        c1 = G.gen_pow(k)
        e0 = util.xor_bytes(msgs[0], self.ot_hash(G.pow(h0, k), len(msgs[0])))
        e1 = util.xor_bytes(msgs[1], self.ot_hash(G.pow(h1, k), len(msgs[1])))

        self.log_ot("alice suggests to bob the message: " + str((c1, msgs[0], msgs[1])) + "\n")
        self.socket.send((c1, e0, e1))
        logging.debug("OT protocol ended")

    def ot_evaluator(self, b):
        """Oblivious transfer, Bob's side.

        Args:
            b: Bob's input bit used to select one of Alice's messages.

        Returns:
            The message selected by Bob.
        """
        logging.debug("OT protocol started")
        G = self.socket.receive()
        self.socket.send(True)

        # OT protocol based on Nigel Smart’s "Cryptography Made Simple"
        c = self.socket.receive()
        x = G.rand_int()
        x_pow = G.gen_pow(x)
        h = (x_pow, G.mul(c, G.inv(x_pow)))
        c1, e0, e1 = self.socket.send_wait(h[b])
        e = (e0, e1)
        ot_hash = self.ot_hash(G.pow(c1, x), len(e[b]))
        mb = util.xor_bytes(e[b], ot_hash)

        self.log_ot(f"bob, using the bit {str(b)}, chooses the message: {str(mb)} \n\n")
        logging.debug("OT protocol ended")
        return mb

    def start_logging(self):
        """
        Method used by alice and bob to communicate to the ot to start logging all the operations involved
        in the oblivious transfer and if there are previous results logged those are erased
        """
        if self.log_flag is not True:
            self.log_flag = True
            truncate_file('outputs/ot_intermediate_outputs.txt')

    def stop_logging(self):
        self.log_flag = False

    def log_ot(self, content):
        if self.log_flag:
            append_to_file('outputs/ot_intermediate_outputs.txt', content)

    @staticmethod
    def ot_hash(pub_key, msg_length):
        """Hash function for OT keys."""
        key_length = (pub_key.bit_length() + 7) // 8  # key length in bytes
        bytes = pub_key.to_bytes(key_length, byteorder="big")
        return hashlib.shake_256(bytes).digest(msg_length)
