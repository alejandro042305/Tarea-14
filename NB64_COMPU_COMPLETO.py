"""
╔══════════════════════════════════════════════════════════════════════════════╗
║                      SIMULADOR DE COMPUTADORA NB-64                          ║
║                    Arquitectura Von Neumann con Coprocesador FPU             ║
╚══════════════════════════════════════════════════════════════════════════════╝

PROYECTO INTEGRADO: Simulador completo de CPU de 8 bits con:
  • RAM de 256 bytes (memoria Von Neumann)
  • 8 registros de 8 bits (R0-R7)
  • Program Counter (PC) de 48 bits
  • Stack Pointer (SP) de 48 bits
  • Coprocesador FPU IEEE 754 (doble precisión)
  • Conjunto de 40+ instrucciones en 4 tamaños diferentes
  • Sistema de banderas de condición (Z, C, N, V)

TAMAÑOS DE INSTRUCCIONES:
  • 1 byte (Prefijo "00"): NOP, HALT, RET, IRET, FPU_OP
  • 2 bytes (Prefijo "01"): Operaciones registro-registro
  • 4 bytes (Prefijo "10"): MOVI (Cargar inmediato)
  • 8 bytes (Prefijo "11"): LOAD, STORE, Saltos, CALL (necesitan dirección 48-bit)

================================================================================
                          MÓDULO 1: MEMORIA RAM
================================================================================
"""

from typing import List, Dict, Tuple, Any, Optional, Callable
import struct
import math
from dataclasses import dataclass


# ═════════════════════════════════════════════════════════════════════════════
# MEMORIA RAM (256 bytes - Arquitectura Von Neumann)
# ═════════════════════════════════════════════════════════════════════════════

class RAM:
    """
    Memoria RAM Von Neumann con 256 bytes.
    
    Cada byte se almacena como string binario de 8 bits. La memoria es
    addressable por byte y soporta lectura/escritura tanto individual como
    por bloques.
    
    Direcciones especiales para coprocesador FPU:
      0xE0-0xE7: Operando A (float64)
      0xE8-0xEF: Operando B (float64)
      0xF0:      Código de operación FPU
      0xF1-0xF8: Resultado FPU
      0xF9:      Flags FPU
    """
    
    def __init__(self, size: int = 256):
        """Inicializa RAM con todos los bytes en 0."""
        self.size = size
        self._memory = ["00000000"] * size

    def read(self, addr: int) -> str:
        """Lee un byte (string binario de 8 bits) en la dirección especificada."""
        if not (0 <= addr < self.size):
            raise IndexError(f"Dirección {addr} fuera de rango [0, {self.size-1}]")
        return self._memory[addr]

    def write(self, addr: int, value: str) -> None:
        """Escribe un byte (string binario de 8 bits) en la dirección especificada."""
        if not (0 <= addr < self.size):
            raise IndexError(f"Dirección {addr} fuera de rango")
        if len(value) != 8 or not all(c in "01" for c in value):
            raise ValueError(f"Valor inválido (debe ser 8 bits binarios): {value}")
        self._memory[addr] = value

    def read_block(self, start: int, length: int) -> List[str]:
        """Lee múltiples bytes consecutivos."""
        return [self.read(start + i) for i in range(length)]

    def write_block(self, start: int, values: List[str]) -> None:
        """Escribe múltiples bytes consecutivos."""
        for i, v in enumerate(values):
            self.write(start + i, v)

    def read_bit(self, addr: int, bit_pos: int) -> int:
        """Lee un bit específico de un byte (bit_pos: 0-7)."""
        byte = self.read(addr)
        return int(byte[7 - bit_pos])

    def write_bit(self, addr: int, bit_pos: int, value: int) -> None:
        """Escribe un bit específico de un byte."""
        byte = list(self.read(addr))
        byte[7 - bit_pos] = str(value & 1)
        self.write(addr, "".join(byte))

    def show(self, start: int = 0, count: int = 16) -> None:
        """Muestra el contenido de RAM en formato legible."""
        end = min(start + count, self.size)
        for addr in range(start, end):
            print(f"{addr:04d}: {self.read(addr)}")


