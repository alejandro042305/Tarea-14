"""
instructions.py — Set de instrucciones para NB-64 con FPU (Tarea 28)

ESQUEMA DE PREFIJOS (corrección bug original):
  Prefijo "00" (1 byte) : NOP, HALT, RET, IRET, FPU_OP
  Prefijo "01" (2 bytes): operaciones registro-registro
  Prefijo "10" (4 bytes): MOVI (único que cabe en 4 bytes con R_IMM8)
  Prefijo "11" (8 bytes): LOAD, STORE, JMP, JZ, JNZ, JC, JNC, CALL, LEA
                          (necesitan 48 bits de dirección → 8 bytes mínimo)
"""

from dataclasses import dataclass
from typing import Optional, Callable, Dict, Tuple
from ram import RAM
from registers import Registers


@dataclass
class Params:
    ra:   Optional[int] = None
    rb:   Optional[int] = None
    addr: Optional[int] = None
    imm8: Optional[int] = None


def _b2i(bits: str, required: int = 0) -> int:
    if required > 0 and len(bits) < required:
        raise ValueError(
            f"params_raw insuficiente: necesita {required} bits, tiene {len(bits)} "
            f"('{bits}'). Verifique el prefijo del opcode."
        )
    return int(bits, 2) if bits else 0


def _rb(mem: RAM, addr: int) -> int:
    return int(mem.read(addr), 2)


def _wb(mem: RAM, addr: int, value: int) -> None:
    mem.write(addr, format(value & 0xFF, "08b"))


def decode_params(kind: str, params_raw: str) -> Params:
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


# ── Movimiento de datos ────────────────────────────────────────────────────────
def instr_mov_rr(cpu, regs, mem, p):   regs.set_reg(p.ra, regs.get_reg(p.rb))
def instr_push(cpu, regs, mem, p):
    if regs.SP <= 0: cpu.halted = True; return
    regs.push_SP(1); _wb(mem, regs.SP, regs.get_reg(p.ra))
def instr_pop(cpu, regs, mem, p):
    regs.set_reg(p.ra, _rb(mem, regs.SP)); regs.pop_SP(1)
def instr_load(cpu, regs, mem, p):    regs.set_reg(p.ra, _rb(mem, p.addr))
def instr_store(cpu, regs, mem, p):   _wb(mem, p.addr, regs.get_reg(p.ra))
def instr_xchg(cpu, regs, mem, p):
    a,b = regs.get_reg(p.ra), regs.get_reg(p.rb)
    regs.set_reg(p.ra,b); regs.set_reg(p.rb,a)
def instr_lea(cpu, regs, mem, p):     regs.set_reg(p.ra, p.addr & 0xFF)

