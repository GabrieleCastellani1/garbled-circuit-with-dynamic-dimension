import json
import operator
import os
import random
import secrets

import sympy

# SOCKET
LOCAL_PORT = 4080
SERVER_HOST = "localhost"
SERVER_PORT = 4080

# PRIME GROUP
PRIME_BITS = 64  # order of magnitude of prime in base 2


def next_prime(num):
    """Return next prime after 'num' (skip 2)."""
    return 3 if num < 3 else sympy.nextprime(num)


def read_input(path):
    """
    Simple method to read from a given path a file containing some integers
    Args:
        path: the relative path to read the file from, the readable files must be stored in the resources folder
    Returns:
        a list containing the read numbers
    """
    # Open the file for reading
    base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    final_path = os.path.normpath(os.path.join(base_path, path))
    with open(final_path, 'r') as file:
        # Read the entire content of the file
        content = file.read()

    # Split the content by spaces and convert each part to an integer
    integers_list = [int(x) for x in content.split()]
    file.close()

    return integers_list


def write_to_file(path, content):
    """
    Simple method to write content in a file at the given path, if the file doesn't exist it is created
    Args:
        path: the relative path to write the file to, the files should be stored in the outputs folder
        content: the content to write to the file
    """
    try:
        # Open the file in write mode
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        final_path = os.path.normpath(os.path.join(base_path, path))
        with open(final_path, 'w') as file:
            # Check if the file is not empty
            if file.tell() != 0:
                # If the file is not empty, truncate it
                file.truncate(0)
            # Write the content to the file
            file.write(content)
            file.close()
    except Exception as e:
        print("An error occurred:", e)


def truncate_file(path):
    """
    Simple method to truncate an existing file
    Args:
        path: the path of the file to truncate, relative to the src folder
    """
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        final_path = os.path.normpath(os.path.join(base_path, path))
        with open(final_path, 'w') as file:
            # Check if the file is not empty
            if file.tell() != 0:
                # If the file is not empty, truncate it
                file.truncate(0)
            file.close()
    except FileNotFoundError:
        print(f"The ot intermediate outputs will be stored in the file ot_intermediate_outputs.txt")


def append_to_file(path, content):
    """
    Simple method to append content in a file at the given path
    Args:
        path: the file to append to, it is path relative to src
        content: the content to append
    """
    try:
        # Open the file in write mode
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        final_path = os.path.normpath(os.path.join(base_path, path))
        with open(final_path, 'a') as file:
            # Write the content to the file
            file.write(content)
            file.close()
    except Exception as e:
        print("An error occurred:", e)


def copy_and_expand_list(original_list, new_size):
    """
    Simple method to copy an existing list into a bigger list of a given size,
    fill the missing values with zeroes and, at the end, shuffle to mix the elements
    Args:
        original_list: the list to copy and expand
        new_size: the size of the new list that wil be created

    Returns:
        the new list
    """
    if new_size <= len(original_list):
        return original_list

    # Copy the original list
    new_list = original_list.copy()

    # Add zeros to the list until it reaches the desired size
    while len(new_list) < new_size:
        new_list.append(0)

    # Shuffle the list to mix zeros evenly with the other numbers
    random.shuffle(new_list)

    return new_list


def gen_prime(num_bits):
    """Return random prime of bit size 'num_bits'"""
    r = secrets.randbits(num_bits)
    return next_prime(r)


def xor_bytes(seq1, seq2):
    """XOR two byte sequence."""
    return bytes(map(operator.xor, seq1, seq2))


def bits(num, width):
    """Convert number into a list of bits."""
    return [int(k) for k in f'{num:0{width}b}']


# HELPER FUNCTIONS
def parse_json(json_path):
    with open(json_path) as json_file:
        return json.load(json_file)