# ═════════════════════════════════════════════════════════════════════════════
# REGISTROS DEL CPU
# ═════════════════════════════════════════════════════════════════════════════

class Registers:
    """
    Registros del CPU NB-64:
    
    • R0-R7: 8 registros de 8 bits para datos generales
    • PC (Program Counter): 48 bits, apunta a la siguiente instrucción
    • SP (Stack Pointer): 48 bits, crece hacia abajo (inicia en 255)
    • IR (Instruction Register): almacena la instrucción actual en binario
    • Banderas:
      - Z (Zero): se activa si el resultado es 0
      - C (Carry): se activa si hay desbordamiento
      - N (Negative): se activa si el resultado es negativo (bit 7 = 1)
      - V (Overflow): se activa si hay desbordamiento de signo
    """
    
    def __init__(self):
        """Inicializa todos los registros a 0."""
        self._regs = [0] * 8     # R0–R7
        self.PC = 0              # 48 bits
        self.SP = 255            # 48 bits (stack pointer, crece hacia abajo)
        self.IR = ""             # Instruction register (string binario)
        self.flag_Z = False      # Zero
        self.flag_C = False      # Carry
        self.flag_N = False      # Negative
        self.flag_V = False      # Overflow

    def get_reg(self, n: int) -> int:
        """Obtiene el valor de un registro (0-7)."""
        if not (0 <= n < 8):
            raise ValueError(f"Registro inválido: R{n}")
        return self._regs[n] & 0xFF

    def set_reg(self, n: int, value: int) -> None:
        """Establece el valor de un registro (se enmascara a 8 bits)."""
        if not (0 <= n < 8):
            raise ValueError(f"Registro inválido: R{n}")
        self._regs[n] = value & 0xFF

    def increment_PC(self, bytes_count: int) -> None:
        """Incrementa el PC (used by fetch)."""
        self.PC += bytes_count

    def push_SP(self, bytes_count: int) -> None:
        """Decrementa el SP (crece hacia abajo en el stack)."""
        self.SP -= bytes_count

    def pop_SP(self, bytes_count: int) -> None:
        """Incrementa el SP (saca datos del stack)."""
        self.SP += bytes_count

    def update_flags(self, result_raw: int = 0, operand_a: int = 0,
                     operand_b: int = 0, operation: str = "add") -> None:
        """
        Actualiza las banderas basándose en el resultado de una operación.
        
        Banderas:
        • Z (Zero): result == 0
        • N (Negative): bit 7 del resultado == 1
        • C (Carry): depende de la operación (overflow/underflow)
        • V (Overflow): desbordamiento de signo
        """
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
        """Retorna una representación string de las banderas."""
        return f"Z={int(self.flag_Z)} C={int(self.flag_C)} N={int(self.flag_N)} V={int(self.flag_V)}"

    def PC_bin(self) -> str:
        """Retorna el PC en formato binario de 48 bits."""
        return format(self.PC, "048b")

    def SP_bin(self) -> str:
        """Retorna el SP en formato binario de 48 bits."""
        return format(self.SP, "048b")

    def show(self) -> None:
        """Muestra el estado actual de todos los registros."""
        print("Registros Generales:")
        for i in range(8):
            print(f"  R{i} = {self._regs[i]:3d}  (bin: {format(self._regs[i], '08b')})")
        print(f"PC = {self.PC}  (bin: {self.PC_bin()})")
        print(f"SP = {self.SP}  (bin: {self.SP_bin()})")
        print(f"IR = {self.IR}")
        print(f"Banderas: {self.get_flags()}")

    def reset(self) -> None:
        """Resetea todos los registros a sus valores iniciales."""
        self._regs = [0] * 8
        self.PC = 0
        self.SP = 255
        self.IR = ""
        self.flag_Z = self.flag_C = self.flag_N = self.flag_V = False


