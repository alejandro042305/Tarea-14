import tkinter as tk
from tkinter import filedialog
import struct
from computer import Computer
from fpu import FPU_A_ADDR, FPU_B_ADDR, FPU_R_ADDR, FPU_OP_ADDR, FPU_FLAGS_ADDR


def _read_float64_from_mem(mem_list, base):
    """Lee 8 bytes de la lista de memoria como float64."""
    try:
        raw = bytes(int(mem_list[base + i], 2) for i in range(8))
        return struct.unpack(">d", raw)[0]
    except Exception:
        return None


class NB64GUI:

    def __init__(self):
        self.comp = Computer()
        self.root = tk.Tk()
        self.root.title("NB-64 Computer — Arquitectura Von Neumann + FPU IEEE 754")
        self.root.geometry("1400x750")
        self.create_widgets()
        self.update_view()

    def create_widgets(self):
        # ── Barra de botones ──────────────────────────────────────────────
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=4, pady=4)

        tk.Button(top, text="Cargar Programa", command=self.load,
                  bg="#4A90D9", fg="white").pack(side="left", padx=2)
        tk.Button(top, text="Step",  command=self.step,
                  bg="#5BA85A", fg="white").pack(side="left", padx=2)
        tk.Button(top, text="Run",   command=self.run,
                  bg="#D9853B", fg="white").pack(side="left", padx=2)
        tk.Button(top, text="Reset", command=self.reset,
                  bg="#C0392B", fg="white").pack(side="left", padx=2)

        self.status_var = tk.StringVar(value="Listo")
        tk.Label(top, textvariable=self.status_var,
                 font=("Courier", 10)).pack(side="left", padx=12)

        # ── Cuerpo principal ──────────────────────────────────────────────
        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=4)

        # Panel izquierdo: RAM
        left = tk.Frame(main)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="RAM (256 bytes)", font=("Courier", 10, "bold")).pack()
        self.mem = tk.Text(left, width=55, font=("Courier", 9))
        sb = tk.Scrollbar(left, command=self.mem.yview)
        self.mem.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.mem.pack(side="left", fill="both", expand=True)

        # Panel central: Registros + Flags
        mid = tk.Frame(main, width=200)
        mid.pack(side="left", fill="y", padx=6)
        tk.Label(mid, text="Registros", font=("Courier", 10, "bold")).pack()
        self.reg = tk.Text(mid, width=28, font=("Courier", 9))
        self.reg.pack(fill="y", expand=True)
        self.flags = tk.Label(mid, text="Flags", font=("Courier", 10),
                              relief="sunken", padx=4)
        self.flags.pack(fill="x")

        # Panel derecho: FPU
        right = tk.Frame(main, width=280)
        right.pack(side="right", fill="y", padx=4)
        tk.Label(right, text="FPU — Coprocesador IEEE 754",
                 font=("Courier", 10, "bold"), fg="#4A90D9").pack()
        tk.Label(right, text="Protocolo: STORE byte→RAM, luego FPU_OP (00000100)",
                 font=("Courier", 8), fg="#666").pack()
        self.fpu_panel = tk.Text(right, width=36, font=("Courier", 9),
                                 bg="#f0f4ff")
        self.fpu_panel.pack(fill="both", expand=True)

    def load(self):
        file = filedialog.askopenfilename(
            filetypes=[("Programas NB-64", "*.txt"), ("Todos", "*.*")]
        )
        if file:
            self.comp.reset()
            self.comp.loader.load_program(file)
            self.status_var.set(f"Cargado: {file.split('/')[-1]}")
            self.update_view()

    def step(self):
        if not self.comp.cpu.halted:
            decoded = self.comp.cpu.step()
            if decoded:
                self.status_var.set(
                    f"PC={self.comp.regs.PC}  OP={decoded['opcode_bits']}"
                )
            self.update_view()
        else:
            self.status_var.set("HALTED")

    def run(self):
        self.comp.cpu.run()
        self.status_var.set("HALTED" if self.comp.cpu.halted else "Terminado")
        self.update_view()

    def reset(self):
        self.comp.reset()
        self.status_var.set("Listo")
        self.update_view()

    def update_view(self):
        mem = self.comp.ram._memory

        # ── RAM ───────────────────────────────────────────────────────────
        self.mem.delete("1.0", tk.END)
        zones = {
            0xE0: "FPU_A", 0xE8: "FPU_B",
            0xF0: "FPU_OP", 0xF1: "FPU_R", 0xF9: "FPU_FL"
        }
        for i in range(256):
            tag = ""
            if i in zones:
                tag = f" ← {zones[i]}"
            elif 0xE0 < i < 0xE8:
                tag = " ← FPU_A"
            elif 0xE8 < i < 0xF0:
                tag = " ← FPU_B"
            elif 0xF1 < i < 0xF9:
                tag = " ← FPU_R"
            val_int = int(mem[i], 2)
            self.mem.insert(tk.END, f"{i:03d}(0x{i:02X}): {mem[i]}  {val_int:3d}{tag}\n")

        # Resaltar zona FPU
        self.mem.tag_configure("fpu", background="#ddeeff")
        # scroll a PC actual
        pc = self.comp.regs.PC
        self.mem.see(f"{max(1, pc-2)}.0")

        # ── Registros ─────────────────────────────────────────────────────
        r = self.comp.regs
        self.reg.delete("1.0", tk.END)
        self.reg.insert(tk.END, f"PC: {r.PC:3d}  (0x{r.PC:04X})\n")
        self.reg.insert(tk.END, f"SP: {r.SP:3d}  (0x{r.SP:04X})\n")
        self.reg.insert(tk.END, f"IR: {r.IR[:16]}...\n\n")
        for i in range(8):
            v = r.get_reg(i)
            self.reg.insert(tk.END, f"R{i}: {v:3d}  0x{v:02X}  {v:08b}\n")

        self.flags.config(
            text=f"Z:{int(r.flag_Z)}  C:{int(r.flag_C)}  "
                 f"N:{int(r.flag_N)}  V:{int(r.flag_V)}"
        )

        # ── Panel FPU ─────────────────────────────────────────────────────
        self.fpu_panel.delete("1.0", tk.END)

        def show_f64(label, base):
            try:
                raw = bytes(int(mem[base+i], 2) for i in range(8))
                val = struct.unpack(">d", raw)[0]
                hex_str = raw.hex().upper()
                self.fpu_panel.insert(
                    tk.END, f"{label}:\n  {val:.8g}\n  0x{hex_str}\n\n"
                )
            except Exception:
                self.fpu_panel.insert(tk.END, f"{label}: (no disponible)\n\n")

        show_f64(f"Operando A  (0xE0)", FPU_A_ADDR)
        show_f64(f"Operando B  (0xE8)", FPU_B_ADDR)

        op_val = int(mem[FPU_OP_ADDR], 2)
        op_names = {0:"(none)",1:"ADD",2:"SUB",3:"MUL",4:"DIV",5:"SQRT",6:"CMP"}
        self.fpu_panel.insert(
            tk.END, f"Operación   (0xF0): {op_val} = {op_names.get(op_val,'?')}\n\n"
        )

        show_f64(f"Resultado   (0xF1)", FPU_R_ADDR)

        flags_val = int(mem[FPU_FLAGS_ADDR], 2)
        z_flag = bool(flags_val & 0x01)
        c_flag = bool(flags_val & 0x02)
        n_flag = bool(flags_val & 0x04)
        self.fpu_panel.insert(
            tk.END,
            f"Flags FPU   (0xF9): {flags_val:08b}\n"
            f"  Z(igual)={int(z_flag)}  "
            f"C(A<B)={int(c_flag)}  "
            f"NaN={int(n_flag)}\n"
        )

    def start(self):
        self.root.mainloop()
