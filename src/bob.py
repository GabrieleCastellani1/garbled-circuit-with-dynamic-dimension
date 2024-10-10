import logging

from yao import evaluatorSocket
from util.util import copy_and_expand_list
from yao import ot


class Bob:
    """Bob is the receiver and evaluator of the Yao circuit.

    Bob receives the Yao circuit from Alice, computes the results and sends
    them back.

    Args:
        oblivious_transfer: Optional; enable the Oblivious Transfer protocol
            (True by default).
    """

    def __init__(self, oblivious_transfer=True):
        self.inputs, self.max_bit_length, self.input_length = [], 0, 0
        self.socket = evaluatorSocket.EvaluatorSocket()

        self.ot = ot.ObliviousTransfer(self.socket, enabled=oblivious_transfer)

    def read_inputs(self, input_list):
        """
        simple method to read the input from a given list
        Args:
            input_list: the list of inputs
        """
        self.inputs = input_list

    def exchange_max_bit_length_and_number_of_inputs(self, input_length, max_bit_length):
        """
        Method used by alice and bob to agree on the size of the inputs and its bit-length representation,
        it useful to not reveal to each other any information about the inputs
        Args:
            input_length: the input length that bob will communicate to alice if it's greater than the alice's
                          input_length received
            max_bit_length: the maximum bit length to represent integers that bob will communicate to alice,
                            if it's greater than the alice's max_bit_length received
        """
        # Receive preliminary data from the socket from alice
        entry = self.socket.receive()

        print("For bob at the beginning input_length is: " + str(input_length) +
              " and bob bit_length is: " + str(max_bit_length))

        # Check if the received entry contains preliminary data
        if entry.get("preliminary_data") is not None:
            # Extract the input length and bit length from the received preliminary data
            communication_input_length = entry["preliminary_data"].get("input_length")
            communication_bit_length = entry["preliminary_data"].get("bit_length")

            if communication_input_length <= input_length:
                # If Bob's input length is greater or equal, use Bob's input length
                communication_input_length = input_length
                self.input_length = input_length
            else:
                # Otherwise, use Alice's received input length
                self.input_length = communication_input_length

            if communication_bit_length <= max_bit_length:
                # If Bob's bit length is greater or equal, use Bob's bit length
                communication_bit_length = max_bit_length
                self.max_bit_length = max_bit_length
            else:
                # Otherwise, use Alice's received bit length
                self.max_bit_length = communication_bit_length

            # Send the agreed upon input length and bit length back to Alice
            self.socket.send(
                {"input_length": communication_input_length, "bit_length": communication_bit_length})

    def listen(self):
        """
        Start listening for Alice messages.
        Returns:
            the result of the multiparty computation of the max, obtained with the Oblivious Transfer
        """
        logging.info("Start listening")
        try:
            for entry in self.socket.poll_socket():
                self.socket.send(True)
                b_wires, bits_b, result = self.send_evaluation(entry)

                return result

        except KeyboardInterrupt:
            logging.info("Stop listening")

    def send_evaluation(self, entry):
        """Evaluate yao circuit for all Bob and Alice's inputs and
        send back the results.

        Args:
            entry: A dict representing the circuit to evaluate.
        """
        self.inputs = copy_and_expand_list(self.inputs, self.input_length)

        circuit, pbits_out = entry["circuit"], entry["pbits_out"]
        garbled_tables = entry["garbled_tables"]
        a_wires = circuit.get("alice", [])  # list of Alice's wires
        b_wires = circuit.get("bob", [])  # list of Bob's wires

        # Generate all possible inputs for both Alice and Bob
        bits_b = []
        for value in self.inputs:
            bits_value = [int(i) for i in bin(value)[2:]]  # Alice's inputs
            if len(bits_value) < self.max_bit_length:
                for i in range(self.max_bit_length - len(bits_value)):
                    bits_value.insert(0, 0)
            bits_b.extend(bits_value)

        # Create dict mapping each wire of Bob to Bob's input
        b_inputs_clear = {
            b_wires[i]: bits_b[i]
            for i in range(len(b_wires))
        }

        # Evaluate and send result to Alice
        result = self.ot.send_result(circuit, garbled_tables, pbits_out, b_inputs_clear)

        return b_wires, bits_b, result