# ═════════════════════════════════════════════════════════════════════════════
# COPROCESADOR FPU (IEEE 754 Doble Precisión)
# ═════════════════════════════════════════════════════════════════════════════

class FPU:
    """
    Coprocesador FPU para operaciones de punto flotante IEEE 754 (doble precisión).
    
    PROTOCOLO EN RAM:
      RAM[0xE0..0xE7] = Operando A (float64, big-endian)
      RAM[0xE8..0xEF] = Operando B (float64, big-endian)
      RAM[0xF0]       = Código de operación FPU
      RAM[0xF1..0xF8] = Resultado
      RAM[0xF9]       = Flags FPU (bit0=Zero, bit1=A<B, bit2=NaN)
    
    OPERACIONES BÁSICAS:
      0x01 = FPU_ADD: A + B
      0x02 = FPU_SUB: A - B
      0x03 = FPU_MUL: A * B
      0x04 = FPU_DIV: A / B
      0x05 = FPU_SQRT: √A
      0x06 = FPU_CMP: Comparación
    
    OPERACIONES EXTENDIDAS:
      0x10 = HERON_STEP: √ usando método de Heron (1 iteración)
      0x20 = BRUN_ACCUMULATE: Constante de Brun (suma de inversos de primos gemelos)
    """
    
    # Pares de primos gemelos (para Constante de Brun)
    TWIN_PRIMES = [
        (3,5),(5,7),(11,13),(17,19),(29,31),
        (41,43),(59,61),(71,73),(101,103),(107,109)
    ]

    # Direcciones especiales en RAM para FPU
    FPU_A_ADDR     = 0xE0
    FPU_B_ADDR     = 0xE8
    FPU_OP_ADDR    = 0xF0
    FPU_R_ADDR     = 0xF1
    FPU_FLAGS_ADDR = 0xF9
    FPU_PARAM0     = 0xFA  # Parámetro 0 para operaciones extendidas
    FPU_PARAM1     = 0xFB  # Parámetro 1
    FPU_PARAM2     = 0xFC  # Parámetro 2

    # Códigos de operación
    FPU_ADD  = 0x01
    FPU_SUB  = 0x02
    FPU_MUL  = 0x03
    FPU_DIV  = 0x04
    FPU_SQRT = 0x05
    FPU_CMP  = 0x06
    FPU_HERON_STEP      = 0x10
    FPU_BRUN_ACCUMULATE = 0x20

    def __init__(self, ram: RAM):
        self.ram = ram

    def execute(self):
        """Ejecuta la operación FPU especificada en RAM[0xF0]."""
        op = int(self.ram.read(self.FPU_OP_ADDR), 2)
        if   op == self.FPU_HERON_STEP:      self._heron_step()
        elif op == self.FPU_BRUN_ACCUMULATE: self._brun_accumulate()
        else:                                self._basic(op)

    def _basic(self, op: int):
        """Ejecuta operaciones FPU básicas."""
        a = self._read_float(self.FPU_A_ADDR)
        b = self._read_float(self.FPU_B_ADDR)
        
        if   op == self.FPU_ADD:  r = a + b
        elif op == self.FPU_SUB:  r = a - b
        elif op == self.FPU_MUL:  r = a * b
        elif op == self.FPU_DIV:  r = (a/b) if b else math.copysign(math.inf, a)
        elif op == self.FPU_SQRT: r = math.sqrt(a) if a >= 0 else float('nan')
        elif op == self.FPU_CMP:  r = a - b
        else: raise ValueError(f"FPU op desconocida: {op:#04x}")
        
        self._write_float(self.FPU_R_ADDR, r)
        self._write_flags(r, a, b)

    def _heron_step(self):
        """
        Método de Heron para raíz cuadrada: y_new = (y + x/y) / 2
        
        Esta es una iteración completa. La fórmula converge rápidamente:
        - Iteración 1: y ≈ 11.25 (para √125)
        - Iteración 2: y ≈ 11.18056
        - Iteración 3: y ≈ 11.18034 (converge)
        
        RAM[0xFA] = dirección de x (float64)
        RAM[0xFB] = dirección de y (float64, se actualiza con la nueva aproximación)
        RAM[0xFC] = contador de iteraciones (se decrementa)
        """
        dx = int(self.ram.read(self.FPU_PARAM0), 2)
        dy = int(self.ram.read(self.FPU_PARAM1), 2)
        cnt = int(self.ram.read(self.FPU_PARAM2), 2)
        
        x = self._read_float(dx)
        y = self._read_float(dy)
        y_new = 0.5 * (y + x / y)
        
        self._write_float(dy, y_new)
        self._write_float(self.FPU_R_ADDR, y_new)
        self._write_flags(y_new, x, y)
        self.ram.write(self.FPU_PARAM2, format(max(0, cnt - 1), "08b"))

    def _brun_accumulate(self):
        """
        Constante de Brun: suma de 1/p + 1/q para pares de primos gemelos.
        
        B₂ = Σ(1/p + 1/q) ≈ 1.902160583104...
        
        Pares usados: (3,5), (5,7), (11,13), (17,19), (29,31), 
                      (41,43), (59,61), (71,73), (101,103), (107,109)
        
        RAM[0xFA] = número de pares a usar
        RAM[0xFB] = dirección del acumulador (float64, se actualiza)
        """
        n    = int(self.ram.read(self.FPU_PARAM0), 2)
        dacc = int(self.ram.read(self.FPU_PARAM1), 2)
        acc  = self._read_float(dacc)
        
        for i in range(min(n, len(self.TWIN_PRIMES))):
            p, q = self.TWIN_PRIMES[i]
            acc += 1.0 / p + 1.0 / q
        
        self._write_float(dacc, acc)
        self._write_float(self.FPU_R_ADDR, acc)
        self._write_flags(acc, acc, 0.0)

    def _read_float(self, base: int) -> float:
        """Lee un float64 big-endian desde RAM."""
        return struct.unpack(">d", bytes(int(self.ram.read(base + i), 2) for i in range(8)))[0]

    def _write_float(self, base: int, v: float) -> None:
        """Escribe un float64 big-endian a RAM."""
        raw = struct.pack(">d", v)
        for i, b in enumerate(raw):
            self.ram.write(base + i, format(b, "08b"))

    def _write_flags(self, r: float, a: float, b: float) -> None:
        """Actualiza las banderas FPU."""
        fl = 0
        if math.isnan(r): fl |= 4
        if r == 0.0:      fl |= 1
        if a < b:         fl |= 2
        self.ram.write(self.FPU_FLAGS_ADDR, format(fl, "08b"))

    # Helpers para testing
    def set_a(self, v: float): self._write_float(self.FPU_A_ADDR, v)
    def set_b(self, v: float): self._write_float(self.FPU_B_ADDR, v)
    def set_op(self, op: int): self.ram.write(self.FPU_OP_ADDR, format(op, "08b"))
    def get_result(self) -> float: return self._read_float(self.FPU_R_ADDR)


