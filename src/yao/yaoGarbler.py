from abc import ABC

from util.util import parse_json

from yao import garbledCircuit


class YaoGarbler(ABC):
    """An abstract class for Yao garblers (e.g. Alice)."""
    def __init__(self, circuits):
        self.circuits = []
        if circuits is not None:
            circuits = parse_json(circuits)
            self.name = circuits["name"]

            for circuit in circuits["circuits"]:
                garbled_circuit = garbledCircuit.GarbledCircuit(circuit)
                pbits = garbled_circuit.get_pbits()
                entry = {
                    "circuit": circuit,
                    "garbled_circuit": garbled_circuit,
                    "garbled_tables": garbled_circuit.get_garbled_tables(),
                    "keys": garbled_circuit.get_keys(),
                    "pbits": pbits,
                    "pbits_out": {w: pbits[w]
                                  for w in circuit["out"]},
                }
                self.circuits.append(entry)

    def update_circuits(self, circuits):
        """
        Simple method to add elements to the circuit list of the garbler
        Args:
            circuits: the circuits to add to the circuits list
        """
        if circuits is not None:
            for circuit in circuits["circuits"]:
                garbled_circuit = garbledCircuit.GarbledCircuit(circuit)
                pbits = garbled_circuit.get_pbits()
                entry = {
                    "circuit": circuit,
                    "garbled_circuit": garbled_circuit,
                    "garbled_tables": garbled_circuit.get_garbled_tables(),
                    "keys": garbled_circuit.get_keys(),
                    "pbits": pbits,
                    "pbits_out": {w: pbits[w]
                                  for w in circuit["out"]},
                }
                self.circuits.append(entry)
