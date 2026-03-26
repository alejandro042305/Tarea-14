# ram.py – Memoria RAM Von Neumann (256 bytes)
# CORRECCIÓN: Sin cambios, este módulo estaba correcto.
from typing import List


class RAM:
    def __init__(self, size: int = 256):
        self.size = size
        self._memory = ["00000000"] * size

    def read(self, addr: int) -> str:
        if not (0 <= addr < self.size):
            raise IndexError(f"Dirección {addr} fuera de rango [0, {self.size-1}]")
        return self._memory[addr]

    def write(self, addr: int, value: str) -> None:
        if not (0 <= addr < self.size):
            raise IndexError(f"Dirección {addr} fuera de rango")
        if len(value) != 8 or not all(c in "01" for c in value):
            raise ValueError(f"Valor inválido (debe ser 8 bits binarios): {value}")
        self._memory[addr] = value

    def read_block(self, start: int, length: int) -> List[str]:
        return [self.read(start + i) for i in range(length)]

    def write_block(self, start: int, values: List[str]) -> None:
        for i, v in enumerate(values):
            self.write(start + i, v)

    def read_bit(self, addr: int, bit_pos: int) -> int:
        byte = self.read(addr)
        return int(byte[7 - bit_pos])

    def write_bit(self, addr: int, bit_pos: int, value: int) -> None:
        byte = list(self.read(addr))
        byte[7 - bit_pos] = str(value & 1)
        self.write(addr, "".join(byte))

    def show(self, start: int = 0, count: int = 16) -> None:
        end = min(start + count, self.size)
        for addr in range(start, end):
            print(f"{addr:04d}: {self.read(addr)}")