# ═════════════════════════════════════════════════════════════════════════════
# CARGADOR DE PROGRAMAS
# ═════════════════════════════════════════════════════════════════════════════

class Loader:
    """
    Cargador de programas binarios en memoria.
    
    Lee archivos con formato de bytes binarios (1 byte = 1 línea de 8 bits)
    e ignora líneas vacías y comentarios (que comienzan con #).
    """
    
    def __init__(self, memory: list):
        self.memory = memory

    def load_program(self, source: str, base_address: int = 0, manual: bool = False) -> None:
        """
        Carga un programa en memoria.
        
        Args:
            source: Ruta del archivo o tupla (dirección, instrucción) si manual=True
            base_address: Dirección donde comienza el programa
            manual: Si True, source es una tupla (addr, instrucción)
        """
        if manual and isinstance(source, tuple):
            addr, instr = source
            self._write_instruction(addr, instr)
        else:
            with open(source, 'r') as f:
                byte_index = 0
                for line_num, line in enumerate(f, start=1):
                    line = line.strip()
                    # Saltar líneas vacías y comentarios
                    if not line or line.startswith('#'):
                        continue
                    if len(line) != 8 or not all(c in '01' for c in line):
                        raise ValueError(
                            f"Línea {line_num}: formato inválido '{line}' "
                            f"(debe ser exactamente 8 bits binarios)"
                        )
                    target = base_address + byte_index
                    if target >= len(self.memory):
                        raise IndexError(
                            f"Línea {line_num}: dirección {target} fuera de rango "
                            f"[0, {len(self.memory)-1}]"
                        )
                    self.memory[target] = line
                    byte_index += 1

    def _write_instruction(self, addr: int, bits: str) -> None:
        """Escribe una instrucción multi-byte en direcciones consecutivas."""
        if len(bits) % 8 != 0:
            raise ValueError(
                f"Instrucción debe tener longitud múltiplo de 8 bits, "
                f"tiene {len(bits)} bits"
            )
        for i in range(0, len(bits), 8):
            byte = bits[i:i+8]
            target = addr + i // 8
            if target >= len(self.memory):
                raise IndexError(f"Dirección {target} fuera de rango")
            self.memory[target] = byte


