import json
import logging

from yao import garblerSocket
from util.util import write_to_file, copy_and_expand_list
from yao import ot
from yao.yaoGarbler import YaoGarbler


class Alice(YaoGarbler):
    """Alice is the creator of the Yao circuit.

    Alice creates a Yao circuit and sends it to the evaluator along with her
    encrypted inputs. Alice will finally print the truth table of the circuit
    for all combination of Alice-Bob inputs.

    Alice does not know Bob's inputs but for the purpose
    of printing the truth table only, Alice assumes that Bob's inputs follow
    a specific order.

    Attributes:
        oblivious_transfer: Optional; enable the Oblivious Transfer protocol
            (True by default).
    """

    def __init__(self, oblivious_transfer=True):
        self.inputs, self.max_bit_length, self.input_length = [], 0, 0
        self.socket = garblerSocket.GarblerSocket()
        super().__init__(None)
        self.ot = ot.ObliviousTransfer(self.socket, enabled=oblivious_transfer)

    def read_inputs(self, input_list):
        """
        Simple method to read the input from a given list
        Args:
            input_list: the list of inputs
        """
        self.inputs = input_list

    def exchange_max_bit_length_and_number_of_inputs(self, input_length, max_bit_length):
        """
        Method used by alice and bob to agree on the size of the inputs and its bit-length representation,
        it useful to not reveal to each other any information about the inputs

        Args:
            input_length: the input length that alice will communicate to bob, that she wants to use
            max_bit_length: the maximum bit length to represent integers that alice will communicate to bob,
                            that she wants to use

        Returns:
            the final lengths used in the communication that both parties have agreed upon
        """
        print(f"For alice at the beginning input_length is: {str(input_length)} "
              f"and alice bit_length is: {str(max_bit_length)}")

        lengths = self.socket.send_wait(
            {"preliminary_data": {"input_length": input_length, "bit_length": max_bit_length}}
        )

        self.input_length = lengths.get("input_length")  # final agreed input length

        self.max_bit_length = lengths.get("bit_length")  # final agreed bit length used to represent integers

        print(f"Alice and bob agree to use as input_length: {str(self.input_length)}"
              f" and as bit_length: {str(self.max_bit_length)}")

        return self.inputs, self.max_bit_length

    def send_preliminary_information(self):
        """
        Method used to send to bob some preliminary information useful to perform the oblivious transfer, such as:
        the circuit, the garbled tables(made from the circuit) and the number of the output gates of the circuit

        Returns:
            the dictionary that alice sends to bob in order to set up the Oblivious Transfer correctly
        """
        for circuit in self.circuits:
            to_send = {
                "circuit": circuit["circuit"],
                "garbled_tables": circuit["garbled_tables"],
                "pbits_out": circuit["pbits_out"],
            }
            logging.debug(f"Sending {circuit['circuit']['id']}")
            self.socket.send_wait(to_send)
            return to_send

    def compute_function(self):
        """
        Method to compute the shared function, the max

        Returns:
            the meaningful results of the Oblivious Transfer, regarding alice and also bob
        """
        self.inputs = copy_and_expand_list(self.inputs, self.input_length)

        for entry in self.circuits:
            circuit, pbits, keys = entry["circuit"], entry["pbits"], entry["keys"]
            outputs = circuit["out"]
            a_wires = circuit.get("alice", [])  # Alice's wires
            a_inputs = {}  # map from Alice's wires to (key, encr_bit) inputs
            b_wires = circuit.get("bob", [])  # Bob's wires
            b_keys = {  # map from Bob's wires to a pair (key, encr_bit)
                w: self._get_encr_bits(pbits[w], key0, key1)
                for w, (key0, key1) in keys.items() if w in b_wires
            }

            bits_a = []

            # Generate all inputs for both Alice and Bob
            for value in self.inputs:
                bits_value = [int(i) for i in bin(value)[2:]]  # Alice's inputs
                if len(bits_value) < self.max_bit_length:
                    for i in range(self.max_bit_length - len(bits_value)):
                        bits_value.insert(0, 0)
                bits_a.extend(bits_value)

            # Map Alice's wires to (key, encr_bit)
            for i in range(len(a_wires)):
                a_inputs[a_wires[i]] = (keys[a_wires[i]][bits_a[i]],
                                        pbits[a_wires[i]] ^ bits_a[i])

            # Send Alice's encrypted inputs and keys to Bob
            result = self.ot.get_result(a_inputs, b_keys)

            return a_wires, bits_a, b_wires, b_keys, outputs, result

    def _get_encr_bits(self, pbit, key0, key1):
        return (key0, 0 ^ pbit), (key1, 1 ^ pbit)

    def create_max_cicruit(self):
        """
        Method to create the max circuit and prepare it to be stored in a readable json format

        Returns:
            the final max circuit as a dictionary and also stores it in a JSON file inside circuits folder,
            named total_circuit.json
        """
        # Initialize input and bit lengths
        input_set_length = self.input_length  # Number of inputs
        bit_rep_length = self.max_bit_length  # Bit representation length for each input
        circuit = {"name": "max_circuit", "circuits": [{}]}  # Initial structure of the circuit

        # Prepare inputs for Alice and Bob
        alice = [i for i in range(1, input_set_length * bit_rep_length + 1)]  # alice input gates from 1 to n where n is input_set_length * bit_rep_length + 1
        bob = [i for i in range(input_set_length * bit_rep_length + 1, input_set_length * bit_rep_length * 2 + 1)]  # bob input gates from alice last gate number up to input_set_length * bit_rep_length * 2 + 1
        index = input_set_length * bit_rep_length * 2 + 1  # Initial index for gate IDs

        # Create initial greater circuit comparison between first segments of Alice's and Bob's inputs
        gates, outputs = self.greater_circuit(alice[:bit_rep_length],
                                              bob[:bit_rep_length],
                                              0,
                                              [],
                                              index)
        # Update Alice and Bob input lists by removing the compared segment
        alice = alice[bit_rep_length:]
        bob = bob[bit_rep_length:]

        index = outputs[-1] + 1  # Update index for next set of gates

        # Iterate over remaining Alice's inputs
        while len(alice) > 0:
            a_inputs = alice[:bit_rep_length]  # Get next segment of Alice's inputs
            gates_list, outputs = self.greater_circuit(a_inputs, outputs, 0, [], index)  # Compare with current outputs

            gates.extend(gates_list)  # Add new gates to the main gate list
            index = outputs[-1] + 1  # Update index
            alice = alice[bit_rep_length:]  # Update Alice's input list removing the just compared segment

        #  Iterate over remaining Bob's inputs
        while len(bob) > 0:
            b_inputs = bob[:bit_rep_length]  # Get next segment of Bob's inputs
            gates_list, outputs = self.greater_circuit(b_inputs, outputs, 0, [], index)  # Compare with current outputs

            gates.extend(gates_list)  # Add new gates to the main gate list
            index = outputs[-1] + 1  # Update index
            bob = bob[bit_rep_length:]  # Update Bob's input list

        #  Finalize circuit dictionary with ids, inputs, outputs, and gates
        circuit["circuits"][0]["id"] = "max_value"  # Set ID for the circuit
        circuit["circuits"][0]["alice"] = [i for i in range(1, input_set_length * bit_rep_length + 1)]
        circuit["circuits"][0]["bob"] = [i for i in range(input_set_length * bit_rep_length + 1,
                                                          input_set_length * bit_rep_length * 2 + 1)]
        circuit["circuits"][0]["out"] = outputs
        circuit["circuits"][0]["gates"] = gates

        # Convert circuit dictionary to JSON string
        circuit_string = str(circuit).replace("'", '"')

        # Write JSON string to file
        json_path = 'circuits/total_circuit.json'
        parsed_circuit = json.loads(circuit_string)
        parsed_circuit = json.dumps(parsed_circuit, indent=4, separators=(', ', ': ')) + "\n"  # Format the string
        write_to_file(json_path, parsed_circuit)

        # Update circuits using superclass method
        super().update_circuits(circuit)

        return circuit

    def greater_circuit(self, first_number, second_number, input_slider, all_gates, index, partial_output=None,
                        carry_compared_gate=None):
        """
        This method creates a single comparator circuit that gives in output the greater number between the
        two compared bit-by-bit. It is a recursive procedure, that can create the comparator for any generic n bit
        unsigned pair of binary numbers.
        Args:
            first_number: first binary number, represented as a list gate indexes
            second_number: second binary number, represented as a list of gate indexes
            input_slider: index to scroll the two lists
            all_gates: all the gates created in this procedure for a single comparator of two n-bit numbers,
                       it starts always as an empty list
            index: progressive index, for the gate IDs, gets update every time a new gate is created
            partial_output: the OR gate before adding the multiplexer to choose the correct number
            carry_compared_gate: the intermediate AND of the various XNOR gates in the circuit

        Returns:
            the circuit with all the gates and the list of the multiplexer output i.e. the chosen
            greater number, that will be the next input for the next comparator in the procedure
            create_max_circuit, until all alice and bob inputs are compared
        """

        # Base case: if input_slider is at the last bit position
        if input_slider == len(first_number) - 1:
            not_index = index
            a0 = first_number[input_slider]  # Current bit from first_number
            b0 = second_number[input_slider]  # Current bit from second_number

            # Create a NOT gate for the current bit of second_number
            all_gates.append({"id": not_index, "type": "NOT", "in": [b0]})
            index += 1

            # Create an AND gate with the current bit of first_number and the NOT gate output
            and_gate = {"id": index, "type": "AND", "in": [a0, not_index]}
            all_gates.append(and_gate)
            and_index = index
            index += 1

            if carry_compared_gate is None:
                final_outputs = [and_gate.get("id")]
            else:
                # If there is the carried gate to AND then create a "final" AND gate with the previous AND gate
                # and carry_compared_gate
                final_and_gate = {"id": index, "type": "AND", "in": [and_index, carry_compared_gate.get("id")]}
                final_and_gate_index = index
                all_gates.append(final_and_gate)

                # Create an OR gate with the "final" AND gate and partial_output
                index += 1
                partial_output = {"id": index, "type": "OR", "in": [final_and_gate_index, partial_output.get("id")]}
                all_gates.append(partial_output)
                index += 1

                # Use multiplexer_circuit to finalize outputs
                final_outputs = self.multiplexer_circuit(first_number, second_number, index, partial_output, all_gates)

            return all_gates, final_outputs
        else:
            # Recursive case: it's not the last bit position: process the current bits and recurse
            not_index = index
            a0 = first_number[input_slider]  # Current bit from first_number
            b0 = second_number[input_slider]  # Current bit from second_number
            input_slider += 1

            # Create a NOT gate for the current bit of second_number
            all_gates.append({"id": not_index, "type": "NOT", "in": [b0]})
            index += 1

            # Create an AND gate with the current bit of first_number and the NOT gate output
            and_gate = {"id": index, "type": "AND", "in": [a0, not_index]}
            all_gates.append(and_gate)
            index += 1

            # Create an XNOR gate for the current bits of first_number and second_number
            xnor_gate = {"id": index, "type": "XNOR", "in": [a0, b0]}
            all_gates.append(xnor_gate)
            index += 1

            if carry_compared_gate is None:
                # Initialize partial_output and carry_compared_gate for the first comparison
                partial_output = and_gate
                carry_compared_gate = xnor_gate
            else:
                # Create a partial AND gate with the current AND gate and carry_compared_gate
                partial_and_gate = {"id": index, "type": "AND",
                                    "in": [and_gate.get("id"), carry_compared_gate.get("id")]}
                partial_and_gate_index = index
                all_gates.append(partial_and_gate)

                # Create an OR gate with the partial AND gate and partial_output
                index += 1
                partial_output = {"id": index, "type": "OR", "in": [partial_and_gate_index, partial_output.get("id")]}
                all_gates.append(partial_output)

                # Create a progressive carry AND gate with the current XNOR gate and carry_compared_gate
                index += 1
                carry_compared_gate = {"id": index, "type": "AND",
                                       "in": [xnor_gate.get("id"), carry_compared_gate.get("id")]}
                all_gates.append(carry_compared_gate)
                index += 1

            # Recursive call to process the next bits
            return self.greater_circuit(
                first_number,
                second_number,
                input_slider,
                all_gates,
                index,
                partial_output,
                carry_compared_gate
            )

    def multiplexer_circuit(self, first_number, second_number, index, partial_output, all_gates):
        """
        The multiplexer_circuit is called to finalize the outputs of the greater_circuit by multiplexing
        the comparison result into the final output gates. It creates a n-bit multiplexer circuit, that, based
        on the final OR gate result of the greater circuit, chooses the correct greater number
        Args:
            first_number: the first number that can be chosen
            second_number: the second number that can be chosen
            index: progressive index, for the gate IDs, gets update every time a new gate is created
            partial_output: the OR gate before adding the multiplexer to choose the correct number
            all_gates: list of all the gates of the circuit

        Returns:
            a list containing the final n indexes of OR gates that represent the chosen greater number
        """

        # List to hold AND gates created for first_number
        first_ands = []
        for gate in first_number:
            # Create an AND gate with the partial output and each gate from first_number
            first_ands.append({"id": index, "type": "AND", "in": [partial_output.get("id"), gate]})
            index += 1
        all_gates.extend(first_ands)

        # Create a NOT gate for the partial output
        not_partial_output_gate = {"id": index, "type": "NOT", "in": [partial_output.get("id")]}
        # List to hold AND gates created for second_number
        second_ands = []
        all_gates.append(not_partial_output_gate)
        index += 1
        for gate in second_number:
            # Create an AND gate with the NOT gate of partial output and each gate from second_number
            second_ands.append({"id": index, "type": "AND", "in": [not_partial_output_gate.get("id"), gate]})
            index += 1
        all_gates.extend(second_ands)

        # List to hold the final output gates
        final_outputs = []
        for first_ands, second_ands in zip(first_ands, second_ands):
            all_gates.append({"id": index, "type": "OR", "in": [first_ands.get("id"), second_ands.get("id")]})
            final_outputs.append(index)
            index += 1

        return final_outputs
