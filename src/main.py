# DO NOT MOVE THIS SCRIPT, IT MUST BE INSIDE THE FOLDER ./src
import json
import random
from multiprocessing import Process

from alice import Alice
from bob import Bob
from util.util import read_input, write_to_file


def main(party):
    """
    This is the method that controls the flow of the protocol:
    - alice inputs and bob inputs get read
    - alice and bob agree on how many input they will send and how to represent these
    - alice, the garbler, sends to bob all the necessary information for the Oblivious Transfer
    - the Oblivious Transfer takes place
    - the result of the Oblivious Transfer gets checked
    Args:
        party: depending on the party on which this main is executed one branch or the other are executed:
               one for alice and the other for bob, in fact this same main gets called twice
    """
    alice_input = read_input('resources/Alice.txt')
    alice_input_length = len(alice_input)
    alice_max_bit_length = len(bin(max(alice_input))[2:])
    random_integer = random.randint(1, alice_input_length)
    alice_input_length = alice_input_length * random_integer  # this adds randomness so that bob doesn't know alice's input cardinality

    bob_input = read_input('resources/Bob.txt')
    bob_input_length = len(bob_input)
    bob_max_bit_length = len(bin(max(bob_input))[2:])
    random_integer = random.randint(1, bob_input_length)
    bob_input_length = bob_input_length * random_integer

    if party == 'alice':
        alice = Alice(oblivious_transfer=True)

        alice.exchange_max_bit_length_and_number_of_inputs(alice_input_length, alice_max_bit_length)
        print_alice_to_bob(alice)
        alice_bob_ot(alice)
        result = alice_mpc_compute(alice, alice_input)
        verify_output(result, alice_input, bob_input)
        print("The ot is executed and logged into the file ot_intermediate_outputs.txt")

    elif party == 'bob':
        bob = Bob(oblivious_transfer=True)

        bob.exchange_max_bit_length_and_number_of_inputs(bob_input_length, bob_max_bit_length)
        alice_bob_ot(bob)
        result = bob_mpc_compute(bob, bob_input)
        print(f"For Bob the max computed is {result}")

    else:
        print("Error: give as argument alice or bob")


def print_alice_to_bob(alice):
    """
    This function prints the necessary output from Alice that she wants to send to Bob.
    Alice prints this preliminary output in the file alice_preliminary_outputs.txt
    The output format and how to read it are described in the report document.
    Args:
        alice: the garbler that sends to bob the preliminary information
    """
    circuit = alice.create_max_cicruit()
    print(f"Alice creates the circuit {circuit.get('name')} and sends it to bob")
    info = alice.send_preliminary_information()
    print(f"Alice sends to bob some initial info to bob before the ot takes place, "
          f"these are stored in the file alice_preliminary_outputs.txt")
    alice_inputs = f"Alice inputs are: {str(info.get('circuit').get('alice'))} \n"
    bob_inputs = f"Bob inputs are: {str(info.get('circuit').get('bob'))} \n"
    circuit = info.get("circuit")
    parsed_gates = json.loads(str(circuit.get("gates")).replace("'", '"'))
    parsed_gates = f"The gates of the circuit are: \n {json.dumps(parsed_gates, indent=4)} \n"

    garbled_tables = "garbled_tables = {\n"
    for key, elements in info.get("garbled_tables").items():
        garbled_tables += f'    "{key}": \n'
        for e in elements.items():
            garbled_tables += f'    "{e}",\n'
        garbled_tables += "}\n"

    garbled_tables = f"The garbled tables are: \n {garbled_tables} \n"

    output_gates = f"The outputs gates are: {str(info.get('circuit').get('out'))} \n"
    write_to_file(
        'outputs/alice_preliminary_outputs.txt',
        alice_inputs + bob_inputs + parsed_gates + garbled_tables + output_gates)


def alice_bob_ot(party):
    """
    This function logs the oblivious transfer's intermediate outputs into the file ./outputs/ot_intermediate_results.txt
    Args:
        party: each of the party that communicates to the ot to log the Oblivious Transfer
    """
    party.ot.start_logging()


def bob_mpc_compute(bob, bob_inputs):
    """
    This function prints the output of the function that Bob computes on the combined data and stores it in the file
    named final_result.txt, the function computed is the max function
    Args:
        bob: is the evaluator in the Oblivious Transfer
        bob_inputs: the list of integers read from the file ./resources/Bob.txt

    Returns:
        a dictionary mapping the output gate of the circuit to the corresponding bits of the result computed
    """
    bob.read_inputs(bob_inputs)
    result = bob.listen()
    return result


def alice_mpc_compute(alice, alice_input):
    """
    This function involves alice in the computing of the max function
    Args:
        alice: the garbler in the Oblivious Transfer
        alice_input: the list of integers read from the file ./resources/Alice.txt

    Returns:
        a dictionary mapping the output gate of the circuit to the corresponding bits of the result computed
    """
    alice.read_inputs(alice_input)
    a_wires, bits_a, b_wires, b_keys, outputs, result = alice.compute_function()
    return result


def verify_output(result, alice_input, bob_input):
    """
    This function verifies whether the output from alice_mpc_compute is same as the output
    from the max function computed non-multiparty way and writes 1 or 0 in the file ./outputs/final_result.txt
    depending on the success of the verification(1) or its failure(0)
    Args:
        result: the result of the multiparty computation of the max function
        alice_input: the list of integers read from the file Alice.txt
        bob_input: the list of integers read from the file Bob.txt
    """
    result = int(''.join(str(digit) for digit in result.values()), 2)
    alice_max = max(alice_input)
    bob_max = max(bob_input)
    final_max = max(alice_max, bob_max)
    if result == final_max:
        res = f"The evaluation was correct, {result} equals {final_max}"
        write_to_file("outputs/final_result.txt", str(1))
    else:
        res = f"The evaluation was not correct, {result} doesn't equal {final_max}"
        write_to_file("outputs/final_result.txt", str(0))

    print(res)
    print("This final result has been stored in the file final_result.txt")


if __name__ == '__main__':
    process_1 = Process(target=main, args=('alice',))
    process_1.start()
    process_2 = Process(target=main, args=('bob',))
    process_2.start()
    process_1.join(60)
    process_2.join(60)
    process_1.terminate()
    process_2.terminate()