# ═════════════════════════════════════════════════════════════════════════════
# INSTRUCCIONES DEL CPU - Tabla completa integrada
# ═════════════════════════════════════════════════════════════════════════════

@dataclass
class Params:
    """Parámetros decodificados de una instrucción."""
    ra:   Optional[int] = None  # Registro A
    rb:   Optional[int] = None  # Registro B
    addr: Optional[int] = None  # Dirección (48 bits)
    imm8: Optional[int] = None  # Inmediato de 8 bits


def _b2i(bits: str, required: int = 0) -> int:
    """Convierte string binario a entero."""
    if required > 0 and len(bits) < required:
        raise ValueError(
            f"Parámetros insuficientes: necesita {required} bits, tiene {len(bits)} "
            f"('{bits}'). Verifique el prefijo del opcode."
        )
    return int(bits, 2) if bits else 0


def _rb(mem: RAM, addr: int) -> int:
    """Lee un byte de memoria."""
    return int(mem.read(addr), 2)


def _wb(mem: RAM, addr: int, value: int) -> None:
    """Escribe un byte en memoria."""
    mem.write(addr, format(value & 0xFF, "08b"))


def decode_params(kind: str, params_raw: str) -> Params:
    """Decodifica los parámetros crudos según su tipo."""
    p = Params()
    if kind == "NONE":
        return p
    if kind == "R":
        _b2i(params_raw, 4)
        p.ra = _b2i(params_raw[0:4])
        return p
    if kind == "RR":
        _b2i(params_raw, 8)
        p.ra = _b2i(params_raw[0:4])
        p.rb = _b2i(params_raw[4:8])
        return p
    if kind == "R_IMM8":
        _b2i(params_raw, 12)
        p.ra   = _b2i(params_raw[0:4])
        p.imm8 = _b2i(params_raw[4:12])
        return p
    if kind == "R_DIR":
        _b2i(params_raw, 52)
        p.ra   = _b2i(params_raw[0:4])
        p.addr = _b2i(params_raw[4:52])
        return p
    if kind == "DIR":
        _b2i(params_raw, 48)
        p.addr = _b2i(params_raw[0:48])
        return p
    raise ValueError(f"Tipo de parámetros desconocido: '{kind}'")


# Funciones de instrucción (simplificadas para brevedad)
def instr_nop(cpu, regs, mem, p): pass
def instr_halt(cpu, regs, mem, p): cpu.halted = True
def instr_ret(cpu, regs, mem, p):
    addr = 0
    for i in range(5, -1, -1):
        if regs.SP >= mem.size: cpu.halted = True; return
        addr = (addr << 8) | _rb(mem, regs.SP); regs.pop_SP(1)
    regs.PC = addr % mem.size
