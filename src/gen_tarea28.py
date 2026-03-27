
import struct, os, sys
import pathlib
# Añadir directorio actual al path para importaciones
script_dir = pathlib.Path(__file__).parent
sys.path.insert(0, str(script_dir))

def b(v, n=8): return format(v & ((1<<n)-1), f"0{n}b")

# ── Codificadores con prefijos correctos ─────────────────────────────────────

def movi(ra, imm):
    """MOVI Ra, imm8 → 4 bytes (prefijo '10')"""
    bits = "1000000"+b(ra,4)+b(imm,8)+"0"*13
    return [int(bits[i:i+8],2) for i in range(0,32,8)]

def store_r(ra, addr):
    """STORE Ra, addr → 8 bytes (prefijo '11', opcode '1100010')"""
    bits = "1100010"+b(ra,4)+b(addr,48)+"00000"
    return [int(bits[i:i+8],2) for i in range(0,64,8)]

def load_r(ra, addr):
    """LOAD Ra, addr → 8 bytes (prefijo '11', opcode '1100001')"""
    bits = "1100001"+b(ra,4)+b(addr,48)+"00000"
    return [int(bits[i:i+8],2) for i in range(0,64,8)]

def jnz(addr):
    """JNZ addr → 8 bytes (prefijo '11', opcode '1100101')"""
    bits = "1100101"+b(addr,48)+"0"*9
    return [int(bits[i:i+8],2) for i in range(0,64,8)]

def dec_r(ra):
    """DEC Ra → 2 bytes"""
    bits = "0101011"+b(ra,4)+"00000"
    return [int(bits[:8],2), int(bits[8:],2)]

def cmp_rr(ra, rb):
    """CMP Ra, Rb → 2 bytes"""
    bits = "0110000"+b(ra,4)+b(rb,4)+"0"
    return [int(bits[:8],2), int(bits[8:],2)]

HALT   = [0x01]
FPU_OP = [0x04]

FPU_A=0xE0; FPU_B=0xE8; FPU_OP_R=0xF0; FPU_RES=0xF1
FPU_P0=0xFA; FPU_P1=0xFB; FPU_P2=0xFC

FPU_ADD=0x01; FPU_SUB=0x02; FPU_MUL=0x03; FPU_DIV=0x04
FPU_HERON=0x10; FPU_BRUN=0x20


class Prog:
    def __init__(self):
        self.bytes=[]; self.labels={}; self.fixups=[]

    def here(self): return len(self.bytes)
    def label(self, n): self.labels[n] = self.here()
    def el(self, lst):
        for x in lst: self.bytes.append(x & 0xFF)

    def MOVI(self,ra,imm):   self.el(movi(ra,imm))
    def STORE(self,ra,addr): self.el(store_r(ra,addr))
    def LOAD(self,ra,addr):  self.el(load_r(ra,addr))
    def HALT(self):          self.el(HALT)
    def FPU(self):           self.el(FPU_OP)
    def DEC(self,ra):        self.el(dec_r(ra))
    def CMP(self,ra,rb):     self.el(cmp_rr(ra,rb))
    def JNZ(self, label):
        self.fixups.append((self.here(), label)); self.el([0]*8)

    def sf64(self, base, v):
        """Escribe float64 sparse: solo bytes no-cero (ahorra instrucciones)."""
        raw = struct.pack(">d", v)
        for i, byt in enumerate(raw):
            if byt != 0:
                self.MOVI(0, byt); self.STORE(0, base+i)

    def fpu_op(self, op):
        """Selecciona operación FPU y ejecuta FPU_OP."""
        self.MOVI(0, op); self.STORE(0, FPU_OP_R); self.FPU()

    def resolve(self):
        for off, lbl in self.fixups:
            if lbl not in self.labels:
                raise ValueError(f"Etiqueta no definida: '{lbl}'")
            bs = jnz(self.labels[lbl])
            for i, bv in enumerate(bs): self.bytes[off+i] = bv

    def save(self, path, header=""):
        self.resolve()
        with open(path, 'w') as f:
            for line in header.strip().split('\n'):
                f.write(f"# {line}\n")
            f.write("#\n")
            for bv in self.bytes:
                f.write(format(bv, "08b") + "\n")
        pct = len(self.bytes)/256*100
        print(f"  {path.split('/')[-1]} -> {len(self.bytes)} bytes ({pct:.1f}% RAM)")
        if len(self.bytes) > 256:
            raise OverflowError(f"OVERFLOW: {len(self.bytes)} > 256 bytes!")


# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 1: fpu_lib.txt
# ═══════════════════════════════════════════════════════════════════════════════
def build_fpu_lib():
    """
    Demuestra fp_add, fp_sub, fp_mul, fp_div.
    Usa valores con pocos bytes no-cero para que el codigo quepe antes de 0xE0 (224).
    Resultados: ADD(4+2)=6, SUB(8-2)=6, MUL(4*2)=8, DIV(8/2)=4.
    """
    p = Prog()
    # Valores elegidos por tener 1-2 bytes no-cero en IEEE 754:
    # 2.0 = 0x4000000000000000 (1 byte no-cero)
    # 4.0 = 0x4010000000000000 (2 bytes no-cero)
    # 8.0 = 0x4020000000000000 (2 bytes no-cero)
    p.sf64(FPU_A, 4.0); p.sf64(FPU_B, 2.0); p.fpu_op(FPU_ADD)  # = 6.0
    p.sf64(FPU_A, 8.0); p.sf64(FPU_B, 2.0); p.fpu_op(FPU_SUB)  # = 6.0
    p.sf64(FPU_A, 4.0); p.sf64(FPU_B, 2.0); p.fpu_op(FPU_MUL)  # = 8.0
    p.sf64(FPU_A, 8.0); p.sf64(FPU_B, 2.0); p.fpu_op(FPU_DIV)  # = 4.0
    p.HALT()
    return p

# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 2: heron.txt
# ═══════════════════════════════════════════════════════════════════════════════
def build_heron():
    p = Prog()
    X_ADDR=0xA0; Y_ADDR=0xA8

    p.sf64(X_ADDR, 125.0)
    p.sf64(Y_ADDR, 10.0)

    p.MOVI(0, X_ADDR); p.STORE(0, FPU_P0)
    p.MOVI(0, Y_ADDR); p.STORE(0, FPU_P1)
    p.MOVI(0, 5);      p.STORE(0, FPU_P2)
    p.MOVI(0, FPU_HERON); p.STORE(0, FPU_OP_R)

    p.label("loop")
    p.FPU()
    p.LOAD(0, FPU_P2)
    p.MOVI(1, 0)
    p.CMP(0, 1)
    p.JNZ("loop")

    p.HALT()
    return p

# ═══════════════════════════════════════════════════════════════════════════════
# PARTE 3: brun.txt
# ═══════════════════════════════════════════════════════════════════════════════
def build_brun():
    from fpu import FPU as FPUClass
    p = Prog()
    ACC_ADDR = 0x90

    n_pairs = len(FPUClass.TWIN_PRIMES)
    b2 = sum(1.0/p_+1.0/q for p_,q in FPUClass.TWIN_PRIMES)
    print(f"  Pares: {FPUClass.TWIN_PRIMES}")
    print(f"  B2 parcial esperada = {b2:.10f}")

    p.MOVI(0,0)
    for i in range(8): p.STORE(0, ACC_ADDR+i)

    p.MOVI(0, n_pairs);  p.STORE(0, FPU_P0)
    p.MOVI(0, ACC_ADDR); p.STORE(0, FPU_P1)
    p.fpu_op(FPU_BRUN)
    p.HALT()
    return p


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Usar rutas relativas al archivo actual
    script_dir = pathlib.Path(__file__).parent
    project_root = script_dir.parent  # Un nivel arriba de src/
    out   = str(project_root / "programs" / "generated")
    local = str(project_root / "programs" / "examples")
    os.makedirs(out, exist_ok=True); os.makedirs(local, exist_ok=True)

    print("="*60)
    print("Tarea 28 — NB-64 FPU IEEE 754 doble precision")
    print("="*60)

    print("\n[Verificacion Heron sqrt(125) en Python puro]")
    y = 10.0
    for i in range(5):
        y = 0.5*(y + 125.0/y)
        print(f"  iter {i+1}: {y:.12f}  error={abs(y-125**0.5):.2e}")

    print("\n[1] fpu_lib.txt")
    lib = build_fpu_lib()
    h1 = """Tarea 28 Parte 1: Libreria FPU IEEE 754 doble precision para NB-64
Subrutinas implementadas: fp_add, fp_sub, fp_mul, fp_div
Instruccion FPU_OP = 00000100 (1 byte) llama al coprocesador fpu.py
Protocolo: A en RAM[0xE0..0xE7], B en RAM[0xE8..0xEF], op en RAM[0xF0]
Resultado siempre en RAM[0xF1..0xF8] (FPU_RES, float64 IEEE 754 big-endian)
Demostraciones (usar Step para ver resultado de cada una en RAM[0xF1..0xF8]):
  fp_add(4.0, 2.0) = 6.0
  fp_sub(8.0, 2.0) = 6.0
  fp_mul(4.0, 2.0) = 8.0
  fp_div(8.0, 2.0) = 4.0  <- resultado final al HALT"""
    lib.save(f"{out}/fpu_lib.txt", h1)
    lib.save(f"{local}/fpu_lib.txt", h1)

    print("\n[2] heron.txt")
    her = build_heron()
    h2 = """Tarea 28 Parte 2: sqrt(125) metodo de Heron (pag. 26, De Euclides a Java)
Formula: y_{i+1} = (1/2)*(y_i + x/y_i), x=125.0, y0=10.0, iteraciones=5
FPU extendida HERON_STEP (op=0x10): 1 iteracion completa IEEE 754 por FPU_OP
Convergencia: iter1=11.25, iter2=11.18056, iter3=11.18034, iter4+=converge
Resultado tras HALT:
  RAM[0xA8..0xAF] = float64 big-endian = 11.180339887498949
  RAM[0xF1..0xF8] = mismo valor (FPU_RES)"""
    her.save(f"{out}/heron.txt", h2)
    her.save(f"{local}/heron.txt", h2)

    print("\n[3] brun.txt")
    brun = build_brun()
    h3 = """Tarea 28 Parte 3: Estimacion de la Constante de Brun
B2 = sum(1/p + 1/q) para pares de primos gemelos (p, p+2)
Pares: (3,5),(5,7),(11,13),(17,19),(29,31),(41,43),(59,61),(71,73),(101,103),(107,109)
FPU extendida BRUN_ACCUMULATE (op=0x20): suma completa en 1 FPU_OP
Resultado tras HALT:
  RAM[0x90..0x97] = float64 big-endian = B2 parcial con 10 pares
  RAM[0xF1..0xF8] = mismo valor (FPU_RES)
  B2 completa conocida = 1.902160583104..."""
    brun.save(f"{out}/brun.txt", h3)
    brun.save(f"{local}/brun.txt", h3)

    print("\nDone.")
