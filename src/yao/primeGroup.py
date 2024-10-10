import random

import sympy

from util.util import gen_prime, PRIME_BITS


class PrimeGroup:
    """Cyclic abelian group of prime order 'prime'."""
    def __init__(self, prime=None):
        self.prime = prime or gen_prime(num_bits=PRIME_BITS)
        self.prime_m1 = self.prime - 1
        self.prime_m2 = self.prime - 2
        self.generator = self.find_generator()

    def mul(self, num1, num2):
        "Multiply two elements." ""
        return (num1 * num2) % self.prime

    def pow(self, base, exponent):
        "Compute nth power of an element." ""
        return pow(base, exponent, self.prime)

    def gen_pow(self, exponent):  # generator exponentiation
        "Compute nth power of a generator." ""
        return pow(self.generator, exponent, self.prime)

    def inv(self, num):
        "Multiplicative inverse of an element." ""
        return pow(num, self.prime_m2, self.prime)

    def rand_int(self):  # random int in [1, prime-1]
        "Return an random int in [1, prime - 1]." ""
        return random.randint(1, self.prime_m1)

    def find_generator(self):  # find random generator for group
        """Find a random generator for the group."""
        factors = sympy.primefactors(self.prime_m1)

        while True:
            candidate = self.rand_int()
            for factor in factors:
                if 1 == self.pow(candidate, self.prime_m1 // factor):
                    break
            else:
                return candidate