def instr_iret(cpu, regs, mem, p): instr_ret(cpu, regs, mem, p)
def instr_int(cpu, regs, mem, p): pass
def instr_fpu_op(cpu, regs, mem, p):
    if cpu.fpu is None: raise RuntimeError("FPU no inicializado.")
    cpu.fpu.execute()
def instr_mov_rr(cpu, regs, mem, p): regs.set_reg(p.ra, regs.get_reg(p.rb))
def instr_push(cpu, regs, mem, p):
    if regs.SP <= 0: cpu.halted = True; return
    regs.push_SP(1); _wb(mem, regs.SP, regs.get_reg(p.ra))
def instr_pop(cpu, regs, mem, p):
    regs.set_reg(p.ra, _rb(mem, regs.SP)); regs.pop_SP(1)
def instr_load(cpu, regs, mem, p): regs.set_reg(p.ra, _rb(mem, p.addr))
def instr_store(cpu, regs, mem, p): _wb(mem, p.addr, regs.get_reg(p.ra))
def instr_xchg(cpu, regs, mem, p):
    a, b = regs.get_reg(p.ra), regs.get_reg(p.rb)
    regs.set_reg(p.ra, b); regs.set_reg(p.rb, a)
def instr_lea(cpu, regs, mem, p): regs.set_reg(p.ra, p.addr & 0xFF)
def instr_movi(cpu, regs, mem, p): regs.set_reg(p.ra, p.imm8)
def instr_add(cpu, regs, mem, p):
    a, b = regs.get_reg(p.ra), regs.get_reg(p.rb)
    res = a + b; regs.update_flags(res, a, b, "add"); regs.set_reg(p.ra, res)
def instr_sub(cpu, regs, mem, p):
    a, b = regs.get_reg(p.ra), regs.get_reg(p.rb)
    res = a - b; regs.update_flags(res, a, b, "sub"); regs.set_reg(p.ra, res)
def instr_mul(cpu, regs, mem, p):
    a, b = regs.get_reg(p.ra), regs.get_reg(p.rb)
    res = a * b; regs.update_flags(res, a, b, "add"); regs.set_reg(p.ra, res)
