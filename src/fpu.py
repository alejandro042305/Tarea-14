"""
fpu.py — Coprocesador FPU IEEE 754 doble precisión para NB-64

PROTOCOLO BÁSICO:
  RAM[0xE0..0xE7] = Operando A  (float64, big-endian)
  RAM[0xE8..0xEF] = Operando B  (float64, big-endian)
  RAM[0xF0]       = Código de operación (0x01=ADD,0x02=SUB,0x03=MUL,0x04=DIV,0x05=SQRT)
  RAM[0xF1..0xF8] = Resultado
  RAM[0xF9]       = Flags (bit0=Zero, bit1=A<B, bit2=NaN)

OPERACIONES EXTENDIDAS (un solo FPU_OP hace toda la operación compuesta):
  RAM[0xF0]=0x10 → HERON_STEP: una iteración de Heron, params en 0xFA,0xFB,0xFC
  RAM[0xF0]=0x20 → BRUN_ACCUMULATE: acumula Constante de Brun, params en 0xFA,0xFB
"""

import struct, math
from ram import RAM

FPU_A_ADDR     = 0xE0
FPU_B_ADDR     = 0xE8
FPU_OP_ADDR    = 0xF0
FPU_R_ADDR     = 0xF1
FPU_FLAGS_ADDR = 0xF9
FPU_PARAM0     = 0xFA
FPU_PARAM1     = 0xFB
FPU_PARAM2     = 0xFC

FPU_ADD  = 0x01
FPU_SUB  = 0x02
FPU_MUL  = 0x03
FPU_DIV  = 0x04
FPU_SQRT = 0x05
FPU_CMP  = 0x06
FPU_HERON_STEP      = 0x10
FPU_BRUN_ACCUMULATE = 0x20


def _rf(ram, base):
    return struct.unpack(">d", bytes(int(ram.read(base+i),2) for i in range(8)))[0]

def _wf(ram, base, v):
    raw = struct.pack(">d", v)
    for i,b in enumerate(raw): ram.write(base+i, format(b,"08b"))

def _wfl(ram, r, a, b):
    fl = 0
    if math.isnan(r): fl |= 4
    if r == 0.0:      fl |= 1
    if a < b:         fl |= 2
    ram.write(FPU_FLAGS_ADDR, format(fl,"08b"))


class FPU:
    TWIN_PRIMES = [
        (3,5),(5,7),(11,13),(17,19),(29,31),
        (41,43),(59,61),(71,73),(101,103),(107,109)
    ]

    def __init__(self, ram: RAM):
        self.ram = ram

    def execute(self):
        op = int(self.ram.read(FPU_OP_ADDR), 2)
        if   op == FPU_HERON_STEP:      self._heron_step()
        elif op == FPU_BRUN_ACCUMULATE: self._brun_accumulate()
        else:                           self._basic(op)

    def _basic(self, op):
        a = _rf(self.ram, FPU_A_ADDR)
        b = _rf(self.ram, FPU_B_ADDR)
        if   op == FPU_ADD:  r = a + b
        elif op == FPU_SUB:  r = a - b
        elif op == FPU_MUL:  r = a * b
        elif op == FPU_DIV:  r = (a/b) if b else math.copysign(math.inf,a)
        elif op == FPU_SQRT: r = math.sqrt(a) if a>=0 else float('nan')
        elif op == FPU_CMP:  r = a - b
        else: raise ValueError(f"FPU op desconocida: {op:#04x}")
        _wf(self.ram, FPU_R_ADDR, r)
        _wfl(self.ram, r, a, b)

    def _heron_step(self):
        """
        Una iteración completa de Heron: y_new = (y + x/y) / 2
        RAM[0xFA] = dirección base de x (float64, 8 bytes)
        RAM[0xFB] = dirección base de y (float64, 8 bytes, se actualiza)
        RAM[0xFC] = contador (se decrementa)
        """
        dx = int(self.ram.read(FPU_PARAM0), 2)
        dy = int(self.ram.read(FPU_PARAM1), 2)
        cnt = int(self.ram.read(FPU_PARAM2), 2)
        x = _rf(self.ram, dx)
        y = _rf(self.ram, dy)
        y_new = 0.5 * (y + x/y)
        _wf(self.ram, dy, y_new)
        _wf(self.ram, FPU_R_ADDR, y_new)
        _wfl(self.ram, y_new, x, y)
        self.ram.write(FPU_PARAM2, format(max(0,cnt-1), "08b"))

    def _brun_accumulate(self):
        """
        Acumula Constante de Brun: acc += sum(1/p + 1/q)
        RAM[0xFA] = número de pares a usar
        RAM[0xFB] = dirección del acumulador (float64, 8 bytes)
        """
        n    = int(self.ram.read(FPU_PARAM0), 2)
        dacc = int(self.ram.read(FPU_PARAM1), 2)
        acc  = _rf(self.ram, dacc)
        for i in range(min(n, len(self.TWIN_PRIMES))):
            p,q = self.TWIN_PRIMES[i]
            acc += 1.0/p + 1.0/q
        _wf(self.ram, dacc, acc)
        _wf(self.ram, FPU_R_ADDR, acc)
        _wfl(self.ram, acc, acc, 0.0)

    # helpers testing
    def set_a(self,v): _wf(self.ram, FPU_A_ADDR, v)
    def set_b(self,v): _wf(self.ram, FPU_B_ADDR, v)
    def set_op(self,op): self.ram.write(FPU_OP_ADDR, format(op,"08b"))
    def get_result(self): return _rf(self.ram, FPU_R_ADDR)
    def get_result_bytes(self): return [int(self.ram.read(FPU_R_ADDR+i),2) for i in range(8)]
    def reset(self): pass
