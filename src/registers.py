# registers.py – Registros del CPU
# CORRECCIÓN: Sin cambios, este módulo estaba correcto.


class Registers:
    def __init__(self):
        self._regs = [0] * 8     # R0–R7
        self.PC = 0              # 48 bits
        self.SP = 255            # 48 bits (stack pointer, crece hacia abajo)
        self.IR = ""             # Instruction register (string binario)
        self.flag_Z = False      # Zero
        self.flag_C = False      # Carry
        self.flag_N = False      # Negative
        self.flag_V = False      # Overflow

    def get_reg(self, n: int) -> int:
        if not (0 <= n < 8):
            raise ValueError(f"Registro inválido: R{n}")
        return self._regs[n] & 0xFF

    def set_reg(self, n: int, value: int) -> None:
        if not (0 <= n < 8):
            raise ValueError(f"Registro inválido: R{n}")
        self._regs[n] = value & 0xFF

    def increment_PC(self, bytes_count: int) -> None:
        self.PC += bytes_count

    def push_SP(self, bytes_count: int) -> None:
        self.SP -= bytes_count

    def pop_SP(self, bytes_count: int) -> None:
        self.SP += bytes_count

    def update_flags(self, result_raw: int = 0, operand_a: int = 0,
                     operand_b: int = 0, operation: str = "add") -> None:
        result = result_raw & 0xFF

        self.flag_Z = (result == 0)
        self.flag_N = (result & 0x80) != 0

        if operation == "add":
            self.flag_C = result_raw > 0xFF
            self.flag_V = ((operand_a & 0x80) == (operand_b & 0x80)) and \
                          ((result & 0x80) != (operand_a & 0x80))
        elif operation == "sub":
            self.flag_C = result_raw < 0
            self.flag_V = ((operand_a & 0x80) != (operand_b & 0x80)) and \
                          ((result & 0x80) != (operand_a & 0x80))
        elif operation == "logic":
            self.flag_C = False
            self.flag_V = False

    def get_flags(self) -> str:
        return f"Z={int(self.flag_Z)} C={int(self.flag_C)} N={int(self.flag_N)} V={int(self.flag_V)}"

    def PC_bin(self) -> str:
        return format(self.PC, "048b")

    def SP_bin(self) -> str:
        return format(self.SP, "048b")

    def show(self) -> None:
        print("Registros Generales:")
        for i in range(8):
            print(f"  R{i} = {self._regs[i]:3d}  (bin: {format(self._regs[i], '08b')})")
        print(f"PC = {self.PC}  (bin: {self.PC_bin()})")
        print(f"SP = {self.SP}  (bin: {self.SP_bin()})")
        print(f"IR = {self.IR}")
        print(f"Banderas: {self.get_flags()}")

    def reset(self) -> None:
        self._regs = [0] * 8
        self.PC = 0
        self.SP = 255
        self.IR = ""
        self.flag_Z = self.flag_C = self.flag_N = self.flag_V = False