def instr_div(cpu, regs, mem, p):
    a, b = regs.get_reg(p.ra), regs.get_reg(p.rb)
    res = (a // b) if b else 0; regs.update_flags(res, a, b, "sub"); regs.set_reg(p.ra, res)
def instr_adc(cpu, regs, mem, p):
    a, b = regs.get_reg(p.ra), regs.get_reg(p.rb)
    res = a + b + (1 if regs.flag_C else 0); regs.update_flags(res, a, b, "add"); regs.set_reg(p.ra, res)
def instr_sbb(cpu, regs, mem, p):
    a, b = regs.get_reg(p.ra), regs.get_reg(p.rb)
    res = a - b - (1 if regs.flag_C else 0); regs.update_flags(res, a, b, "sub"); regs.set_reg(p.ra, res)
def instr_inc(cpu, regs, mem, p):
    a = regs.get_reg(p.ra); res = a + 1; regs.set_reg(p.ra, res); regs.update_flags(res, a, 1, "add")
def instr_dec(cpu, regs, mem, p):
    a = regs.get_reg(p.ra); res = a - 1; regs.set_reg(p.ra, res); regs.update_flags(res, a, 1, "sub")
def instr_neg(cpu, regs, mem, p):
    a = regs.get_reg(p.ra); res = (-a) & 0xFF; regs.set_reg(p.ra, res); regs.update_flags(res, 0, a, "sub")
def instr_and(cpu, regs, mem, p):
    res = regs.get_reg(p.ra) & regs.get_reg(p.rb); regs.set_reg(p.ra, res); regs.update_flags(res, operation="logic")
def instr_xor(cpu, regs, mem, p):
    res = regs.get_reg(p.ra) ^ regs.get_reg(p.rb); regs.set_reg(p.ra, res); regs.update_flags(res, operation="logic")
def instr_xora(cpu, regs, mem, p):
    res = ~(regs.get_reg(p.ra) ^ regs.get_reg(p.rb)) & 0xFF; regs.set_reg(p.ra, res); regs.update_flags(res, operation="logic")
def instr_not(cpu, regs, mem, p):
    res = (~regs.get_reg(p.ra)) & 0xFF; regs.set_reg(p.ra, res); regs.update_flags(res, operation="logic")
def instr_shl(cpu, regs, mem, p):
    a = regs.get_reg(p.ra); c = bool(a & 0x80); res = (a << 1) & 0xFF
    regs.set_reg(p.ra, res); regs.update_flags(res, operation="logic"); regs.flag_C = c
def instr_shr(cpu, regs, mem, p):
    a = regs.get_reg(p.ra); c = bool(a & 0x01); res = (a >> 1) & 0xFF
    regs.set_reg(p.ra, res); regs.update_flags(res, operation="logic"); regs.flag_C = c
def instr_rol(cpu, regs, mem, p):
    a = regs.get_reg(p.ra); res = ((a << 1) | (a >> 7)) & 0xFF
    regs.set_reg(p.ra, res); regs.update_flags(res, operation="logic")
def instr_ror(cpu, regs, mem, p):
    a = regs.get_reg(p.ra); res = ((a >> 1) | ((a & 1) << 7)) & 0xFF
    regs.set_reg(p.ra, res); regs.update_flags(res, operation="logic")
def instr_cmp(cpu, regs, mem, p):
    a, b = regs.get_reg(p.ra), regs.get_reg(p.rb); regs.update_flags(a - b, a, b, "sub")
def instr_test(cpu, regs, mem, p):
    regs.update_flags(regs.get_reg(p.ra) & regs.get_reg(p.rb), operation="logic")
def instr_jmp(cpu, regs, mem, p): regs.PC = p.addr % mem.size
def instr_jz(cpu, regs, mem, p):
    if regs.flag_Z: regs.PC = p.addr % mem.size
def instr_jnz(cpu, regs, mem, p):
    if not regs.flag_Z: regs.PC = p.addr % mem.size
def instr_jc(cpu, regs, mem, p):
    if regs.flag_C: regs.PC = p.addr % mem.size
def instr_jnc(cpu, regs, mem, p):
    if not regs.flag_C: regs.PC = p.addr % mem.size
def instr_call(cpu, regs, mem, p):
    ret = regs.PC
    for i in range(5, -1, -1):
        if regs.SP <= 0: cpu.halted = True; return
        regs.push_SP(1); _wb(mem, regs.SP, (ret >> (8 * i)) & 0xFF)
    regs.PC = p.addr % mem.size


instr_dict: Dict[str, Tuple[Callable, str]] = {
    "00000000": (instr_nop,    "NONE"),
    "00000001": (instr_halt,   "NONE"),
    "00000010": (instr_ret,    "NONE"),
    "00000011": (instr_iret,   "NONE"),
    "00000100": (instr_fpu_op, "NONE"),
    "0100000":  (instr_mov_rr, "RR"),
    "0100001":  (instr_xchg,   "RR"),
    "0100010":  (instr_push,   "R"),
    "0100011":  (instr_pop,    "R"),
    "0100100":  (instr_add,    "RR"),
    "0100101":  (instr_sub,    "RR"),
    "0100110":  (instr_mul,    "RR"),
    "0100111":  (instr_div,    "RR"),
    "0101000":  (instr_adc,    "RR"),
    "0101001":  (instr_sbb,    "RR"),
    "0101010":  (instr_inc,    "R"),
    "0101011":  (instr_dec,    "R"),
    "0101100":  (instr_neg,    "R"),
    "0101101":  (instr_and,    "RR"),
    "0101110":  (instr_xor,    "RR"),
    "0101111":  (instr_xora,   "RR"),
    "0110000":  (instr_cmp,    "RR"),
    "0110001":  (instr_test,   "RR"),
    "0110010":  (instr_not,    "R"),
    "0110011":  (instr_shl,    "R"),
    "0110100":  (instr_shr,    "R"),
    "0110101":  (instr_rol,    "R"),
    "0110110":  (instr_ror,    "R"),
    "1000000":  (instr_movi,   "R_IMM8"),
    "1100001":  (instr_load,   "R_DIR"),
    "1100010":  (instr_store,  "R_DIR"),
    "1100011":  (instr_lea,    "R_DIR"),
    "1100100":  (instr_jz,     "DIR"),
    "1100101":  (instr_jnz,    "DIR"),
    "1100110":  (instr_jc,     "DIR"),
    "1100111":  (instr_jnc,    "DIR"),
    "1101000":  (instr_jmp,    "DIR"),
    "1101001":  (instr_call,   "DIR"),
}


# ═════════════════════════════════════════════════════════════════════════════
# NÚCLEO DEL CPU
# ═════════════════════════════════════════════════════════════════════════════

class CPUCore:
    """Núcleo del CPU NB-64 que implementa FETCH-DECODE-EXECUTE."""
    
    PREFIX_TO_BYTES: Dict[str, int] = {"00": 1, "01": 2, "10": 4, "11": 8}

    def __init__(self, ram: RAM, regs: Registers, fpu=None):
        self.ram    = ram
        self.regs   = regs
        self.fpu    = fpu
        self.halted = False

    def fetch(self) -> str:
        pc = self.regs.PC
        first_byte = self.ram.read(pc)
        prefix = first_byte[:2]
        instr_bytes = self.PREFIX_TO_BYTES.get(prefix, 1)
        bits_list = [first_byte]
        for i in range(1, instr_bytes):
            bits_list.append(self.ram.read(pc + i))
        instr_bits = "".join(bits_list)
        self.regs.increment_PC(instr_bytes)
        self.regs.IR = instr_bits
        return instr_bits

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
            raise ValueError(f"Opcode desconocido. PC={self.regs.PC}, IR={instr_bits!r}")
        params_raw = instr_bits[len(opcode_bits):]
        return {
            "opcode_bits": opcode_bits,
            "function":    func,
            "param_type":  param_type,
            "params_raw":  params_raw,
        }

    def step(self):
        if self.halted:
            return
        instr_bits = self.fetch()
        decoded    = self.decode(instr_bits)
        params: Params = decode_params(decoded["param_type"], decoded["params_raw"])
        decoded["function"](self, self.regs, self.ram, params)
        return decoded

    def run(self, max_cycles=10000):
        cycles = 0
        while not self.halted and cycles < max_cycles:
            pc = self.regs.PC
            if pc >= self.ram.size:
                print("Fin de memoria alcanzado")
                break
            self.step()
            cycles += 1

    def reset(self):
        self.regs.reset()
        self.halted = False


# ═════════════════════════════════════════════════════════════════════════════
# COMPUTADORA
# ═════════════════════════════════════════════════════════════════════════════

class Computer:
    """Orquestador de la computadora NB-64."""

    def __init__(self):
        self.ram    = RAM(256)
        self.regs   = Registers()
        self.loader = Loader(self.ram._memory)
        self.fpu    = FPU(self.ram)
        self.cpu    = CPUCore(self.ram, self.regs, fpu=self.fpu)

    def reset(self):
        self.ram    = RAM(256)
        self.regs   = Registers()
        self.loader = Loader(self.ram._memory)
        self.fpu    = FPU(self.ram)
        self.cpu    = CPUCore(self.ram, self.regs, fpu=self.fpu)

    def load_program(self, filepath: str, base_addr: int = 0):
        self.loader.load_program(filepath, base_addr)
        print(f"Programa cargado en dirección {base_addr}")

    def run(self, max_cycles=10000):
        self.cpu.run(max_cycles)
        print(f"Ejecución completada.")

    def show_state(self):
        print("\n" + "="*60)
        print("ESTADO DE LA COMPUTADORA NB-64")
        print("="*60)
        self.regs.show()
        print("\nMemoria (primeros 16 bytes):")
        self.ram.show(0, 16)


if __name__ == "__main__":
    print("Simulador NB-64 cargado exitosamente.")
    print("Para usar: computadora = Computer()")