# ── Aritmética entera ─────────────────────────────────────────────────────────
def _alu(regs, p, op):
    a,b = regs.get_reg(p.ra), regs.get_reg(p.rb)
    if   op=="add": res=a+b;              regs.update_flags(res,a,b,"add")
    elif op=="sub": res=a-b;              regs.update_flags(res,a,b,"sub")
    elif op=="mul": res=a*b;              regs.update_flags(res,a,b,"add")
    elif op=="div": res=(a//b) if b else 0; regs.update_flags(res,a,b,"sub")
    elif op=="adc": res=a+b+(1 if regs.flag_C else 0); regs.update_flags(res,a,b,"add")
    elif op=="sbb": res=a-b-(1 if regs.flag_C else 0); regs.update_flags(res,a,b,"sub")
    regs.set_reg(p.ra, res)

def instr_movi(cpu, regs, mem, p): regs.set_reg(p.ra, p.imm8)
def instr_add(cpu, regs, mem, p):  _alu(regs,p,"add")
def instr_sub(cpu, regs, mem, p):  _alu(regs,p,"sub")
def instr_mul(cpu, regs, mem, p):  _alu(regs,p,"mul")
def instr_div(cpu, regs, mem, p):  _alu(regs,p,"div")
def instr_adc(cpu, regs, mem, p):  _alu(regs,p,"adc")
def instr_sbb(cpu, regs, mem, p):  _alu(regs,p,"sbb")
def instr_inc(cpu, regs, mem, p):
    a=regs.get_reg(p.ra); res=a+1
    regs.set_reg(p.ra,res); regs.update_flags(res,a,1,"add")
def instr_dec(cpu, regs, mem, p):
    a=regs.get_reg(p.ra); res=a-1
    regs.set_reg(p.ra,res); regs.update_flags(res,a,1,"sub")
def instr_neg(cpu, regs, mem, p):
    a=regs.get_reg(p.ra); res=(-a)&0xFF
    regs.set_reg(p.ra,res); regs.update_flags(res,0,a,"sub")

# ── Lógica ────────────────────────────────────────────────────────────────────
def instr_and(cpu, regs, mem, p):
    res=regs.get_reg(p.ra)&regs.get_reg(p.rb)
    regs.set_reg(p.ra,res); regs.update_flags(res,operation="logic")
def instr_xor(cpu, regs, mem, p):
    res=regs.get_reg(p.ra)^regs.get_reg(p.rb)
    regs.set_reg(p.ra,res); regs.update_flags(res,operation="logic")
def instr_xora(cpu, regs, mem, p):
    res=~(regs.get_reg(p.ra)^regs.get_reg(p.rb))&0xFF
    regs.set_reg(p.ra,res); regs.update_flags(res,operation="logic")
def instr_not(cpu, regs, mem, p):
    res=(~regs.get_reg(p.ra))&0xFF
    regs.set_reg(p.ra,res); regs.update_flags(res,operation="logic")
def instr_shl(cpu, regs, mem, p):
    a=regs.get_reg(p.ra); c=bool(a&0x80); res=(a<<1)&0xFF
    regs.set_reg(p.ra,res); regs.update_flags(res,operation="logic"); regs.flag_C=c
def instr_shr(cpu, regs, mem, p):
    a=regs.get_reg(p.ra); c=bool(a&0x01); res=(a>>1)&0xFF
    regs.set_reg(p.ra,res); regs.update_flags(res,operation="logic"); regs.flag_C=c
def instr_rol(cpu, regs, mem, p):
    a=regs.get_reg(p.ra); res=((a<<1)|(a>>7))&0xFF
    regs.set_reg(p.ra,res); regs.update_flags(res,operation="logic")
def instr_ror(cpu, regs, mem, p):
    a=regs.get_reg(p.ra); res=((a>>1)|((a&1)<<7))&0xFF
    regs.set_reg(p.ra,res); regs.update_flags(res,operation="logic")
def instr_cmp(cpu, regs, mem, p):
    a,b=regs.get_reg(p.ra),regs.get_reg(p.rb)
    regs.update_flags(a-b,a,b,"sub")
def instr_test(cpu, regs, mem, p):
    regs.update_flags(regs.get_reg(p.ra)&regs.get_reg(p.rb),operation="logic")

# ── Control de flujo ──────────────────────────────────────────────────────────
def instr_jmp(cpu, regs, mem, p):  regs.PC = p.addr % mem.size
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
    for i in range(5,-1,-1):
        if regs.SP <= 0: cpu.halted = True; return
        regs.push_SP(1); _wb(mem, regs.SP, (ret>>(8*i))&0xFF)
    regs.PC = p.addr % mem.size

# ── Sistema ───────────────────────────────────────────────────────────────────
def instr_nop(cpu, regs, mem, p):  pass
def instr_halt(cpu, regs, mem, p): cpu.halted = True
def instr_ret(cpu, regs, mem, p):
    addr = 0
    for i in range(5,-1,-1):
        if regs.SP >= mem.size: cpu.halted = True; return
        addr = (addr<<8)|_rb(mem, regs.SP); regs.pop_SP(1)
    regs.PC = addr % mem.size
def instr_iret(cpu, regs, mem, p): instr_ret(cpu, regs, mem, p)
def instr_int(cpu, regs, mem, p):  pass

# ── FPU_OP — Coprocesador FPU ─────────────────────────────────────────────────
def instr_fpu_op(cpu, regs, mem, p):
    """
    Llama al coprocesador FPU. Protocolo en RAM:
      [0xE0..0xE7] = Operando A (float64, big-endian)
      [0xE8..0xEF] = Operando B (float64, big-endian)
      [0xF0]       = Código de operación FPU
      [0xF1..0xF8] = Resultado (escrito por FPU)
      [0xF9]       = Flags FPU
    Operaciones extendidas: 0x10=HERON_STEP, 0x20=BRUN_ACCUMULATE
    """
    if cpu.fpu is None:
        raise RuntimeError("FPU no inicializado.")
    cpu.fpu.execute()


# ── Tabla de instrucciones ────────────────────────────────────────────────────
instr_dict: Dict[str, Tuple[Callable, str]] = {

    # 1 byte — prefijo "00"
    "00000000": (instr_nop,    "NONE"),
    "00000001": (instr_halt,   "NONE"),
    "00000010": (instr_ret,    "NONE"),
    "00000011": (instr_iret,   "NONE"),
    "00000100": (instr_fpu_op, "NONE"),   # FPU_OP

    # 2 bytes — prefijo "01"
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

    # 4 bytes — prefijo "10" (solo MOVI cabe en 4 bytes con R_IMM8)
    "1000000":  (instr_movi,   "R_IMM8"),

    # 8 bytes — prefijo "11" (LOAD, STORE, saltos, CALL necesitan 48-bit addr)
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
