from typing import Dict, Any

from ram import RAM
from registers import Registers
from instructions import instr_dict, decode_params, Params


# Mapa de prefijo (2 bits altos del primer byte) → longitud total en BYTES
PREFIX_TO_BYTES: Dict[str, int] = {
    "00": 1,
    "01": 2,
    "10": 4,
    "11": 8,
}


class CPUCore:

    def __init__(self, ram: RAM, regs: Registers):

        self.ram = ram
        self.regs = regs

        # ← CORRECCIÓN IMPORTANTE
        self.halted = False


    # ─────────────────────────────────────────
    # FETCH
    # ─────────────────────────────────────────

    def fetch(self) -> str:

        pc = self.regs.PC

        first_byte = self.ram.read(pc)

        prefix = first_byte[:2]

        instr_bytes = PREFIX_TO_BYTES.get(prefix, 1)

        bits_list = [first_byte]

        for i in range(1, instr_bytes):
            bits_list.append(self.ram.read(pc + i))

        instr_bits = "".join(bits_list)

        self.regs.increment_PC(instr_bytes)

        self.regs.IR = instr_bits

        return instr_bits


    # ─────────────────────────────────────────
    # DECODE
    # ─────────────────────────────────────────

    def decode(self, instr_bits: str) -> Dict[str, Any]:

        opcode_bits = None
        func = None
        param_type = None

        for key, (f, knd) in instr_dict.items():

            if instr_bits.startswith(key):

                if opcode_bits is None or len(key) > len(opcode_bits):

                    opcode_bits = key
                    func = f
                    param_type = knd

        if opcode_bits is None:
            raise ValueError(
                f"Opcode desconocido. PC={self.regs.PC}, IR={instr_bits!r}"
            )

        params_raw = instr_bits[len(opcode_bits):]

        return {
            "opcode_bits": opcode_bits,
            "function": func,
            "param_type": param_type,
            "params_raw": params_raw,
        }


    # ─────────────────────────────────────────
    # STEP
    # ─────────────────────────────────────────

    def step(self):

        if self.halted:
            return

        instr_bits = self.fetch()

        decoded = self.decode(instr_bits)

        params: Params = decode_params(
            decoded["param_type"],
            decoded["params_raw"]
        )

        decoded["function"](self, self.regs, self.ram, params)

        return decoded


    # ─────────────────────────────────────────
    # RUN
    # ─────────────────────────────────────────

    def run(self, max_cycles=1000):

        cycles = 0

        while not self.halted and cycles < max_cycles:

            pc = self.regs.PC

            if pc >= self.ram.size:
                print("Fin de memoria alcanzado")
                break

            self.step()
            cycles += 1


    # ─────────────────────────────────────────
    # RESET
    # ─────────────────────────────────────────

    def reset(self):

        self.regs.reset()

        self.halted = False